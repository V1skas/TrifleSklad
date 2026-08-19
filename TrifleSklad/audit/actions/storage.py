from typing import ClassVar, Dict

from TrifleSklad.audit.base import BaseAuditAction, FieldResolver
from TrifleSklad.audit.labels import storage_type_label, worker_fio

_LABELS: Dict[str, str] = {
    "type": "Тип",
    "title": "Назва",
    "description": "Опис",
    "address": "Адреса",
    "id_responsible": "Відповідальний",
    "is_default": "За замовчуванням для рухів",
}


class _StorageAction(BaseAuditAction):
    table_name: ClassVar[str] = "storage"
    FIELD_LABELS: ClassVar[Dict[str, str]] = _LABELS
    FIELD_RESOLVERS: ClassVar[Dict[str, FieldResolver]] = {
        "type": storage_type_label,
        "id_responsible": worker_fio,
    }


class StorageCreated(_StorageAction):
    action: ClassVar[str] = "create"


class StorageUpdated(_StorageAction):
    action: ClassVar[str] = "update"


class StorageDeleted(_StorageAction):
    action: ClassVar[str] = "delete"
