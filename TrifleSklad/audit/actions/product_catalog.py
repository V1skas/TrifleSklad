from typing import ClassVar, Dict

from TrifleSklad.audit.base import BaseAuditAction, FieldResolver
from TrifleSklad.audit.labels import category_title

_LABELS: Dict[str, str] = {
    "title": "Назва",
    "description": "Опис",
    "id_category": "Категорія",
    "unit": "Одиниця виміру",
    "divisible": "Подільний",
    "uniq": "Унікальний (серійний)",
    "capacity": "Ємність одиниці",
    "no_fixed_capacity": "Без фіксованої ємності",
}


class _ProductCatalogAction(BaseAuditAction):
    table_name: ClassVar[str] = "products"
    FIELD_LABELS: ClassVar[Dict[str, str]] = _LABELS
    FIELD_RESOLVERS: ClassVar[Dict[str, FieldResolver]] = {"id_category": category_title}


class ProductCatalogCreated(_ProductCatalogAction):
    action: ClassVar[str] = "create"


class ProductCatalogUpdated(_ProductCatalogAction):
    action: ClassVar[str] = "update"


class ProductCatalogDeleted(_ProductCatalogAction):
    action: ClassVar[str] = "delete"
