from typing import ClassVar, Dict

from TrifleSklad.audit.base import BaseAuditAction

_LABELS: Dict[str, str] = {
    "title": "Назва",
    "rate": "Ставка, %",
    "description": "Опис",
    "is_default": "За замовчуванням для рухів",
}


class _NdsRateAction(BaseAuditAction):
    table_name: ClassVar[str] = "nds_rates"
    FIELD_LABELS: ClassVar[Dict[str, str]] = _LABELS


class NdsRateCreated(_NdsRateAction):
    action: ClassVar[str] = "create"


class NdsRateUpdated(_NdsRateAction):
    action: ClassVar[str] = "update"


class NdsRateDeleted(_NdsRateAction):
    action: ClassVar[str] = "delete"
