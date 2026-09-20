from typing import List, Optional, Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.dao_legacy import (
    IssueDAO,
    MovementDAO,
    OwnerDAO,
    ProductDAO,
    RequestDAO,
    StorageDAO,
    WorkerDAO,
)
from TrifleSklad.declared import (
    MovementsStatus,
    MovementsType,
    StorageType,
    format_request_qty,
    movements_status_list,
    movements_type_list,
)
from TrifleSklad.models import (
    Issue,
    Movement,
    MovementProductsCatalog,
    Product,
    ProductCatalog,
)
from TrifleSklad.movement.inline_creators import LookupCreatorsMixin
from TrifleSklad.movement.list_mixin import ALL, MovementListFilterMixin
from TrifleSklad.movement.products.backend import ProductsMovementListState
from TrifleSklad.services.errors import ServiceError
from TrifleSklad.services.movement_edit import FullEditPayload, MovementEditService
from TrifleSklad.states.app import AppState
from TrifleSklad.states.audit_mixin import AuditHistoryMixin
from TrifleSklad.states.movement_cancel_mixin import CancelWithReasonMixin
from TrifleSklad.states.movement_edit_mixin import FullEditMixin
from TrifleSklad.utils.clock import now_local


class ListIssueState(MovementListFilterMixin, AppState):
    items: List[Issue] = []
    in_progress: bool = True

    filter_recipient: str = ALL
    filter_site: str = ALL
    list_recipients: List[Tuple[str, str]] = []
    list_sites: List[Tuple[str, str]] = []

    def _load_section_filter_options(self):
        self.list_recipients = [(w.fio, str(w.id)) for w in WorkerDAO.get_all()]
        sites = StorageDAO.get_all_by_type(StorageType.TECHNICAL_SITE) + \
            StorageDAO.get_all_by_type(StorageType.DEPARTMENT)
        self.list_sites = [(s.title, str(s.id)) for s in sites]

    def _reset_section_filter_values(self):
        self.filter_recipient = ALL
        self.filter_site = ALL

    def _reload(self):
        self._all_pages, self.items = IssueDAO.get_paginated(
            self._current_page,
            self._limit,
            self._date_from_eff(),
            self._date_to_eff(),
            self.selected_statuses,
            incoming_storage=self.filter_incoming_storage,
            incoming_owner=self.filter_incoming_owner,
            site=self.filter_site,
            recipient=self.filter_recipient,
            catalog_ids=self.selected_catalog_ids,
        )

    @rx.event
    def on_load(self):
        if not self.has_permission(Action.ISSUES_LIST):
            yield rx.redirect(routes.WELCOME)
            yield rx.toast.error("У Вас немає дозволу на перегляд цієї сторінки!")
            return
        self.in_progress = True
        self._enter_list()
        self._reload()
        self.in_progress = False

    @rx.event
    def on_click_add(self):
        return rx.redirect(routes.MOVEMENT_ISSUES_ADD)

    @rx.event
    def on_change_filter_recipient(self, value: str):
        self.filter_recipient = value
        return self._apply_filters()

    @rx.event
    def on_change_filter_site(self, value: str):
        self.filter_site = value
        return self._apply_filters()

    @rx.var
    def has_active_filters(self) -> bool:
        return bool(
            self.filter_date_enabled
            or self.selected_statuses
            or self.selected_catalog_ids
            or self.filter_incoming_storage != ALL
            or self.filter_incoming_owner != ALL
            or self.filter_site != ALL
            or self.filter_recipient != ALL
        )

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def get_items(self) -> List[Tuple[int, Issue]]:
        return [(index, item) for index, item in enumerate(self.items)]

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list


