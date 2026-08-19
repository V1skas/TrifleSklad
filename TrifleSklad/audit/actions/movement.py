from typing import ClassVar, Dict, Optional

from TrifleSklad.audit.base import BaseAuditAction, FieldResolver
from TrifleSklad.audit.labels import (
    movement_status_label,
    nds_rate_title,
    owner_title,
    payment_type_title,
    sale_reference,
    storage_title,
    supplier_title,
    worker_fio,
)
from TrifleSklad.declared import MovementsType

_COMMON_LABELS: Dict[str, str] = {
    "id_incoming_storage": "Склад/площадка джерела",
    "id_destination_storage": "Склад/площадка призначення",
    "id_incoming_owner": "Власник джерела",
    "id_destination_owner": "Власник призначення",
    "date": "Дата",
    "comment": "Коментар",
    "status": "Статус",
    "total_cost": "Загальна вартість",
}
_COMMON_RESOLVERS: Dict[str, FieldResolver] = {
    "id_incoming_storage": storage_title,
    "id_destination_storage": storage_title,
    "id_incoming_owner": owner_title,
    "id_destination_owner": owner_title,
    "status": movement_status_label,
}


def _movement_action_group(
    name_prefix: str,
    tbl_name: str,
    extra_labels: Optional[Dict[str, str]] = None,
    extra_resolvers: Optional[Dict[str, FieldResolver]] = None,
):
    """Будує (Created, Updated, Deleted) трійку для одного типу руху зі спільними
    полями Movement + додатковими полями дочірньої таблиці (якщо є)."""
    labels = {**_COMMON_LABELS, **(extra_labels or {})}
    resolvers = {**_COMMON_RESOLVERS, **(extra_resolvers or {})}

    class _Base(BaseAuditAction):
        table_name: ClassVar[str] = tbl_name
        FIELD_LABELS: ClassVar[Dict[str, str]] = labels
        FIELD_RESOLVERS: ClassVar[Dict[str, FieldResolver]] = resolvers

    class Created(_Base):
        action: ClassVar[str] = "create"

    class Updated(_Base):
        action: ClassVar[str] = "update"

    class Deleted(_Base):
        action: ClassVar[str] = "delete"

    for cls, suffix in ((Created, "Created"), (Updated, "Updated"), (Deleted, "Deleted")):
        cls.__name__ = cls.__qualname__ = f"{name_prefix}{suffix}"

    return Created, Updated, Deleted


WriteOffCreated, WriteOffUpdated, WriteOffDeleted = _movement_action_group("WriteOff", "write_offs")
TransferCreated, TransferUpdated, TransferDeleted = _movement_action_group("Transfer", "movements")
ReturnCreated, ReturnUpdated, ReturnDeleted = _movement_action_group("Return", "returns")

AdmissionCreated, AdmissionUpdated, AdmissionDeleted = _movement_action_group(
    "Admission",
    "admissions",
    extra_labels={
        "id_payment_type": "Тип оплати",
        "id_supplier": "Постачальник",
        "flag_nds": "Ціна вказана з ПДВ",
        "id_nds_rate": "Ставка ПДВ",
        "dollar_rate": "Курс долара",
        "invoice_number": "Номер накладної",
    },
    extra_resolvers={
        "id_payment_type": payment_type_title,
        "id_supplier": supplier_title,
        "id_nds_rate": nds_rate_title,
    },
)

IssueCreated, IssueUpdated, IssueDeleted = _movement_action_group(
    "Issue",
    "issues",
    extra_labels={"id_recipient": "Отримувач"},
    extra_resolvers={"id_recipient": worker_fio},
)

ClientIssueCreated, ClientIssueUpdated, ClientIssueDeleted = _movement_action_group(
    "ClientIssue",
    "client_issues",
    extra_labels={
        "id_recipient": "Отримувач",
        "contract_number": "Номер договору",
        "installation_address": "Адреса встановлення",
    },
    extra_resolvers={"id_recipient": worker_fio},
)

SaleCreated, SaleUpdated, SaleDeleted = _movement_action_group(
    "Sale",
    "sales",
    extra_labels={"id_responsible": "Відповідальний", "client_info": "Інформація про клієнта"},
    extra_resolvers={"id_responsible": worker_fio},
)

SaleReturnCreated, SaleReturnUpdated, SaleReturnDeleted = _movement_action_group(
    "SaleReturn",
    "sale_returns",
    extra_labels={"id_sale": "Вихідний продаж"},
    extra_resolvers={"id_sale": sale_reference},
)

# Повна мапа типу руху -> (Created, Updated, Deleted). Потрібна для
# MovementDAO.cancel_movement (скасування — спільна дія для УСІХ 8 типів, не
# лише write_off/movements/returns, що йдуть через MovementDAO.add_one/edit_one
# без власної дочірньої таблиці) і для MovementDAO.add_one/edit_one самих.
_MOVEMENT_TYPE_ACTIONS = {
    MovementsType.ADMISSION: (AdmissionCreated, AdmissionUpdated, AdmissionDeleted),
    MovementsType.WRITE_OFF: (WriteOffCreated, WriteOffUpdated, WriteOffDeleted),
    MovementsType.MOVEMENT: (TransferCreated, TransferUpdated, TransferDeleted),
    MovementsType.ISSUE: (IssueCreated, IssueUpdated, IssueDeleted),
    MovementsType.SALE: (SaleCreated, SaleUpdated, SaleDeleted),
    MovementsType.RETURN: (ReturnCreated, ReturnUpdated, ReturnDeleted),
    MovementsType.SALE_RETURN: (SaleReturnCreated, SaleReturnUpdated, SaleReturnDeleted),
    MovementsType.CLIENT_ISSUE: (ClientIssueCreated, ClientIssueUpdated, ClientIssueDeleted),
}


def movement_actions_for(movement_type: int):
    """(Created, Updated, Deleted) для довільного типу руху (MovementsType).
    Для типів із власною дочірньою таблицею (admission/issue/...) поля, яких
    немає на базовому Movement, просто не потраплять у diff (getattr -> None
    з обох боків) — придатно й для MovementDAO.cancel_movement, який працює
    лише з полями самого Movement незалежно від типу."""
    return _MOVEMENT_TYPE_ACTIONS[movement_type]
