from types import SimpleNamespace
from typing import Any, Callable, List, Optional

from sqlmodel import Session

from TrifleSklad.audit.base import MISSING_LABEL, LineChange
from TrifleSklad.dao.nds_rate import NdsRateDao
from TrifleSklad.dao.owner import OwnerDao
from TrifleSklad.dao.payment_type import PaymentTypeDao
from TrifleSklad.dao.product_catalog import ProductCatalogDao
from TrifleSklad.dao.product_category import ProductCategoryDao
from TrifleSklad.dao.storage import StorageDao
from TrifleSklad.dao.supplier import SupplierDao
from TrifleSklad.dao.user import UserDao
from TrifleSklad.dao.worker import WorkerDao
from TrifleSklad.declared import (
    format_amount,
    movements_status_list,
    movements_type_list,
    request_status_list,
    storage_type_list,
)

ACTION_LABELS = {"create": "Створення", "update": "Редагування", "delete": "Видалення"}


def _fk_title(dao_get_by_id: Callable, value: Optional[int], session: Session, attr: str = "title") -> str:
    """Резолвить FK у назву пов'язаного запису. `with_del=True` — щоб історичні
    посилання на вже видалений довідник (на момент читання) все одно
    показували назву на момент запису дії (назви денормалізуються при записі)."""
    if not value:
        return MISSING_LABEL
    obj = dao_get_by_id(value, session, with_del=True)
    if obj is None:
        return MISSING_LABEL
    return getattr(obj, attr, None) or MISSING_LABEL


def category_title(value: Any, session: Session) -> str:
    return _fk_title(ProductCategoryDao.get_by_id, value, session)


def owner_title(value: Any, session: Session) -> str:
    return _fk_title(OwnerDao.get_by_id, value, session)


def storage_title(value: Any, session: Session) -> str:
    return _fk_title(StorageDao.get_by_id, value, session)


def supplier_title(value: Any, session: Session) -> str:
    return _fk_title(SupplierDao.get_by_id, value, session)


def payment_type_title(value: Any, session: Session) -> str:
    return _fk_title(PaymentTypeDao.get_by_id, value, session)


def nds_rate_title(value: Any, session: Session) -> str:
    return _fk_title(NdsRateDao.get_by_id, value, session)


def product_catalog_title(value: Any, session: Session) -> str:
    return _fk_title(ProductCatalogDao.get_by_id, value, session)


def worker_fio(value: Any, session: Session) -> str:
    return _fk_title(WorkerDao.get_by_id, value, session, attr="fio")


def user_fio_by_login(value: Any, session: Session) -> str:
    if not value:
        return MISSING_LABEL
    return UserDao.get_fio(value, session) or value


def storage_type_label(value: Any, _session: Session) -> str:
    if value is None:
        return MISSING_LABEL
    return storage_type_list.get(value, str(value))


def movement_status_label(value: Any, _session: Session) -> str:
    if value is None or not (0 <= value < len(movements_status_list)):
        return MISSING_LABEL
    return movements_status_list[value]


def request_status_label(value: Any, _session: Session) -> str:
    if value is None or not (0 <= value < len(request_status_list)):
        return MISSING_LABEL
    return request_status_list[value]


def movement_type_label(value: Any, _session: Session) -> str:
    if value is None:
        return MISSING_LABEL
    return movements_type_list.get(value, str(value))


def movement_reference(value: Any, _session: Session) -> str:
    return f"Рух №{value}" if value else MISSING_LABEL


def sale_reference(value: Any, _session: Session) -> str:
    return f"Продаж №{value}" if value else MISSING_LABEL


def diff_related_titles(
    old_items: Optional[List[Any]],
    new_items: Optional[List[Any]],
    *,
    key: Callable[[Any], Any] = lambda x: x.id,
    title: Callable[[Any], str] = lambda x: x.title,
) -> List[LineChange]:
    """Діф двох списків пов'язаних об'єктів (ролі/права користувача, права
    ролі) у LineChange (додано/видалено) за назвами, а не id."""
    old_by_key = {key(i): i for i in (old_items or [])}
    new_by_key = {key(i): i for i in (new_items or [])}
    lines: List[LineChange] = []
    for k, item in new_by_key.items():
        if k not in old_by_key:
            lines.append(LineChange(kind="added", title=title(item)))
    for k, item in old_by_key.items():
        if k not in new_by_key:
            lines.append(LineChange(kind="removed", title=title(item)))
    return lines


def movement_position_title(line: Any, session: Session) -> str:
    return product_catalog_title(line.id_product_catalog, session)


def movement_position_label(line: Any, _session: Session) -> str:
    return f"{line.count} × {line.price}"


def snapshot_position_lines(items: Optional[List[Any]]) -> List[SimpleNamespace]:
    """Знімок позицій (id каталогу/кількість/ціна) у незалежні від ORM-сесії
    об'єкти — знімати ДО `session.merge()`, інакше `session.merge` мутує ТІ Ж
    рядкові об'єкти in place (identity map) і diff порівнює значення саме з
    собою."""
    return [
        SimpleNamespace(id_product_catalog=item.id_product_catalog, count=item.count, price=item.price)
        for item in (items or [])
    ]


