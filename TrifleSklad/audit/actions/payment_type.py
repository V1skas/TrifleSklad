from typing import ClassVar, Dict

from TrifleSklad.audit.base import BaseAuditAction

_LABELS: Dict[str, str] = {
    "title": "Назва",
    "description": "Опис",
    "is_default": "За замовчуванням для рухів",
}


class _PaymentTypeAction(BaseAuditAction):
    table_name: ClassVar[str] = "payment_types"
    FIELD_LABELS: ClassVar[Dict[str, str]] = _LABELS


class PaymentTypeCreated(_PaymentTypeAction):
    action: ClassVar[str] = "create"


class PaymentTypeUpdated(_PaymentTypeAction):
    action: ClassVar[str] = "update"


class PaymentTypeDeleted(_PaymentTypeAction):
    action: ClassVar[str] = "delete"
