from typing import ClassVar, Dict

from TrifleSklad.audit.base import BaseAuditAction

_LABELS: Dict[str, str] = {
    "title": "Назва",
    "description": "Опис",
    "is_default": "За замовчуванням для рухів",
}


class _OwnerAction(BaseAuditAction):
    table_name: ClassVar[str] = "owners"
    FIELD_LABELS: ClassVar[Dict[str, str]] = _LABELS


class OwnerCreated(_OwnerAction):
    action: ClassVar[str] = "create"


class OwnerUpdated(_OwnerAction):
    action: ClassVar[str] = "update"


class OwnerDeleted(_OwnerAction):
    action: ClassVar[str] = "delete"
