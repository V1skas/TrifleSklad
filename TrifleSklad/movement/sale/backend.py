from datetime import date
from typing import List, Optional, Tuple

import reflex as rx

import TrifleSklad.routes as routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.dao import (
    MovementDAO,
    OwnerDAO,
    ProductDAO,
    SaleDAO,
    StorageDAO,
    WorkerDAO,
)
from TrifleSklad.declared import (
    MovementsStatus,
    StorageType,
    movements_status_list,
    movements_type_list,
)
from TrifleSklad.models import Movement, Product, Sale
from TrifleSklad.movement.list_mixin import MovementListFilterMixin
from TrifleSklad.movement.products.backend import ProductsMovementListState
from TrifleSklad.state import AppState


class ListSaleState(MovementListFilterMixin, rx.State):
    items: List[Sale] = []

    def _reload(self):
        self._all_pages, self.items = SaleDAO.get_paginated(
            self._current_page,
            self._limit,
            self.filter_date_from,
            self.filter_date_to,
            self.selected_statuses,
        )

    # Dynamic variables
    # ======================
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

    # Detailed position dialog (одиниці ТМЦ обраної позиції)
    # ======================
    is_position_dialog_open: bool = False
    selected_position_index: int = -1
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
    def positions(self) -> List[Tuple[int, str, int, float, float]]:
        # (індекс, назва позиції, кількість, ціна за одиницю, сума по позиції)
        if self.item is None:
            return []
        return [
            (
                index,
                pc.product.title,
                pc.count,
                pc.price,
                round(pc.price * pc.count, 2),
            )
            for index, pc in enumerate(self.item.movement.products_catalog)
        ]

    @rx.var
    def selected_position_title(self) -> str:
        if (
            self.item is None
            or self.selected_position_index < 0
            or self.selected_position_index >= len(self.item.movement.products_catalog)
        ):
            return ""
        return self.item.movement.products_catalog[self.selected_position_index].product.title

    @rx.var
    def selected_position_units(self) -> List[Tuple[str, str, str]]:
        # (id одиниці, серійний номер або '—', залишок для подільного або '—')
        if (
            self.item is None
            or self.selected_position_index < 0
            or self.selected_position_index >= len(self.item.movement.products_catalog)
        ):
            return []
        pc = self.item.movement.products_catalog[self.selected_position_index]
        units: List[Tuple[str, str, str]] = []
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
            units.append((str(unit.id), serial, remain))
        return units

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
    def open_position_dialog(self, index: int):
        self.selected_position_index = index
        self.is_position_dialog_open = True

    @rx.event
    def set_position_dialog_open(self, value: bool):
        self.is_position_dialog_open = value
        if not value:
            self.selected_position_index = -1

    # Action handlers
    # ======================
    @rx.event
    async def on_load(self, id: int):
        self.is_position_dialog_open = False
        self.selected_position_index = -1
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


class AddSaleState(rx.State):
    current_date: str = date.today().__str__()

    id_incoming_storage: str = ""
    id_incoming_owner: str = ""
    id_responsible: str = ""
    search_name_incoming_storage: str = ""
    status: str = ""
    comment: str = ""

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
            if self.search_name_incoming_storage == ""
            or self.search_name_incoming_storage.lower() in item.title.lower()
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
        # «Скасовано» виставляється лише кнопкою «Скасувати» (з поверненням залишків).
        return [
            status
            for index, status in enumerate(movements_status_list)
            if index != MovementsStatus.CANCELED
        ]
    # ======================

    # Action handlers
    # ======================
    @rx.event
    async def on_load(self):
        self.current_date = date.today().__str__()
        self.id_incoming_storage = ""
        self.id_incoming_owner = ""
        self.id_responsible = ""
        self.search_name_incoming_storage = ""
        self.status = ""
        self.comment = ""

        self._load_list_storages()
        self._load_list_owners()
        self._load_list_workers()

        self.products_movement_list_state = await self.get_state(
            ProductsMovementListState
        )
        self.products_movement_list_state.items = []
        await self.products_movement_list_state.on_load()
        self.products_movement_list_state.set_view_mode(False)
        # Продаж: ціна за позицію обов'язкова; для ТМЦ із серійним номером — s/n.
        self.products_movement_list_state.set_require_price(True)
        self.products_movement_list_state.set_require_serial(True)

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
    async def add_one(self):
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
        return [
            rx.toast.success("Продаж скасовано!"),
            rx.redirect(f"{routes.MOVEMENT_SALES_VIEW_ID}{view_state.item.id}"),
        ]
