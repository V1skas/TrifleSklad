from typing import ClassVar, Dict

from TrifleSklad.audit.base import BaseAuditAction

_LABELS: Dict[str, str] = {
    "fio": "ПІБ",
    "phone_number": "Телефон",
    "email": "Email",
    "position": "Посада",
    "is_default": "За замовчуванням для рухів",
}


class _WorkerAction(BaseAuditAction):
    table_name: ClassVar[str] = "workers"
    FIELD_LABELS: ClassVar[Dict[str, str]] = _LABELS


class WorkerCreated(_WorkerAction):
    action: ClassVar[str] = "create"


class WorkerUpdated(_WorkerAction):
    action: ClassVar[str] = "update"


class WorkerDeleted(_WorkerAction):
    action: ClassVar[str] = "delete"
