from typing import ClassVar, Dict

from TrifleSklad.audit.base import BaseAuditAction

_LABELS: Dict[str, str] = {
    "title": "Назва",
    "description": "Опис",
}


class _RoleAction(BaseAuditAction):
    table_name: ClassVar[str] = "roles"
    FIELD_LABELS: ClassVar[Dict[str, str]] = _LABELS


class RoleCreated(_RoleAction):
    action: ClassVar[str] = "create"


class RoleUpdated(_RoleAction):
    action: ClassVar[str] = "update"


class RoleDeleted(_RoleAction):
    action: ClassVar[str] = "delete"
