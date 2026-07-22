from typing import ClassVar, Dict

from TrifleSklad.audit.base import BaseAuditAction

_LABELS: Dict[str, str] = {
    "title": "Назва",
    "description": "Опис",
    "address": "Адреса",
    "email": "Email",
    "contact_person": "Контактна особа",
    "contact_phone": "Контактний телефон",
    "edrpou": "ЄДРПОУ",
}


class _SupplierAction(BaseAuditAction):
    table_name: ClassVar[str] = "suppliers"
    FIELD_LABELS: ClassVar[Dict[str, str]] = _LABELS


class SupplierCreated(_SupplierAction):
    action: ClassVar[str] = "create"


class SupplierUpdated(_SupplierAction):
    action: ClassVar[str] = "update"


class SupplierDeleted(_SupplierAction):
    action: ClassVar[str] = "delete"
