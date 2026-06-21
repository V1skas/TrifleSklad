from datetime import date
from typing import Dict, List, Optional, Tuple

import reflex as rx

import TrifleSklad.routes as routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.dao import (
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
from TrifleSklad.movement.list_mixin import ALL, MovementListFilterMixin
from TrifleSklad.movement.inline_creators import LookupCreatorsMixin
from TrifleSklad.movement.products.backend import ProductsMovementListState
from TrifleSklad.state import AppState


class ListSaleState(MovementListFilterMixin, rx.State):
    items: List[Sale] = []

    # Фільтр, специфічний для продажів: відповідальний.
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

    # Dynamic variables
    # ======================
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
    # ======================

    # Action handlers
    # ======================
    @rx.event
    def on_load(self):
        self._reset_list_state()
        self.filter_responsible = ALL
        self.list_responsibles = [(w.fio, str(w.id)) for w in WorkerDAO.get_all()]
        self._reload()

    @rx.event
    def on_change_filter_responsible(self, value: str):
        self.filter_responsible = value

    @rx.event
    def reset_filters(self):
        today = date.today().isoformat()
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
    # ======================


class ViewSaleState(rx.State):
    item: Optional[Sale] = None

    # Nested form states
    # ======================
    products_movement_list_state: Optional[ProductsMovementListState] = None
    # ======================

    app_state: Optional[AppState] = None

    # Cancel-conflict dialog
    # ======================
    cancel_conflict_movements: List[Movement] = []
    is_cancel_conflict_dialog_open: bool = False
    # ======================

    # Розгорнуті позиції в таблиці (клік по рядку розкриває перелік одиниць).
    # Ключ — індекс позиції в products_catalog.
    # ======================
    expanded_positions: Dict[int, bool] = {}
    # ======================

    # Dynamic variables
    # ======================
    @rx.var
    def item_status(self) -> str:
        return (
            movements_status_list[self.item.movement.status]
            if self.item is not None
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
        # Позиції з вбудованим переліком одиниць для розгортання:
        # (індекс, назва, к-сть, ціна за од., сума по позиції,
        #  одиниці = [(id, серійний номер | '—', залишок | '—')]).
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
    # ======================

    @rx.event
    def set_cancel_conflict_dialog_open(self, value: bool):
        self.is_cancel_conflict_dialog_open = value

    @rx.event
    def toggle_position(self, index: int):
        self.expanded_positions[index] = not self.expanded_positions.get(index, False)

    # Action handlers
    # ======================
    @rx.event
    async def on_load(self, id: int):
        self.expanded_positions = {}
        self.item = SaleDAO.get_by_id_with_all_relationship(id)
        if self.item is None:
            return [
                rx.redirect(routes.MOVEMENT_SALES),
                rx.toast.error("Запис не знайдено!"),
            ]

        self.products_movement_list_state = await self.get_state(
            ProductsMovementListState
        )
        await self.products_movement_list_state.on_load()
        self.products_movement_list_state.set_view_mode(True)

        all_products: List[Product] = []
        for product_category in self.item.movement.products_catalog:
            for product in product_category.products:
                product.product_catalog = product_category.product
                all_products.append(product)
        self.products_movement_list_state.items = all_products

        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
    # ======================


class AddSaleState(LookupCreatorsMixin, rx.State):
    current_date: str = date.today().__str__()

    id_incoming_storage: str = ""
    id_incoming_owner: str = ""
    id_responsible: str = ""
    search_name_incoming_storage: str = ""
    search_responsible: str = ""
    status: str = ""
    comment: str = ""

    list_storages: List[Tuple[str, str]] = []
    list_owners: List[Tuple[str, str]] = []
    list_workers: List[Tuple[str, str]] = []

    # Формування продажу на основі заявки
    list_requests: List[Tuple[str, str]] = []
    selected_request_id: str = ""
    # позиції заявки для відображення (довідково): (назва, опис к-сті)
    request_positions: List[Tuple[str, str]] = []

    products_movement_list_state: Optional[ProductsMovementListState] = None
    app_state: Optional[AppState] = None

    # Backend only
    # ======================
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
    # ======================

    # Dynamic variables
    # ======================
    @rx.var
    def filtered_list_workers(self) -> List[Tuple[str, str]]:
        # Живий пошук відповідального за продаж (підрядок у ПІБ).
        term = self.search_responsible.strip().lower()
        if term == "":
            return self.list_workers
        return [w for w in self.list_workers if term in w[0].lower()]

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list

    @rx.var
    def editable_statuses(self) -> List[str]:
        # «Скасовано» виставляється лише кнопкою «Скасувати» (з поверненням залишків).
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
    # ======================

    # Inline-створення довідників
    # ======================
    def _after_create_storage(self, new_id: int):
        self._load_list_storages()
        self.id_incoming_storage = str(new_id)
        if self.products_movement_list_state is not None:
            self.products_movement_list_state.filter_by_storage = new_id
            self.products_movement_list_state.items = []

    def _after_create_owner(self, new_id: int):
        self._load_list_owners()
        self.id_incoming_owner = str(new_id)
        if self.products_movement_list_state is not None:
            self.products_movement_list_state.filter_by_owner = new_id
            self.products_movement_list_state.items = []

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

        self.products_movement_list_state.items = []
        await self.products_movement_list_state.on_load()
        self.products_movement_list_state.set_view_mode(False)
        self.products_movement_list_state.set_require_price(True)
        self.products_movement_list_state.set_require_serial(True)
        if keep["id_incoming_storage"] != "":
            self.products_movement_list_state.filter_by_storage = int(keep["id_incoming_storage"])
        if keep["id_incoming_owner"] != "":
            self.products_movement_list_state.filter_by_owner = int(keep["id_incoming_owner"])

    # Action handlers
    # ======================
    @rx.event
    async def on_load(self):
        self.current_date = date.today().__str__()
        self.id_incoming_storage = ""
        self.id_incoming_owner = ""
        self.id_responsible = ""
        self.search_name_incoming_storage = ""
        self.search_responsible = ""
        self.status = ""
        self.comment = ""
        self.selected_request_id = ""
        self.request_positions = []

        self._load_list_storages()
        self._load_list_owners()
        self._load_list_workers()
        self._load_requests()

        self.products_movement_list_state = await self.get_state(
            ProductsMovementListState
        )
        self.products_movement_list_state.items = []
        await self.products_movement_list_state.on_load()
        self.products_movement_list_state.set_view_mode(False)
        # Продаж: ціна за позицію обов'язкова; для ТМЦ із серійним номером — s/n.
        self.products_movement_list_state.set_require_price(True)
        self.products_movement_list_state.set_require_serial(True)

        # Передзаповнення значень за замовчуванням (TS-33)
        default_storage = StorageDAO.get_default_id(StorageType.WAREHOUSE)
        if default_storage is not None:
            self.id_incoming_storage = str(default_storage)
            self.products_movement_list_state.filter_by_storage = default_storage
        default_owner = OwnerDAO.get_default_id()
        if default_owner is not None:
            self.id_incoming_owner = str(default_owner)
            self.products_movement_list_state.filter_by_owner = default_owner
        default_worker = WorkerDAO.get_default_id()
        if default_worker is not None:
            self.id_responsible = str(default_worker)

        if self.app_state is None:
            self.app_state = await self.get_state(AppState)

    @rx.event
    def on_change_id_incoming_storage(self, value: str):
        self.id_incoming_storage = value
        if self.products_movement_list_state is not None:
            self.products_movement_list_state.filter_by_storage = (
                int(value) if value != "" else -1
            )
            self.products_movement_list_state.items = []

    @rx.event
    def on_change_id_incoming_owner(self, value: str):
        self.id_incoming_owner = value
        if self.products_movement_list_state is not None:
            self.products_movement_list_state.filter_by_owner = (
                int(value) if value != "" else -1
            )
            self.products_movement_list_state.items = []

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
            return rx.toast.error("Заявку не знайдено!")
        # Коментар заявки переносимо у продаж; перелік позицій — довідково
        # (заявка має рекомендаційний характер).
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

    @rx.event
    def on_click_search_name_incoming_storage(self):
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
    async def add_one(self, keep: bool = False):
        if not self.app_state.has_permission(ActionEnum.SALES_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        if (
            self.id_incoming_storage == ""
            or self.id_incoming_owner == ""
            or self.id_responsible == ""
        ):
            return rx.toast.error("Не обрано склад, власника або відповідального!")
        if (
            self.products_movement_list_state is None
            or len(self.products_movement_list_state.items) == 0
        ):
            return rx.toast.error("Список товарів для продажу порожній!")

        # Серверна перевірка типу місця: продаж можливий лише зі складу.
        if not StorageDAO.is_type(
            int(self.id_incoming_storage), StorageType.WAREHOUSE
        ):
            return rx.toast.error("Продаж можливий лише зі складу!")

        # Розділення подільного ТМЦ + перевірка серійних номерів.
        ok, msg, products_list = (
            self.products_movement_list_state.resolve_movement_products()
        )
        if not ok:
            return rx.toast.error(msg)

        # Перевіряємо, що для кожної позиції вказано ціну (> 0).
        prices = self.products_movement_list_state.get_prices()
        positions = {p.id_product_catalog for p in products_list}
        for catalog_id in positions:
            if prices.get(catalog_id, 0.0) <= 0:
                return rx.toast.error("Вкажіть вартість для кожної позиції товару!")

        form_data = {
            "id_responsible": int(self.id_responsible),
            "date": self.current_date,
            "id_incoming_storage": int(self.id_incoming_storage),
            "id_incoming_owner": int(self.id_incoming_owner),
            "status": self._status_index(),
            "comment": self.comment,
            "movement_products_list": products_list,
            "prices": prices,
            "id_user": (await self.get_state(AppState)).user.login,
        }

        list_id_products: List[int] = [p.id for p in products_list]
        flag, text, id = SaleDAO.add_one(form_data)
        if flag:
            # Зберігаємо серійні номери, уточнені під час продажу. Працюємо лише з
            # колонками (id/serial_number), без доступу до лінивої зв'язки
            # product_catalog (інстанси відокремлені). Для неунікального ТМЦ s/n
            # порожній — оновлення на те саме значення безпечне.
            serials = {p.id: p.serial_number for p in products_list}
            ProductDAO.update_serial_numbers(serials)
            # Проданий ТМЦ виводиться із залишків.
            ProductDAO.delete_list(list_id_products)
            # Якщо продаж формується на основі заявки — позначаємо її виконаною.
            if self.selected_request_id != "":
                RequestDAO.mark_completed(int(self.selected_request_id), id)
            if keep:
                await self._reset_for_continue()
                return rx.toast.success("Продаж проведено!")
            return [
                rx.toast.success("Продаж проведено!"),
                rx.redirect(f"{routes.MOVEMENT_SALES_VIEW_ID}{id}"),
            ]
        return rx.toast.error(text)
    # ======================


class EditSaleState(rx.State):
    item: Optional[Sale] = None

    id_incoming_storage: str = ""
    id_incoming_owner: str = ""
    id_responsible: str = ""
    status: str = ""

    list_storages: List[Tuple[str, str]] = []
    list_owners: List[Tuple[str, str]] = []
    list_workers: List[Tuple[str, str]] = []

    products_movement_list_state: Optional[ProductsMovementListState] = None
    app_state: Optional[AppState] = None

    # Backend only
    # ======================
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
    # ======================

    # Dynamic variables
    # ======================
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
    # ======================

    # Action handlers
    # ======================
    @rx.event
    async def on_load(self, id: int):
        self.item = SaleDAO.get_by_id_with_all_relationship(id)
        if self.item is None:
            return [
                rx.redirect(routes.MOVEMENT_SALES),
                rx.toast.error("Запис не знайдено!"),
            ]

        self.id_incoming_storage = str(self.item.movement.id_incoming_storage)
        self.id_incoming_owner = str(self.item.movement.id_incoming_owner)
        self.id_responsible = str(self.item.id_responsible)
        self.status = movements_status_list[self.item.movement.status]

        self._load_list_storages()
        self._load_list_owners()
        self._load_list_workers()

        self.products_movement_list_state = await self.get_state(
            ProductsMovementListState
        )
        await self.products_movement_list_state.on_load()
        self.products_movement_list_state.set_view_mode(True)

        all_products: List[Product] = []
        for product_category in self.item.movement.products_catalog:
            for product in product_category.products:
                product.product_catalog = product_category.product
                all_products.append(product)
        self.products_movement_list_state.items = all_products

        if self.app_state is None:
            self.app_state = await self.get_state(AppState)

    @rx.event
    def on_change_status(self, value: str):
        self.status = value

    @rx.event
    def on_change_comment(self, value: str):
        if self.item is not None:
            self.item.movement.comment = value

    @rx.event
    def edit_one(self):
        if not self.app_state.has_permission(ActionEnum.SALES_EDIT):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        if self.item is None:
            return rx.toast.error("Запис не завантажено!")
        if self.item.movement.status == MovementsStatus.CANCELED:
            return rx.toast.error("Продаж вже скасовано!")

        status_index = self._status_index()
        if status_index == MovementsStatus.CANCELED:
            return rx.toast.error(
                "Скасування виконується кнопкою «Скасувати», а не через редагування!"
            )

        # Склад/власник/позиції продажу не редагуються — лише статус і коментар.
        form_data = {
            "id": self.item.id,
            "status": status_index,
            "comment": self.item.movement.comment,
        }
        flag, text, id = SaleDAO.edit_one(form_data)
        if flag:
            return [
                rx.toast.success("Продаж змінено!"),
                rx.redirect(f"{routes.MOVEMENT_SALES_VIEW_ID}{id}"),
            ]
        return rx.toast.error(text)
    # ======================


class SaleState(rx.State):
    class Pages:
        ADD = "add"
        EDIT = "edit"
        VIEW = "view"
        LIST = "list"

    current_page: str = Pages.LIST
    app_state: Optional[AppState] = None

    def _check_path(self):
        page = self.router.page.params.get("page", "")
        if page != "":
            id = -1
            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                yield rx.redirect(routes.MOVEMENT_SALES)
                return

            if page == self.Pages.ADD:
                if not self.app_state.has_permission(ActionEnum.SALES_CREATE):
                    yield rx.redirect(routes.WELCOME)
                    return
                yield AddSaleState.on_load()
            elif page == self.Pages.EDIT:
                if not self.app_state.has_permission(ActionEnum.SALES_EDIT):
                    yield rx.redirect(routes.WELCOME)
                    return
                id = self.router.page.params.get("id", "")
                if id != "":
                    yield EditSaleState.on_load(int(id))
                else:
                    yield rx.redirect(routes.MOVEMENT_SALES)
                    return
            elif page == self.Pages.VIEW:
                if not self.app_state.has_permission(ActionEnum.SALES_VIEW):
                    yield rx.redirect(routes.WELCOME)
                    return
                id = self.router.page.params.get("id", "")
                if id != "":
                    yield ViewSaleState.on_load(int(id))
                else:
                    yield rx.redirect(routes.MOVEMENT_SALES)
                    return

            self.current_page = page
        else:
            if not self.app_state.has_permission(ActionEnum.SALES_LIST):
                yield rx.redirect(routes.WELCOME)
                return
            yield ListSaleState.on_load()
            self.current_page = self.Pages.LIST

    @rx.event
    async def on_load(self):
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
        return self._check_path()

    @rx.event
    async def delete_one(self, id: int):
        if not self.app_state.has_permission(ActionEnum.SALES_DELETE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        view_state = await self.get_state(ViewSaleState)
        if view_state.item is None or view_state.products_movement_list_state is None:
            return rx.toast.error("Не обрано запис для скасування!")
        if view_state.item.movement.status == MovementsStatus.CANCELED:
            return rx.toast.error("Продаж вже скасовано!")

        list_id_products: List[int] = [
            p.id for p in view_state.products_movement_list_state.items
        ]

        # Якщо товар бере участь у пізніших рухах — скасування заборонено.
        related_movements = MovementDAO.get_with_products_from_id(
            list_id_products, view_state.item.id
        )
        if any(m.id != view_state.item.id for m in related_movements):
            view_state.cancel_conflict_movements = related_movements
            view_state.is_cancel_conflict_dialog_open = True
            return rx.toast.error(
                "Скасування неможливе: товар бере участь у пізніших рухах!"
            )

        flag, text = MovementDAO.cancel_movement(view_state.item.id)
        if not flag:
            return rx.toast.error(text)

        # Скасування продажу повертає товари у залишки (їх було виведено при продажу).
        ProductDAO.undelete_list(list_id_products)
        # Якщо продаж був сформований за заявкою — повертаємо заявку у стан «Нова».
        RequestDAO.revert_completion_by_movement(view_state.item.id)
        return [
            rx.toast.success("Продаж скасовано!"),
            rx.redirect(f"{routes.MOVEMENT_SALES_VIEW_ID}{view_state.item.id}"),
        ]
