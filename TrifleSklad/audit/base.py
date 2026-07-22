from types import SimpleNamespace
from typing import Any, Callable, ClassVar, Dict, List, Optional

from pydantic import BaseModel
from sqlmodel import Session

MISSING_LABEL = "—"

# Резолвер: (значення_поля, сесія) -> людський підпис.
FieldResolver = Callable[[Any, Session], str]


class FieldChange(BaseModel):
    old: Optional[str] = None
    new: Optional[str] = None


class LineChange(BaseModel):
    """Зміна пов'язаного рядка (позиція ТМЦ, роль тощо): додано/видалено/змінено."""

    kind: str  # "added" | "removed" | "changed"
    title: str
    old: Optional[str] = None
    new: Optional[str] = None


def bool_label(value: Optional[bool], _session: Session) -> str:
    if value is None:
        return MISSING_LABEL
    return "Так" if value else "Ні"


class BaseAuditAction(BaseModel):
    """Базовий клас декларативних дій аудиту. Підклас на сутність оголошує лише
    `action`/`table_name` (ClassVar) і словник `FIELD_LABELS` (поле -> підпис),
    опційно `FIELD_RESOLVERS` (поле -> функція резолву FK/enum у рядок) —
    вся механіка diff/serialize/describe — тут, спільна для всіх сутностей."""

    action: ClassVar[str]
    table_name: ClassVar[str]
    FIELD_LABELS: ClassVar[Dict[str, str]] = {}
    FIELD_RESOLVERS: ClassVar[Dict[str, FieldResolver]] = {}
    # Підмножина ключів FIELD_LABELS, які diff/for_create/for_delete обходять
    # автоматично. None (типово) — усі ключі FIELD_LABELS. Звужується, коли в
    # словнику є "синтетичні" підписи для полів, що виставляються вручну поза
    # автоматичним обходом (напр. User.password — див. mark_password_changed).
    AUTO_FIELDS: ClassVar[Optional[List[str]]] = None

    summary: str = ""
    fields: Dict[str, FieldChange] = {}
    lines: List[LineChange] = []

    def has_changes(self) -> bool:
        return bool(self.fields) or bool(self.lines)

    def describe(self) -> List[str]:
        """Людиночитний перелік змін для розгорнутого рядка історії."""
        lines: List[str] = []
        for name, change in self.fields.items():
            label = self.FIELD_LABELS.get(name, name)
            if self.action == "create":
                lines.append(f"{label}: {change.new}")
            elif self.action == "delete":
                lines.append(f"{label}: {change.old}")
            else:
                lines.append(f"{label}: {change.old} → {change.new}")
        for line in self.lines:
            if line.kind == "added":
                suffix = f" ({line.new})" if line.new else ""
                lines.append(f"Додано: {line.title}{suffix}")
            elif line.kind == "removed":
                suffix = f" ({line.old})" if line.old else ""
                lines.append(f"Видалено: {line.title}{suffix}")
            else:
                lines.append(f"{line.title}: {line.old} → {line.new}")
        return lines

    def describe_rows(self) -> List[tuple]:
        """(підпис, було, стало) для табличного відображення розгорнутого
        рядка історії в UI — структурована альтернатива describe()."""
        rows: List[tuple] = []
        for name, change in self.fields.items():
            label = self.FIELD_LABELS.get(name, name)
            rows.append((label, change.old or "", change.new or ""))
        for line in self.lines:
            if line.kind == "added":
                rows.append((f"Додано: {line.title}", "", line.new or ""))
            elif line.kind == "removed":
                rows.append((f"Видалено: {line.title}", line.old or "", ""))
            else:
                rows.append((line.title, line.old or "", line.new or ""))
        return rows

    def summary_text(self) -> str:
        """Короткий підсумок для згорнутого рядка історії (без розгортання)."""
        if self.action == "create":
            return "Створено"
        if self.action == "delete":
            return "Видалено"
        labels = [self.FIELD_LABELS.get(name, name) for name in self.fields]
        for line in self.lines:
            prefix = {"added": "Додано: ", "removed": "Видалено: "}.get(line.kind, "")
            labels.append(f"{prefix}{line.title}")
        if not labels:
            return "Без змін"
        preview = ", ".join(labels[:3])
        if len(labels) > 3:
            preview += f" та ще {len(labels) - 3}"
        return f"Змінено: {preview}"

    @classmethod
    def _auto_fields(cls) -> List[str]:
        return cls.AUTO_FIELDS if cls.AUTO_FIELDS is not None else list(cls.FIELD_LABELS)

    @classmethod
    def snapshot(cls, obj: Any) -> SimpleNamespace:
        """Знімок значень полів `FIELD_LABELS` у незалежний від ORM-сесії
        об'єкт — знімати ДО `session.merge()`/мутації, інакше diff порівнює
        об'єкт сам із собою (той самий рядок у identity map)."""
        return SimpleNamespace(**{name: getattr(obj, name, None) for name in cls.FIELD_LABELS})

    @classmethod
    def _resolve(cls, name: str, value: Any, session: Session) -> str:
        resolver = cls.FIELD_RESOLVERS.get(name)
        if resolver is not None:
            return resolver(value, session)
        if value is None or value == "":
            return MISSING_LABEL
        if isinstance(value, bool):
            return "Так" if value else "Ні"
        return str(value)

    @classmethod
    def for_create(
        cls, obj: Any, session: Session, *, summary: str = "", lines: Optional[List[LineChange]] = None
    ) -> "BaseAuditAction":
        fields = {
            name: FieldChange(new=cls._resolve(name, getattr(obj, name, None), session))
            for name in cls._auto_fields()
        }
        return cls(summary=summary, fields=fields, lines=lines or [])

    @classmethod
    def for_delete(
        cls, obj: Any, session: Session, *, summary: str = "", lines: Optional[List[LineChange]] = None
    ) -> "BaseAuditAction":
        fields = {
            name: FieldChange(old=cls._resolve(name, getattr(obj, name, None), session))
            for name in cls._auto_fields()
        }
        return cls(summary=summary, fields=fields, lines=lines or [])

    @classmethod
    def from_diff(
        cls, old: Any, new: Any, session: Session, *, summary: str = "", lines: Optional[List[LineChange]] = None
    ) -> "BaseAuditAction":
        fields: Dict[str, FieldChange] = {}
        for name in cls._auto_fields():
            old_val = getattr(old, name, None)
            new_val = getattr(new, name, None)
            if old_val != new_val:
                fields[name] = FieldChange(
                    old=cls._resolve(name, old_val, session),
                    new=cls._resolve(name, new_val, session),
                )
        return cls(summary=summary, fields=fields, lines=lines or [])