# Поріг, після якого поштучний перелік одиниць у записі аудиту замінюється
# агрегатом — інакше рух на сотні одиниць роздуває JSON `audit_logs.changes`.
UNIT_LINES_LIMIT = 50


def snapshot_unit_rows(units: Optional[List[Any]]) -> List[SimpleNamespace]:
    """Знімок складу руху (id одиниці / id каталогу / s/n / залишок) у незалежні
    від ORM-сесії об'єкти — знімати ДО мутацій складу, та сама пастка identity
    map, що й у `snapshot_position_lines`."""
    return [
        SimpleNamespace(
            id=unit.id,
            id_product_catalog=unit.id_product_catalog,
            serial_number=unit.serial_number,
            count=unit.count,
            price=getattr(unit, "price", None),
        )
        for unit in (units or [])
    ]


def _unit_title(unit: Any, session: Session) -> str:
    return f"Одиниця №{unit.id} — {product_catalog_title(unit.id_product_catalog, session)}"


def _unit_label(unit: Any) -> str:
    chunks: List[str] = []
    if getattr(unit, "serial_number", None):
        chunks.append(f"s/n {unit.serial_number}")
    if getattr(unit, "count", None) is not None:
        chunks.append(f"залишок {format_amount(unit.count)}")
    if getattr(unit, "price", None) is not None:
        chunks.append(f"ціна {format_amount(unit.price)}")
    return " · ".join(chunks) if chunks else MISSING_LABEL


def diff_unit_lines(
    old_units: Optional[List[Any]],
    new_units: Optional[List[Any]],
    session: Session,
) -> List[LineChange]:
    """Діф складу руху до КОНКРЕТНИХ одиниць ТМЦ — доповнює
    `diff_position_lines`, який схлопує позиції за id каталогу і тому не бачить
    заміну однієї одиниці іншою в межах тієї самої позиції.

    Понад `UNIT_LINES_LIMIT` змін — повертає агрегати замість поштучного
    переліку."""
    old_by_id = {unit.id: unit for unit in (old_units or [])}
    new_by_id = {unit.id: unit for unit in (new_units or [])}
    added = [unit for unit_id, unit in new_by_id.items() if unit_id not in old_by_id]
    removed = [unit for unit_id, unit in old_by_id.items() if unit_id not in new_by_id]

    if len(added) + len(removed) > UNIT_LINES_LIMIT:
        result: List[LineChange] = []
        if added:
            result.append(LineChange(kind="added", title="Одиниці ТМЦ", new=f"{len(added)} шт."))
        if removed:
            result.append(LineChange(kind="removed", title="Одиниці ТМЦ", old=f"{len(removed)} шт."))
        return result

    return [
        *(
            LineChange(kind="added", title=_unit_title(unit, session), new=_unit_label(unit))
            for unit in added
        ),
        *(
            LineChange(kind="removed", title=_unit_title(unit, session), old=_unit_label(unit))
            for unit in removed
        ),
    ]


def movement_view(entity: Any) -> SimpleNamespace:
    """Дочірні сутності руху (Admission/Issue/ClientIssue/Sale/SaleReturn)
    успадковують спільні поля Movement (склад/власник/дата/статус/…) лише
    через relationship `.movement`, а не як власні атрибути. Об'єднує обидва
    набори полів у єдиний об'єкт для BaseAuditAction.for_create/from_diff/
    snapshot, які читають поля через звичайний getattr(entity, name)."""
    movement = getattr(entity, "movement", None)
    merged: dict = {}
    if movement is not None:
        merged.update({k: v for k, v in vars(movement).items() if not k.startswith("_")})
    merged.update({k: v for k, v in vars(entity).items() if not k.startswith("_")})
    return SimpleNamespace(**merged)


def diff_position_lines(
    old_items: Optional[List[Any]],
    new_items: Optional[List[Any]],
    session: Session,
    *,
    key: Callable[[Any], Any],
    title: Callable[[Any, Session], str],
    label: Callable[[Any, Session], str],
) -> List[LineChange]:
    """Діф позицій ТМЦ руху/заявки (незалежно від конкретного типу рядка —
    MovementProductsCatalog чи кортеж заявки) у LineChange за назвою каталогу.
    `key` — ідентифікатор позиції (зазвичай id каталогу), `title` — резолв
    назви, `label` — текстовий опис кількості/ціни для порівняння/показу."""
    old_by_key = {key(i): i for i in (old_items or [])}
    new_by_key = {key(i): i for i in (new_items or [])}
    result: List[LineChange] = []
    for k, new_item in new_by_key.items():
        item_title = title(new_item, session)
        old_item = old_by_key.get(k)
        if old_item is None:
            result.append(LineChange(kind="added", title=item_title, new=label(new_item, session)))
        elif label(old_item, session) != label(new_item, session):
            result.append(
                LineChange(kind="changed", title=item_title, old=label(old_item, session), new=label(new_item, session))
            )
    for k, old_item in old_by_key.items():
        if k not in new_by_key:
            result.append(LineChange(kind="removed", title=title(old_item, session), old=label(old_item, session)))
    return result
