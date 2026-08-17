from typing import Dict, List, Optional, Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.dao_legacy import (
    MovementDAO,
    OwnerDAO,
    ProductDAO,
    RequestDAO,
    SaleDAO,
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
    sale_line_cost,
)
from TrifleSklad.models import Movement, Product, Sale
from TrifleSklad.movement.inline_creators import LookupCreatorsMixin
from TrifleSklad.movement.list_mixin import ALL, MovementListFilterMixin
from TrifleSklad.movement.products.backend import ProductsMovementListState
from TrifleSklad.services.errors import ServiceError
from TrifleSklad.services.movement_edit import FullEditPayload, MovementEditService
from TrifleSklad.states.app import AppState
from TrifleSklad.states.audit_mixin import AuditHistoryMixin
from TrifleSklad.states.movement_edit_mixin import FullEditMixin
from TrifleSklad.utils.clock import now_local


class ListSaleState(MovementListFilterMixin, AppState):
    items: List[Sale] = []
    in_progress: bool = True

    filter_responsible: str = ALL
    list_responsibles: List[Tuple[str, str]] = []

    def _reload(self):
        self._all_pages, self.items = SaleDAO.get_paginated(
            self._current_page,
            self._limit,
            self._date_from_eff(),
            self._date_to_eff(),
            self.selected_statuses,
            incoming_storage=self.filter_incoming_storage,
            incoming_owner=self.filter_incoming_owner,
            responsible=self.filter_responsible,
        )

    @rx.var
    def has_active_filters(self) -> bool:
        return bool(
            self.filter_date_enabled
            or self.selected_statuses
            or self.filter_incoming_storage != ALL
            or self.filter_incoming_owner != ALL
            or self.filter_responsible != ALL
        )

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def get_items(self) -> List[Tuple[int, Sale]]:
        return [(index, item) for index, item in enumerate(self.items)]

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list

    @rx.event
    def on_load(self):
        if not self.has_permission(Action.SALES_LIST):
            yield rx.redirect(routes.WELCOME)
            yield rx.toast.error("У Вас немає дозволу на перегляд цієї сторінки!")
            return
        self.in_progress = True
        self._reset_list_state()
        self.filter_responsible = ALL
        self.list_responsibles = [(w.fio, str(w.id)) for w in WorkerDAO.get_all()]
        self._reload()
        self.in_progress = False

    @rx.event
    def on_click_add(self):
        return rx.redirect(routes.MOVEMENT_SALES_ADD)

    @rx.event
    def on_change_filter_responsible(self, value: str):
        self.filter_responsible = value

    @rx.event
    def reset_filters(self):
        today = now_local().date().isoformat()
        self.filter_date_enabled = False
        self.filter_date_from = today
        self.filter_date_to = today
        self.selected_statuses = []
        self.filter_incoming_storage = ALL
        self.filter_destination_storage = ALL
        self.filter_incoming_owner = ALL
        self.filter_destination_owner = ALL
        self.filter_responsible = ALL
        self._current_page = 1
        self._reload()


