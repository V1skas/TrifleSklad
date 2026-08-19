from typing import Dict, Tuple, Type

from TrifleSklad.audit.actions.category import CategoryCreated, CategoryDeleted, CategoryUpdated
from TrifleSklad.audit.actions.nds_rate import NdsRateCreated, NdsRateDeleted, NdsRateUpdated
from TrifleSklad.audit.actions.movement import (
    AdmissionCreated,
    AdmissionDeleted,
    AdmissionUpdated,
    ClientIssueCreated,
    ClientIssueDeleted,
    ClientIssueUpdated,
    IssueCreated,
    IssueDeleted,
    IssueUpdated,
    ReturnCreated,
    ReturnDeleted,
    ReturnUpdated,
    SaleCreated,
    SaleDeleted,
    SaleReturnCreated,
    SaleReturnDeleted,
    SaleReturnUpdated,
    SaleUpdated,
    TransferCreated,
    TransferDeleted,
    TransferUpdated,
    WriteOffCreated,
    WriteOffDeleted,
    WriteOffUpdated,
)
from TrifleSklad.audit.actions.owner import OwnerCreated, OwnerDeleted, OwnerUpdated
from TrifleSklad.audit.actions.payment_type import PaymentTypeCreated, PaymentTypeDeleted, PaymentTypeUpdated
from TrifleSklad.audit.actions.product_catalog import (
    ProductCatalogCreated,
    ProductCatalogDeleted,
    ProductCatalogUpdated,
)
from TrifleSklad.audit.actions.request import RequestCreated, RequestDeleted, RequestUpdated
from TrifleSklad.audit.actions.role import RoleCreated, RoleDeleted, RoleUpdated
from TrifleSklad.audit.actions.storage import StorageCreated, StorageDeleted, StorageUpdated
from TrifleSklad.audit.actions.supplier import SupplierCreated, SupplierDeleted, SupplierUpdated
from TrifleSklad.audit.actions.user import UserCreated, UserDeleted, UserUpdated
from TrifleSklad.audit.actions.worker import WorkerCreated, WorkerDeleted, WorkerUpdated
from TrifleSklad.audit.base import BaseAuditAction
from TrifleSklad.models import AuditLog

ACTIONS: Dict[Tuple[str, str], Type[BaseAuditAction]] = {}


def _register(*classes: Type[BaseAuditAction]) -> None:
    for cls in classes:
        ACTIONS[(cls.table_name, cls.action)] = cls


_register(WorkerCreated, WorkerUpdated, WorkerDeleted)
_register(RoleCreated, RoleUpdated, RoleDeleted)
_register(UserCreated, UserUpdated, UserDeleted)
_register(CategoryCreated, CategoryUpdated, CategoryDeleted)
_register(ProductCatalogCreated, ProductCatalogUpdated, ProductCatalogDeleted)
_register(OwnerCreated, OwnerUpdated, OwnerDeleted)
_register(SupplierCreated, SupplierUpdated, SupplierDeleted)
_register(StorageCreated, StorageUpdated, StorageDeleted)
_register(PaymentTypeCreated, PaymentTypeUpdated, PaymentTypeDeleted)
_register(NdsRateCreated, NdsRateUpdated, NdsRateDeleted)
_register(WriteOffCreated, WriteOffUpdated, WriteOffDeleted)
_register(TransferCreated, TransferUpdated, TransferDeleted)
_register(ReturnCreated, ReturnUpdated, ReturnDeleted)
_register(AdmissionCreated, AdmissionUpdated, AdmissionDeleted)
_register(IssueCreated, IssueUpdated, IssueDeleted)
_register(ClientIssueCreated, ClientIssueUpdated, ClientIssueDeleted)
_register(SaleCreated, SaleUpdated, SaleDeleted)
_register(SaleReturnCreated, SaleReturnUpdated, SaleReturnDeleted)
_register(RequestCreated, RequestUpdated, RequestDeleted)


def parse_changes(log: AuditLog) -> BaseAuditAction:
    action_cls = ACTIONS[(log.table_name, log.action)]
    return action_cls.model_validate_json(log.changes)
