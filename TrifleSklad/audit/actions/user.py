from typing import ClassVar, Dict, List

from TrifleSklad.audit.base import MISSING_LABEL, BaseAuditAction, FieldChange, FieldResolver
from TrifleSklad.audit.labels import worker_fio

_LABELS: Dict[str, str] = {
    "login": "Логін",
    "id_worker": "Прив'язаний співробітник",
    "password": "Пароль",
}


class _UserAction(BaseAuditAction):
    table_name: ClassVar[str] = "users"
    FIELD_LABELS: ClassVar[Dict[str, str]] = _LABELS
    # "password" — синтетичне поле, виставляється лише вручну через
    # mark_password_changed(); автообхід diff/for_create його не чіпає.
    AUTO_FIELDS: ClassVar[List[str]] = ["login", "id_worker"]
    FIELD_RESOLVERS: ClassVar[Dict[str, FieldResolver]] = {"id_worker": worker_fio}


class UserCreated(_UserAction):
    action: ClassVar[str] = "create"


class UserUpdated(_UserAction):
    action: ClassVar[str] = "update"

    def mark_password_changed(self) -> "UserUpdated":
        # password_hash/salt самі по собі ніколи не логуються — тільки факт зміни.
        self.fields["password"] = FieldChange(old=MISSING_LABEL, new="Змінено")
        return self


class UserDeleted(_UserAction):
    action: ClassVar[str] = "delete"
