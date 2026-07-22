from typing import ClassVar, Dict

from sqlmodel import Session

from TrifleSklad.audit.base import BaseAuditAction, FieldResolver, MISSING_LABEL
from TrifleSklad.audit.labels import (
    movement_reference,
    movement_type_label,
    request_status_label,
    storage_title,
    user_fio_by_login,
    worker_fio,
)
from TrifleSklad.dao.product_catalog import ProductCatalogDao
from TrifleSklad.declared import format_request_qty

_LABELS: Dict[str, str] = {
    "type": "Тип",
    "id_author": "Автор заявки",
    "id_responsible": "Відповідальний",
    "id_destination_storage": "Склад призначення",
    "date": "Дата",
    "comment": "Коментар",
    "status": "Статус",
    "id_movement": "Пов'язаний рух",
}
_RESOLVERS: Dict[str, FieldResolver] = {
    "type": movement_type_label,
    "id_author": user_fio_by_login,
    "id_responsible": worker_fio,
    "id_destination_storage": storage_title,
    "status": request_status_label,
    "id_movement": movement_reference,
}


class _RequestAction(BaseAuditAction):
    table_name: ClassVar[str] = "requests"
    FIELD_LABELS: ClassVar[Dict[str, str]] = _LABELS
    FIELD_RESOLVERS: ClassVar[Dict[str, FieldResolver]] = _RESOLVERS


class RequestCreated(_RequestAction):
    action: ClassVar[str] = "create"


class RequestUpdated(_RequestAction):
    action: ClassVar[str] = "update"


class RequestDeleted(_RequestAction):
    action: ClassVar[str] = "delete"


def request_position_title(position, session: Session) -> str:
    catalog_id = position[0]
    catalog = ProductCatalogDao.get_by_id(catalog_id, session, with_del=True)
    return catalog.title if catalog is not None else MISSING_LABEL


def request_position_label(position, session: Session) -> str:
    catalog_id, count, part = position
    catalog = ProductCatalogDao.get_by_id(catalog_id, session, with_del=True)
    unit = catalog.unit if catalog is not None else ""
    return format_request_qty(count, part, unit)