class ViewIssueState(CancelWithReasonMixin, AuditHistoryMixin, AppState):
    HISTORY_TABLE = "issues"
    HISTORY_ACTION = Action.ISSUES_HISTORY
    HISTORY_DETAIL_ACTION = Action.ISSUES_HISTORY_DETAIL

    item: Issue = Issue(
        id_recipient=-1,
        movement=Movement(
            id_incoming_storage=-1,
            id_incoming_owner=-1,
            date=now_local().date().__str__(),
            comment="",
            status=MovementsStatus.CREATED,
            type=MovementsType.ISSUE,
            total_cost=0.0,
            products_catalog=[],
        ),
    )
    in_process: bool = True

    _products_selector_state: Optional[ProductsMovementListState] = None

    cancel_conflict_movements: List[Movement] = []
    is_cancel_conflict_dialog_open: bool = False

    @rx.event
    async def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(Action.ISSUES_VIEW):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        self.in_process = True
        item = IssueDAO.get_by_id_with_movement_product_storage_owner_recipient(int(id))
        if item is None:
            self.in_process = False
            yield rx.redirect(routes.MOVEMENT_ISSUES)
            yield rx.toast.error("Запис не знайдено!")
            return
        self.item = item
        self._products_selector_state = await self.get_state(ProductsMovementListState)
        await self._products_selector_state.on_load()
        self._products_selector_state.set_view_mode(True)

        all_products: List[Product] = []
        for product_category in self.item.movement.products_catalog:
            for product in product_category.products:
                product.product_catalog = product_category.product
                all_products.append(product)
        self._products_selector_state.items = all_products
        self._load_history(self.item.id)
        self.in_process = False

    @rx.event
    def on_click_edit(self):
        if self.item is None:
            return
        return rx.redirect(routes.MOVEMENT_ISSUES_EDIT_ID + str(self.item.id))

    @rx.var
    def item_status(self) -> str:
        return movements_status_list[self.item.movement.status]

    @rx.var
    def current_is_canceled(self) -> bool:
        return self.item is not None and self.item.movement.status == MovementsStatus.CANCELED

    @rx.var
    def cancel_conflict_rows(self) -> List[Tuple[str, str, str, str, str]]:
        return [
            (
                str(m.id),
                movements_type_list.get(m.type, "—"),
                m.date,
                movements_status_list[m.status],
                routes.movement_view_url(m.type, m.id),
            )
            for m in self.cancel_conflict_movements
        ]

    @rx.event
    def set_cancel_conflict_dialog_open(self, value: bool):
        self.is_cancel_conflict_dialog_open = value

    @rx.event
    def on_click_cancel(self):
        if not self.has_permission(Action.ISSUES_DELETE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None or self._products_selector_state is None:
            yield rx.toast.error("Не обрано запис для скасування!")
            return
        if self.item.movement.status == MovementsStatus.CANCELED:
            yield rx.toast.error("Видачу вже скасовано!")
            return

        list_id_products: List[int] = [p.id for p in self._products_selector_state.items]

        related_movements = MovementDAO.get_with_products_from_id(list_id_products, self.item.id)
        if related_movements:
            self.cancel_conflict_movements = related_movements
            self.is_cancel_conflict_dialog_open = True
            yield rx.toast.error("Скасування неможливе: товар бере участь у пізніших рухах!")
            return

        flag, text = MovementDAO.cancel_movement(self.item.id, self.user.login, reason=self.cancel_reason)
        if not flag:
            yield rx.toast.error(text)
            return

        ProductDAO.undelete_list(list_id_products)
        MovementDAO.restore_products_to_previous_location(list_id_products, self.item.id)
        RequestDAO.revert_completion_by_movement(self.item.id, self.user.login)
        yield rx.toast.success("Видачу скасовано!")
        yield ListIssueState.on_load()
        yield rx.redirect(f"{routes.MOVEMENT_ISSUES_VIEW_ID}{self.item.id}")


class AddIssueState(LookupCreatorsMixin, AppState):
    item: Issue = Issue(
        id_recipient=-1,
        movement=Movement(
            id_incoming_storage=-1,
            id_incoming_owner=-1,
            id_destination_storage=-1,
            id_destination_owner=-1,
            date=now_local().date().__str__(),
            comment="",
            status=MovementsStatus.CREATED,
            type=MovementsType.ISSUE,
            total_cost=0.0,
            products_catalog=[],
        ),
    )

    list_incoming_storages: List[Tuple[str, str]] = []
    list_destination_storages: List[Tuple[str, str]] = []
    list_owners: List[Tuple[str, str]] = []
    list_workers: List[Tuple[str, str]] = []

    search_name_destination_storage: str = ""

    is_open_product_dialog: bool = False

    _products_selector_state: Optional[ProductsMovementListState] = None

    list_requests: List[Tuple[str, str]] = []
    selected_request_id: str = ""
    request_positions: List[Tuple[str, str]] = []

    def _load_incoming_storages(self):
        self.list_incoming_storages = [
            (item.title, str(item.id))
            for item in StorageDAO.get_all_by_type(StorageType.WAREHOUSE)
        ]

    def _load_destination_storages(self):
        destinations = StorageDAO.get_all_by_type(
            StorageType.TECHNICAL_SITE
        ) + StorageDAO.get_all_by_type(StorageType.DEPARTMENT)
        self.list_destination_storages = [
            (item.title, str(item.id))
            for item in destinations
            if self.search_name_destination_storage == ""
            or self.search_name_destination_storage.lower() in item.title.lower()
        ]

    def _load_owners(self):
        self.list_owners = [(item.title, str(item.id)) for item in OwnerDAO.get_all()]

    def _load_workers(self):
        self.list_workers = [(item.fio, str(item.id)) for item in WorkerDAO.get_all()]

    def _load_requests(self):
        self.list_requests = [
            (
                f"№{r.id} від {r.date}"
                + (f" — {r.responsible.fio}" if r.responsible is not None else ""),
                str(r.id),
            )
            for r in RequestDAO.get_open_by_type(MovementsType.ISSUE)
        ]

    @rx.event
    async def on_load(self):
        if not self.has_permission(Action.ISSUES_CREATE):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return

        self.item = Issue(
            id_recipient=-1,
            movement=Movement(
                id_incoming_storage=-1,
                id_incoming_owner=-1,
                id_destination_storage=-1,
                id_destination_owner=-1,
                date=now_local().date().__str__(),
                comment="",
                status=MovementsStatus.CREATED,
                type=MovementsType.ISSUE,
                total_cost=0.0,
                products_catalog=[],
            ),
        )
        self.is_open_product_dialog = False
        self.selected_request_id = ""
        self.request_positions = []

        self._load_incoming_storages()
        self._load_destination_storages()
        self._load_owners()
        self._load_workers()
        self._load_requests()

        self._products_selector_state = await self.get_state(ProductsMovementListState)
        await self._products_selector_state.on_load()
        self._products_selector_state.set_view_mode(False)
        self._products_selector_state.set_require_serial(True)

        default_storage = StorageDAO.get_default_id(StorageType.WAREHOUSE)
        if default_storage is not None:
            self.item.movement.id_incoming_storage = default_storage
            self._products_selector_state.filter_by_storage = default_storage
        default_owner = OwnerDAO.get_default_id()
        if default_owner is not None:
            self.item.movement.id_incoming_owner = default_owner
            self.item.movement.id_destination_owner = default_owner
            self._products_selector_state.filter_by_owner = default_owner
        default_worker = WorkerDAO.get_default_id()
        if default_worker is not None:
            self.item.id_recipient = default_worker

    @rx.var
    def has_requests(self) -> bool:
        return len(self.list_requests) > 0

    @rx.var
    def has_request_positions(self) -> bool:
        return len(self.request_positions) > 0

    @rx.event
    def on_change_request(self, value: str):
        self.selected_request_id = value
        if value == "":
            self.request_positions = []
            return
        request = RequestDAO.get_by_id_with_relationships(int(value))
        if request is None:
            self.selected_request_id = ""
            yield rx.toast.error("Заявку не знайдено!")
            return
        if request.id_responsible is not None:
            self.item.id_recipient = request.id_responsible
        if request.id_destination_storage is not None:
            self.item.movement.id_destination_storage = request.id_destination_storage
        self.request_positions = [
            (
                pc.product.title,
                format_request_qty(pc.count, pc.part_amount, pc.product.unit),
            )
            for pc in request.products_catalog
        ]

    @rx.var
    def id_incoming_storage(self) -> str:
        return str(self.item.movement.id_incoming_storage)

    @rx.var
    def id_incoming_owner(self) -> str:
        return str(self.item.movement.id_incoming_owner)

    @rx.var
    def id_destination_storage(self) -> str:
        return str(self.item.movement.id_destination_storage)

    @rx.var
    def id_destination_owner(self) -> str:
        return str(self.item.movement.id_destination_owner)

    @rx.var
    def id_recipient(self) -> str:
        return str(self.item.id_recipient)

    @rx.var
    def status(self) -> str:
        return movements_status_list[self.item.movement.status]

    @rx.event
    def on_change_search_name_destination_storage(self, value: str):
        self.search_name_destination_storage = value
        self._load_destination_storages()

    @rx.event
    def on_click_search_name_destination_storage(self):
        self._load_destination_storages()

    @rx.event
    def on_change_id_incoming_storage(self, value: str):
        self.item.movement.id_incoming_storage = int(value)
        self._products_selector_state.filter_by_storage = (
            int(self.item.movement.id_incoming_storage)
            if self.item.movement.id_incoming_storage != ""
            else -1
        )
        self._products_selector_state.items = []

    @rx.event
    def on_change_id_incoming_owner(self, value: str):
        self.item.movement.id_incoming_owner = int(value)
        self.item.movement.id_destination_owner = int(value)
        self._products_selector_state.filter_by_owner = (
            int(self.item.movement.id_incoming_owner)
            if self.item.movement.id_incoming_owner != ""
            else -1
        )
        self._products_selector_state.items = []

    @rx.event
    def on_change_id_destination_storage(self, value: str):
        self.item.movement.id_destination_storage = int(value)

    @rx.event
    def on_change_id_recipient(self, value: str):
        self.item.id_recipient = int(value)

    @rx.event
    def on_change_status(self, value: str):
        status = None
        for index, status_text in enumerate(movements_status_list):
            if status_text == value:
                status = index
                break
        if status is not None:
            self.item.movement.status = status

    @rx.event
    def on_change_date(self, value: str):
        self.item.movement.date = value

    @rx.event
    def on_change_comment(self, value: str):
        self.item.movement.comment = value

    @rx.event
    def on_close_product_dialog(self):
        self.is_open_product_dialog = False

    @rx.var
    def item_status(self) -> str:
        return movements_status_list[self.item.movement.status]

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list

    @rx.var
    def editable_statuses(self) -> List[str]:
        return [
            status
            for index, status in enumerate(movements_status_list)
            if index != MovementsStatus.CANCELED
        ]

    def _after_create_storage(self, new_id: int):
        if self.st_slot == "incoming":
            self._load_incoming_storages()
            self.item.movement.id_incoming_storage = new_id
            if self._products_selector_state is not None:
                self._products_selector_state.filter_by_storage = new_id
                self._products_selector_state.items = []
        else:
            self._load_destination_storages()
            self.item.movement.id_destination_storage = new_id

    def _after_create_owner(self, new_id: int):
        self._load_owners()
        self.item.movement.id_incoming_owner = new_id
        self.item.movement.id_destination_owner = new_id
        if self._products_selector_state is not None:
            self._products_selector_state.filter_by_owner = new_id
            self._products_selector_state.items = []

    def _after_create_worker(self, new_id: int):
        self._load_workers()
        self.item.id_recipient = new_id

    async def _reset_for_continue(self):
        m = self.item.movement
        keep = dict(
            date=m.date,
            id_incoming_storage=m.id_incoming_storage,
            id_incoming_owner=m.id_incoming_owner,
            id_destination_storage=m.id_destination_storage,
            id_destination_owner=m.id_destination_owner,
            id_recipient=self.item.id_recipient,
            status=m.status,
        )
        self.item = Issue(
            id_recipient=keep["id_recipient"],
            movement=Movement(
                id_incoming_storage=keep["id_incoming_storage"],
                id_incoming_owner=keep["id_incoming_owner"],
                id_destination_storage=keep["id_destination_storage"],
                id_destination_owner=keep["id_destination_owner"],
                date=keep["date"],
                comment="",
                status=keep["status"],
                type=MovementsType.ISSUE,
                total_cost=0.0,
                products_catalog=[],
            ),
        )
        self.selected_request_id = ""
        self.request_positions = []

        self._load_incoming_storages()
        self._load_destination_storages()
        self._load_owners()
        self._load_workers()
        self._load_requests()

        await self._products_selector_state.on_load()
        self._products_selector_state.set_view_mode(False)
        self._products_selector_state.set_require_serial(True)
        if keep["id_incoming_storage"] != -1:
            self._products_selector_state.filter_by_storage = keep["id_incoming_storage"]
        if keep["id_incoming_owner"] != -1:
            self._products_selector_state.filter_by_owner = keep["id_incoming_owner"]

    @rx.event
    async def add_one(self, keep: bool = False):
        if not self.has_permission(Action.ISSUES_CREATE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item.movement.id_incoming_storage == -1:
            yield rx.toast.error("Не обрано склад відправлення!")
            return
        if self.item.movement.id_incoming_owner == -1:
            yield rx.toast.error("Не обрано власника відправлення!")
            return
        if self.item.id_recipient == -1:
            yield rx.toast.error("Не обрано отримувача!")
            return
        if self._products_selector_state is None or len(self._products_selector_state.items) == 0:
            yield rx.toast.error("Список ТМЦ для видачі порожній!")
            return
        if self.item.movement.id_destination_storage == -1:
            yield rx.toast.error("Не обрано майданчик призначення!")
            return

        if not StorageDAO.is_type(self.item.movement.id_incoming_storage, StorageType.WAREHOUSE):
            yield rx.toast.error("Видача можлива лише зі складу!")
            return
        if not StorageDAO.is_type(
            self.item.movement.id_destination_storage,
            (StorageType.TECHNICAL_SITE, StorageType.DEPARTMENT),
        ):
            yield rx.toast.error("Видача можлива лише на площадку або відділ!")
            return

        self.item.movement.id_user = self.user.login

        ok, msg, products_list = self._products_selector_state.resolve_movement_products()
        if not ok:
            yield rx.toast.error(msg)
            return

        products_catalog: List[ProductCatalog] = []
        movement_products_catalog: List[MovementProductsCatalog] = []

        for product in products_list:
            if product.product_catalog not in products_catalog:
                products_catalog.append(product.product_catalog)

        for product_catalog in products_catalog:
            movement_product_catalog: MovementProductsCatalog = MovementProductsCatalog(
                id_movement=self.item.movement.id,
                id_product_catalog=product_catalog.id,
                count=0,
                products=[],
            )
            for product in products_list:
                if product.id_product_catalog == product_catalog.id:
                    movement_product_catalog.products.append(product)
                    movement_product_catalog.count += 1
            movement_products_catalog.append(movement_product_catalog)

        self.item.movement.products_catalog = movement_products_catalog

        list_id_products: List[int] = [p.id for p in products_list]
        flag, text, id = IssueDAO.add_one(self.item, self.user.login)
        if flag:
            serials = {
                p.id: p.serial_number
                for p in products_list
                if p.product_catalog is not None and p.product_catalog.uniq
            }
            ProductDAO.update_serial_numbers(serials)
            ProductDAO.apply_issue_relocation(
                products_list,
                int(self.item.movement.id_destination_owner),
                int(self.item.movement.id_destination_storage),
            )
            if self.selected_request_id != "":
                RequestDAO.mark_completed(int(self.selected_request_id), id, self.user.login)
            if keep:
                await self._reset_for_continue()
                yield rx.toast.success(text)
                return
            yield rx.toast.success(text)
            yield ListIssueState.on_load()
            yield rx.redirect(f"{routes.MOVEMENT_ISSUES_VIEW_ID}{id}", replace=True)
            return
        yield rx.toast.error(text)


class EditIssueState(FullEditMixin, AppState):
    MOVEMENT_TYPE = MovementsType.ISSUE

    item: Optional[Issue] = None
    in_process: bool = True
    # id заявки, за якою сформовано рух (інформаційно — заявку не чіпаємо).
    source_request_id: str = ""

    list_incoming_storages: List[Tuple[str, str]] = []
    list_destination_storages: List[Tuple[str, str]] = []
    list_owners: List[Tuple[str, str]] = []
    list_workers: List[Tuple[str, str]] = []

    search_name_destination_storage: str = ""

    is_open_product_dialog: bool = False

    _products_selector_state: Optional[ProductsMovementListState] = None

    def _load_incoming_storages(self):
        self.list_incoming_storages = [
            (item.title, str(item.id))
            for item in StorageDAO.get_all_by_type(StorageType.WAREHOUSE)
        ]

    def _load_destination_storages(self):
        destinations = StorageDAO.get_all_by_type(
            StorageType.TECHNICAL_SITE
        ) + StorageDAO.get_all_by_type(StorageType.DEPARTMENT)
        self.list_destination_storages = [
            (item.title, str(item.id))
            for item in destinations
            if self.search_name_destination_storage == ""
            or self.search_name_destination_storage.lower() in item.title.lower()
        ]

    def _load_owners(self):
        self.list_owners = [(item.title, str(item.id)) for item in OwnerDAO.get_all()]

    def _load_workers(self):
        self.list_workers = [(item.fio, str(item.id)) for item in WorkerDAO.get_all()]

    @rx.event
    async def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(Action.ISSUES_EDIT):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return

        self.in_process = True
        self.is_open_product_dialog = False
        self._load_incoming_storages()
        self._load_destination_storages()
        self._load_owners()
        self._load_workers()

        self.item = IssueDAO.get_by_id_with_all_relationship(int(id))
        if self.item is None:
            self.in_process = False
            yield rx.redirect(routes.MOVEMENT_ISSUES)
            yield rx.toast.error("Запис не знайдено!")
            return

        self._load_editability(self.item.id)
        request_id = RequestDAO.get_id_by_movement(self.item.id)
        self.source_request_id = str(request_id) if request_id is not None else ""

        self._products_selector_state = await self.get_state(ProductsMovementListState)
        await self._products_selector_state.on_load()
        self._products_selector_state.set_view_mode(not self.can_edit_full)
        self._products_selector_state.set_require_serial(True)
        self._products_selector_state.filter_by_storage = self.item.movement.id_incoming_storage
        self._products_selector_state.filter_by_owner = self.item.movement.id_incoming_owner

        all_products: List[Product] = []
        for product_category in self.item.movement.products_catalog:
            for product in product_category.products:
                product.product_catalog = product_category.product
                all_products.append(product)
        self._products_selector_state.prefill_for_edit(all_products)
        self.in_process = False

    @rx.var
    def has_source_request(self) -> bool:
        return self.source_request_id != ""

    @rx.var
    def id_incoming_storage(self) -> str:
        return str(self.item.movement.id_incoming_storage) if self.item is not None else ""

    @rx.var
    def id_incoming_owner(self) -> str:
        return str(self.item.movement.id_incoming_owner) if self.item is not None else ""

    @rx.var
    def id_destination_storage(self) -> str:
        return str(self.item.movement.id_destination_storage) if self.item is not None else ""

    @rx.var
    def id_destination_owner(self) -> str:
        return str(self.item.movement.id_destination_owner) if self.item is not None else ""

    @rx.var
    def id_recipient(self) -> str:
        return str(self.item.id_recipient) if self.item is not None else ""

    @rx.var
    def status(self) -> str:
        return movements_status_list[self.item.movement.status] if self.item is not None else ""

    @rx.var
    def item_status(self) -> str:
        return movements_status_list[self.item.movement.status] if self.item is not None else ""

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list

    @rx.var
    def editable_statuses(self) -> List[str]:
        return [
            status
            for index, status in enumerate(movements_status_list)
            if index != MovementsStatus.CANCELED
        ]

    @rx.event
    def on_change_search_name_destination_storage(self, value: str):
        self.search_name_destination_storage = value
        self._load_destination_storages()

    @rx.event
    def on_click_search_name_destination_storage(self):
        self._load_destination_storages()

    @rx.event
    def on_change_id_incoming_storage(self, value: str):
        if self.item is None or not self.can_edit_full or not value.lstrip("-").isdigit():
            return
        self.item.movement.id_incoming_storage = int(value)
        if self._products_selector_state is not None:
            self._products_selector_state.filter_by_storage = int(value)
            self._products_selector_state.items = []
        yield rx.toast.warning("Перелік ТМЦ очищено — оберіть одиниці на новому складі!")

    @rx.event
    def on_change_id_incoming_owner(self, value: str):
        if self.item is None or not self.can_edit_full or not value.lstrip("-").isdigit():
            return
        self.item.movement.id_incoming_owner = int(value)
        self.item.movement.id_destination_owner = int(value)
        if self._products_selector_state is not None:
            self._products_selector_state.filter_by_owner = int(value)
            self._products_selector_state.items = []
        yield rx.toast.warning("Перелік ТМЦ очищено — оберіть одиниці нового власника!")

    @rx.event
    def on_change_id_destination_storage(self, value: str):
        if self.item is not None and self.can_edit_full and value.lstrip("-").isdigit():
            self.item.movement.id_destination_storage = int(value)

    @rx.event
    def on_change_id_recipient(self, value: str):
        if self.item is not None and self.can_edit_full and value.lstrip("-").isdigit():
            self.item.id_recipient = int(value)

    @rx.event
    def on_change_status(self, value: str):
        if self.item is None:
            return
        for index, status_text in enumerate(movements_status_list):
            if status_text == value:
                self.item.movement.status = index
                return

    @rx.event
    def on_change_date(self, value: str):
        if self.item is not None and self.can_edit_full:
            self.item.movement.date = value

    @rx.event
    def on_change_comment(self, value: str):
        if self.item is not None:
            self.item.movement.comment = value

    @rx.event
    def on_close_product_dialog(self):
        self.is_open_product_dialog = False

    @rx.event
    def edit_one(self):
        if not self.has_permission(Action.ISSUES_EDIT):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None:
            yield rx.toast.error("Запис не завантажено!")
            return
        if self.item.movement.id_incoming_storage == -1:
            yield rx.toast.error("Не обрано склад відправлення!")
            return
        if self.item.movement.id_incoming_owner == -1:
            yield rx.toast.error("Не обрано власника відправлення!")
            return
        if self.item.id_recipient == -1:
            yield rx.toast.error("Не обрано отримувача!")
            return
        if self._products_selector_state is None or len(self._products_selector_state.items) == 0:
            yield rx.toast.error("Список ТМЦ для видачі порожній!")
            return
        if self.item.movement.status == MovementsStatus.CANCELED:
            yield rx.toast.error("Скасування виконується кнопкою «Скасувати», а не через редагування!")
            return

        self.item.movement.id_user = self.user.login

        if self.can_edit_full:
            if self.item.movement.id_destination_storage == -1:
                yield rx.toast.error("Не обрано місце призначення!")
                return
            if not StorageDAO.is_type(self.item.movement.id_incoming_storage, StorageType.WAREHOUSE):
                yield rx.toast.error("Видача можлива лише зі складу!")
                return
            if not StorageDAO.is_type(
                self.item.movement.id_destination_storage,
                (StorageType.TECHNICAL_SITE, StorageType.DEPARTMENT),
            ):
                yield rx.toast.error("Видача можлива лише на площадку або у відділ!")
                return
            flag, text, plan = self._products_selector_state.collect_unit_plan()
            if not flag:
                yield rx.toast.error(text)
                return
            try:
                MovementEditService().save_full(
                    FullEditPayload(
                        movement_id=self.item.id,
                        movement_type=MovementsType.ISSUE,
                        reason=self.edit_reason,
                        header={
                            "date": self.item.movement.date,
                            "id_incoming_storage": self.item.movement.id_incoming_storage,
                            "id_incoming_owner": self.item.movement.id_incoming_owner,
                            "id_destination_storage": self.item.movement.id_destination_storage,
                            "id_destination_owner": self.item.movement.id_destination_owner,
                            "status": self.item.movement.status,
                            "comment": self.item.movement.comment,
                        },
                        child={"id_recipient": self.item.id_recipient},
                        unit_plan=plan,
                        serials=self._products_selector_state.collect_serials(),
                    ),
                    self.user.login,
                )
            except ServiceError as e:
                yield rx.toast.error(str(e))
                return
            yield rx.toast.success("Видачу змінено!")
            yield ListIssueState.on_load()
            yield rx.redirect(f"{routes.MOVEMENT_ISSUES_VIEW_ID}{self.item.id}", replace=True)
            return

        flag, text, id = IssueDAO.edit_one(self.item, self.user.login)
        if flag:
            yield rx.toast.success(text)
            yield ListIssueState.on_load()
            yield rx.redirect(f"{routes.MOVEMENT_ISSUES_VIEW_ID}{id}", replace=True)
            return
        yield rx.toast.error(text)
