from typing import ClassVar, Dict

from TrifleSklad.audit.base import BaseAuditAction, FieldResolver
from TrifleSklad.audit.labels import category_title

_LABELS: Dict[str, str] = {
    "title": "Назва",
    "description": "Опис",
    "id_parent": "Батьківська категорія",
}


class _CategoryAction(BaseAuditAction):
    table_name: ClassVar[str] = "categories"
    FIELD_LABELS: ClassVar[Dict[str, str]] = _LABELS
    FIELD_RESOLVERS: ClassVar[Dict[str, FieldResolver]] = {"id_parent": category_title}


class CategoryCreated(_CategoryAction):
    action: ClassVar[str] = "create"


class CategoryUpdated(_CategoryAction):
    action: ClassVar[str] = "update"


class CategoryDeleted(_CategoryAction):
    action: ClassVar[str] = "delete"