class ViewSaleState(AuditHistoryMixin, AppState):
    HISTORY_TABLE = "sales"
    HISTORY_ACTION = Action.SALES_HISTORY
    HISTORY_DETAIL_ACTION = Action.SALES_HISTORY_DETAIL

    item: Optional[Sale] = None
    in_process: bool = True

    _products_movement_list_state: Optional[ProductsMovementListState] = None

    cancel_conflict_movements: List[Movement] = []
    is_cancel_conflict_dialog_open: bool = False

    expanded_positions: Dict[int, bool] = {}

    @rx.var
    def item_status(self) -> str:
        return (
            movements_status_list[self.item.movement.status]
            if self.item is not None
            else ""
        )

    @rx.var
    def client_info(self) -> str:
        return (
            self.item.client_info
            if self.item is not None and self.item.client_info is not None
            else ""
        )

    @rx.var
    def current_is_canceled(self) -> bool:
        return (
            self.item is not None
            and self.item.movement.status == MovementsStatus.CANCELED
        )

    @rx.var
    def positions_grouped(
        self,
    ) -> List[Tuple[int, str, int, float, float, List[Tuple[int, str, str]]]]:
        if self.item is None:
            return []
        result: List[Tuple[int, str, int, float, float, List[Tuple[int, str, str]]]] = []
        for index, pc in enumerate(self.item.movement.products_catalog):
            units: List[Tuple[int, str, str]] = []
            line_units: List[Tuple[int, bool, int]] = []
            for unit in pc.products:
                catalog = unit.product_catalog
                serial = (
                    unit.serial_number
                    if (catalog is not None and catalog.uniq and unit.serial_number)
                    else "—"
                )
                remain = (
                    str(unit.count)
                    if (catalog is not None and catalog.divisible)
                    else "—"
                )
                units.append((unit.id, serial, remain))
                line_units.append(
                    (
                        unit.count or 0,
                        catalog.divisible if catalog is not None else False,
                        catalog.capacity if catalog is not None else 0,
                    )
                )
            result.append(
                (
                    index,
                    pc.product.title,
                    pc.count,
                    pc.price,
                    sale_line_cost(pc.price, line_units),
                    units,
                )
            )
        return result

    @rx.var
    def total_cost(self) -> float:
        return (
            self.item.movement.total_cost
            if self.item is not None and self.item.movement.total_cost is not None
            else 0.0
        )

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
    def toggle_position(self, index: int):
        self.expanded_positions[index] = not self.expanded_positions.get(index, False)

    @rx.event
    def on_click_edit(self):
        if self.item is None:
            return
        return rx.redirect(routes.MOVEMENT_SALES_EDIT_ID + str(self.item.id))

    @rx.event
    async def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(Action.SALES_VIEW):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        self.in_process = True
        self.expanded_positions = {}
        self.item = SaleDAO.get_by_id_with_all_relationship(int(id))
        if self.item is None:
            self.in_process = False
            yield rx.redirect(routes.MOVEMENT_SALES)
            yield rx.toast.error("Запис не знайдено!")
            return

        self._products_movement_list_state = await self.get_state(ProductsMovementListState)
        await self._products_movement_list_state.on_load()
        self._products_movement_list_state.set_view_mode(True)

        all_products: List[Product] = []
        for product_category in self.item.movement.products_catalog:
            for product in product_category.products:
                product.product_catalog = product_category.product
                all_products.append(product)
        self._products_movement_list_state.items = all_products
        self._load_history(self.item.id)
        self.in_process = False

    @rx.event
    def on_click_cancel(self):
        if not self.has_permission(Action.SALES_DELETE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None or self._products_movement_list_state is None:
            yield rx.toast.error("Не обрано запис для скасування!")
            return
        if self.item.movement.status == MovementsStatus.CANCELED:
            yield rx.toast.error("Продаж вже скасовано!")
            return

        list_id_products: List[int] = [p.id for p in self._products_movement_list_state.items]

        related_movements = MovementDAO.get_with_products_from_id(list_id_products, self.item.id)
        if any(m.id != self.item.id for m in related_movements):
            self.cancel_conflict_movements = related_movements
            self.is_cancel_conflict_dialog_open = True
            yield rx.toast.error("Скасування неможливе: товар бере участь у пізніших рухах!")
            return

        flag, text = MovementDAO.cancel_movement(self.item.id, self.user.login)
        if not flag:
            yield rx.toast.error(text)
            return

        ProductDAO.undelete_list(list_id_products)
        RequestDAO.revert_completion_by_movement(self.item.id, self.user.login)
        yield rx.toast.success("Продаж скасовано!")
        yield ListSaleState.on_load()
        yield rx.redirect(f"{routes.MOVEMENT_SALES_VIEW_ID}{self.item.id}")


class AddSaleState(LookupCreatorsMixin, AppState):
    current_date: str = ""

    id_incoming_storage: str = ""
    id_incoming_owner: str = ""
    id_responsible: str = ""
    search_name_incoming_storage: str = ""
    search_responsible: str = ""
    status: str = ""
    comment: str = ""
    client_info: str = ""

    list_storages: List[Tuple[str, str]] = []
    list_owners: List[Tuple[str, str]] = []
    list_workers: List[Tuple[str, str]] = []

    list_requests: List[Tuple[str, str]] = []
    selected_request_id: str = ""
    request_positions: List[Tuple[str, str]] = []

    _products_movement_list_state: Optional[ProductsMovementListState] = None

    def _load_list_storages(self):
        self.list_storages = [
            (item.title, str(item.id))
            for item in StorageDAO.get_all_by_type(StorageType.WAREHOUSE)
            if self.search_name_incoming_storage == ""
            or self.search_name_incoming_storage.lower() in item.title.lower()
        ]

    def _load_requests(self):
        self.list_requests = [
            (f"№{r.id} від {r.date}", str(r.id))
            for r in RequestDAO.get_open_by_type(MovementsType.SALE)
        ]

    def _load_list_owners(self):
        self.list_owners = [(item.title, str(item.id)) for item in OwnerDAO.get_all()]

    def _load_list_workers(self):
        self.list_workers = [(item.fio, str(item.id)) for item in WorkerDAO.get_all()]

    def _status_index(self) -> int:
        for index, status_text in enumerate(movements_status_list):
            if status_text == self.status:
                return index
        return MovementsStatus.CREATED

    @rx.var
    def filtered_list_workers(self) -> List[Tuple[str, str]]:
        term = self.search_responsible.strip().lower()
        if term == "":
            return self.list_workers
        return [w for w in self.list_workers if term in w[0].lower()]

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
    def on_change_search_responsible(self, value: str):
        self.search_responsible = value

    @rx.var
    def has_requests(self) -> bool:
        return len(self.list_requests) > 0

    @rx.var
    def has_request_positions(self) -> bool:
        return len(self.request_positions) > 0

    def _after_create_storage(self, new_id: int):
        self._load_list_storages()
        self.id_incoming_storage = str(new_id)
        if self._products_movement_list_state is not None:
            self._products_movement_list_state.filter_by_storage = new_id
            self._products_movement_list_state.items = []

    def _after_create_owner(self, new_id: int):
        self._load_list_owners()
        self.id_incoming_owner = str(new_id)
        if self._products_movement_list_state is not None:
            self._products_movement_list_state.filter_by_owner = new_id
            self._products_movement_list_state.items = []

    def _after_create_worker(self, new_id: int):
        self._load_list_workers()
        self.id_responsible = str(new_id)

    async def _reset_for_continue(self):
        keep = dict(
            current_date=self.current_date,
            id_incoming_storage=self.id_incoming_storage,
            id_incoming_owner=self.id_incoming_owner,
            id_responsible=self.id_responsible,
            status=self.status,
        )
        self.search_name_incoming_storage = ""
        self.search_responsible = ""
        self.comment = ""
        self.client_info = ""
        self.selected_request_id = ""
        self.request_positions = []

        self.id_incoming_storage = keep["id_incoming_storage"]
        self.id_incoming_owner = keep["id_incoming_owner"]
        self.id_responsible = keep["id_responsible"]
        self.current_date = keep["current_date"]
        self.status = keep["status"]

        self._load_list_storages()
        self._load_list_owners()
        self._load_list_workers()
        self._load_requests()

        self._products_movement_list_state.items = []
        await self._products_movement_list_state.on_load()
        self._products_movement_list_state.set_view_mode(False)
        self._products_movement_list_state.set_require_price(True)
        self._products_movement_list_state.set_require_serial(True)
        if keep["id_incoming_storage"] != "":
            self._products_movement_list_state.filter_by_storage = int(keep["id_incoming_storage"])
        if keep["id_incoming_owner"] != "":
            self._products_movement_list_state.filter_by_owner = int(keep["id_incoming_owner"])

    @rx.event
    async def on_load(self):
        if not self.has_permission(Action.SALES_CREATE):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return

        self.current_date = now_local().date().__str__()
        self.id_incoming_storage = ""
        self.id_incoming_owner = ""
        self.id_responsible = ""
        self.search_name_incoming_storage = ""
        self.search_responsible = ""
        self.status = ""
        self.comment = ""
        self.client_info = ""
        self.selected_request_id = ""
        self.request_positions = []

        self._load_list_storages()
        self._load_list_owners()
        self._load_list_workers()
        self._load_requests()

        self._products_movement_list_state = await self.get_state(ProductsMovementListState)
        self._products_movement_list_state.items = []
        await self._products_movement_list_state.on_load()
        self._products_movement_list_state.set_view_mode(False)
        self._products_movement_list_state.set_require_price(True)
        self._products_movement_list_state.set_require_serial(True)

        default_storage = StorageDAO.get_default_id(StorageType.WAREHOUSE)
        if default_storage is not None:
            self.id_incoming_storage = str(default_storage)
            self._products_movement_list_state.filter_by_storage = default_storage
        default_owner = OwnerDAO.get_default_id()
        if default_owner is not None:
            self.id_incoming_owner = str(default_owner)
            self._products_movement_list_state.filter_by_owner = default_owner
        default_worker = WorkerDAO.get_default_id()
        if default_worker is not None:
            self.id_responsible = str(default_worker)

    @rx.event
    def on_change_id_incoming_storage(self, value: str):
        self.id_incoming_storage = value
        if self._products_movement_list_state is not None:
            self._products_movement_list_state.filter_by_storage = (
                int(value) if value != "" else -1
            )
            self._products_movement_list_state.items = []

    @rx.event
    def on_change_id_incoming_owner(self, value: str):
        self.id_incoming_owner = value
        if self._products_movement_list_state is not None:
            self._products_movement_list_state.filter_by_owner = (
                int(value) if value != "" else -1
            )
            self._products_movement_list_state.items = []

    @rx.event
    def on_change_id_responsible(self, value: str):
        self.id_responsible = value

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
        if request.comment:
            self.comment = request.comment
        self.request_positions = [
            (
                pc.product.title,
                format_request_qty(pc.count, pc.part_amount, pc.product.unit),
            )
            for pc in request.products_catalog
        ]

    @rx.event
    def on_change_search_name_incoming_storage(self, value: str):
        self.search_name_incoming_storage = value
        self._load_list_storages()

    @rx.event
    def on_change_status(self, value: str):
        self.status = value

    @rx.event
    def on_change_date(self, value: str):
        self.current_date = value

    @rx.event
    def on_change_comment(self, value: str):
        self.comment = value

    @rx.event
    def on_change_client_info(self, value: str):
        self.client_info = value

    @rx.event
    async def add_one(self, keep: bool = False):
        if not self.has_permission(Action.SALES_CREATE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.id_incoming_storage == "":
            yield rx.toast.error("Не обрано склад!")
            return
        if self.id_incoming_owner == "":
            yield rx.toast.error("Не обрано власника!")
            return
        if self.id_responsible == "":
            yield rx.toast.error("Не обрано відповідального!")
            return
        if (
            self._products_movement_list_state is None
            or len(self._products_movement_list_state.items) == 0
        ):
            yield rx.toast.error("Список товарів для продажу порожній!")
            return

        if not StorageDAO.is_type(int(self.id_incoming_storage), StorageType.WAREHOUSE):
            yield rx.toast.error("Продаж можливий лише зі складу!")
            return

        ok, msg, products_list = self._products_movement_list_state.resolve_movement_products()
        if not ok:
            yield rx.toast.error(msg)
            return

        prices = self._products_movement_list_state.get_prices()
        positions = {p.id_product_catalog for p in products_list}
        for catalog_id in positions:
            if prices.get(catalog_id, 0.0) <= 0:
                yield rx.toast.error("Вкажіть вартість для кожної позиції товару!")
                return

        form_data = {
            "id_responsible": int(self.id_responsible),
            "date": self.current_date,
            "id_incoming_storage": int(self.id_incoming_storage),
            "id_incoming_owner": int(self.id_incoming_owner),
            "status": self._status_index(),
            "comment": self.comment,
            "client_info": self.client_info,
            "movement_products_list": products_list,
            "prices": prices,
            "id_user": self.user.login,
        }

        list_id_products: List[int] = [p.id for p in products_list]
        flag, text, id = SaleDAO.add_one(form_data, self.user.login)
        if flag:
            serials = {p.id: p.serial_number for p in products_list}
            ProductDAO.update_serial_numbers(serials)
            ProductDAO.delete_list(list_id_products)
            if self.selected_request_id != "":
                RequestDAO.mark_completed(int(self.selected_request_id), id, self.user.login)
            if keep:
                await self._reset_for_continue()
                yield rx.toast.success("Продаж проведено!")
                return
            yield rx.toast.success("Продаж проведено!")
            yield ListSaleState.on_load()
            yield rx.redirect(f"{routes.MOVEMENT_SALES_VIEW_ID}{id}", replace=True)
            return
        yield rx.toast.error(text)


class EditSaleState(FullEditMixin, AppState):
    MOVEMENT_TYPE = MovementsType.SALE

    item: Optional[Sale] = None
    in_process: bool = True
    # id заявки, за якою сформовано продаж (інформаційно — заявку не чіпаємо).
    source_request_id: str = ""

    id_incoming_storage: str = ""
    id_incoming_owner: str = ""
    id_responsible: str = ""
    status: str = ""

    list_storages: List[Tuple[str, str]] = []
    list_owners: List[Tuple[str, str]] = []
    list_workers: List[Tuple[str, str]] = []

    _products_movement_list_state: Optional[ProductsMovementListState] = None

    def _load_list_storages(self):
        self.list_storages = [
            (item.title, str(item.id))
            for item in StorageDAO.get_all_by_type(StorageType.WAREHOUSE)
        ]

    def _load_list_owners(self):
        self.list_owners = [(item.title, str(item.id)) for item in OwnerDAO.get_all()]

    def _load_list_workers(self):
        self.list_workers = [(item.fio, str(item.id)) for item in WorkerDAO.get_all()]

    def _status_index(self) -> int:
        for index, status_text in enumerate(movements_status_list):
            if status_text == self.status:
                return index
        return MovementsStatus.CREATED

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list

    @rx.var
    def client_info(self) -> str:
        return (
            self.item.client_info
            if self.item is not None and self.item.client_info is not None
            else ""
        )

    @rx.var
    def editable_statuses(self) -> List[str]:
        return [
            status
            for index, status in enumerate(movements_status_list)
            if index != MovementsStatus.CANCELED
        ]

    @rx.event
    async def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(Action.SALES_EDIT):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return

        self.in_process = True
        self.item = SaleDAO.get_by_id_with_all_relationship(int(id))
        if self.item is None:
            self.in_process = False
            yield rx.redirect(routes.MOVEMENT_SALES)
            yield rx.toast.error("Запис не знайдено!")
            return

        self.id_incoming_storage = str(self.item.movement.id_incoming_storage)
        self.id_incoming_owner = str(self.item.movement.id_incoming_owner)
        self.id_responsible = str(self.item.id_responsible)
        self.status = movements_status_list[self.item.movement.status]

        self._load_list_storages()
        self._load_list_owners()
        self._load_list_workers()

        self._load_editability(self.item.id)
        request_id = RequestDAO.get_id_by_movement(self.item.id)
        self.source_request_id = str(request_id) if request_id is not None else ""

        self._products_movement_list_state = await self.get_state(ProductsMovementListState)
        await self._products_movement_list_state.on_load()
        self._products_movement_list_state.set_view_mode(not self.can_edit_full)
        self._products_movement_list_state.set_require_serial(True)
        self._products_movement_list_state.set_require_price(True)
        self._products_movement_list_state.filter_by_storage = self.item.movement.id_incoming_storage
        self._products_movement_list_state.filter_by_owner = self.item.movement.id_incoming_owner

        all_products: List[Product] = []
        for product_category in self.item.movement.products_catalog:
            for product in product_category.products:
                product.product_catalog = product_category.product
                all_products.append(product)
        # Ціни позицій підтягуємо з руху — інакше в режимі редагування поля
        # порожні, а підсумок порахувався б у нуль.
        self._products_movement_list_state.prefill_for_edit(
            all_products,
            {pc.id_product_catalog: pc.price for pc in self.item.movement.products_catalog},
        )
        self.in_process = False

    @rx.var
    def has_source_request(self) -> bool:
        return self.source_request_id != ""

    @rx.event
    def on_change_id_incoming_storage(self, value: str):
        if not self.can_edit_full:
            return
        self.id_incoming_storage = value
        if self._products_movement_list_state is not None:
            self._products_movement_list_state.filter_by_storage = int(value)
            self._products_movement_list_state.items = []
        yield rx.toast.warning("Перелік ТМЦ очищено — оберіть одиниці на новому складі!")

    @rx.event
    def on_change_id_incoming_owner(self, value: str):
        if not self.can_edit_full:
            return
        self.id_incoming_owner = value
        if self._products_movement_list_state is not None:
            self._products_movement_list_state.filter_by_owner = int(value)
            self._products_movement_list_state.items = []
        yield rx.toast.warning("Перелік ТМЦ очищено — оберіть одиниці нового власника!")

    @rx.event
    def on_change_id_responsible(self, value: str):
        if self.can_edit_full:
            self.id_responsible = value

    @rx.event
    def on_change_status(self, value: str):
        self.status = value

    @rx.event
    def on_change_comment(self, value: str):
        if self.item is not None:
            self.item.movement.comment = value

    @rx.event
    def on_change_client_info(self, value: str):
        if self.item is not None:
            self.item.client_info = value

    @rx.event
    def edit_one(self):
        if not self.has_permission(Action.SALES_EDIT):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None:
            yield rx.toast.error("Запис не завантажено!")
            return
        if self.item.movement.status == MovementsStatus.CANCELED:
            yield rx.toast.error("Продаж вже скасовано!")
            return

        status_index = self._status_index()
        if status_index == MovementsStatus.CANCELED:
            yield rx.toast.error(
                "Скасування виконується кнопкою «Скасувати», а не через редагування!"
            )
            return

        if self.can_edit_full:
            error = self._require_reason()
            if error is not None:
                yield rx.toast.error(error)
                return
            if not StorageDAO.is_type(int(self.id_incoming_storage), StorageType.WAREHOUSE):
                yield rx.toast.error("Продаж можливий лише зі складу!")
                return
            flag, text, plan = self._products_movement_list_state.collect_unit_plan()
            if not flag:
                yield rx.toast.error(text)
                return
            if len(plan) == 0:
                yield rx.toast.error("Список ТМЦ для продажу порожній!")
                return
            prices = self._products_movement_list_state.get_prices()
            for product in self._products_movement_list_state.items:
                catalog_id = product.id_product_catalog
                if prices.get(catalog_id, 0.0) <= 0:
                    yield rx.toast.error("Вкажіть ціну для кожної позиції!")
                    return
            try:
                MovementEditService().save_full(
                    FullEditPayload(
                        movement_id=self.item.id,
                        movement_type=MovementsType.SALE,
                        reason=self.edit_reason,
                        header={
                            "id_incoming_storage": int(self.id_incoming_storage),
                            "id_incoming_owner": int(self.id_incoming_owner),
                            "status": status_index,
                            "comment": self.item.movement.comment,
                        },
                        child={
                            "id_responsible": int(self.id_responsible),
                            "client_info": self.item.client_info,
                        },
                        unit_plan=plan,
                        prices=prices,
                        serials=self._products_movement_list_state.collect_serials(),
                    ),
                    self.user.login,
                )
            except ServiceError as e:
                yield rx.toast.error(str(e))
                return
            yield rx.toast.success("Продаж змінено!")
            yield ListSaleState.on_load()
            yield rx.redirect(f"{routes.MOVEMENT_SALES_VIEW_ID}{self.item.id}", replace=True)
            return

        form_data = {
            "id": self.item.id,
            "status": status_index,
            "comment": self.item.movement.comment,
            "client_info": self.item.client_info,
        }
        flag, text, id = SaleDAO.edit_one(form_data, self.user.login)
        if flag:
            yield rx.toast.success("Продаж змінено!")
            yield ListSaleState.on_load()
            yield rx.redirect(f"{routes.MOVEMENT_SALES_VIEW_ID}{id}", replace=True)
            return
        yield rx.toast.error(text)
