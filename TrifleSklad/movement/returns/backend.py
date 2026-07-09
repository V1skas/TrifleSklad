from datetime import date
from typing import List, Optional, Tuple

import reflex as rx

import TrifleSklad.routes as routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.dao import MovementDAO, ProductDAO, StorageDAO
from TrifleSklad.declared import (
    MovementsStatus,
    MovementsType,
    StorageType,
    movements_status_list,
    movements_type_list,
)
from TrifleSklad.models import Movement, Product
from TrifleSklad.movement.list_mixin import MovementListFilterMixin
from TrifleSklad.movement.inline_creators import LookupCreatorsMixin
from TrifleSklad.movement.products.backend import ProductsMovementListState
from TrifleSklad.state import AppState


class ListReturnsState(MovementListFilterMixin, rx.State):
    items: List[Movement] = []

    def _reload(self):
        self._all_pages, self.items = MovementDAO.get_by_type_paginated(
            MovementsType.RETURN,
            self._current_page,
            self._limit,
            self._date_from_eff(),
            self._date_to_eff(),
            self.selected_statuses,
            incoming_storage=self.filter_incoming_storage,
            destination_storage=self.filter_destination_storage,
        )

    # Dynamic variables
    # ======================
    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def get_items(self) -> List[Tuple[int, Movement]]:
        return [(index, item) for index, item in enumerate(self.items)]

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list
    # ======================

    @rx.event
    def on_load(self):
        self._reset_list_state()
        self._reload()


class ViewReturnsState(rx.State):
    item: Optional[Movement] = None

    products_movement_list_state: Optional[ProductsMovementListState] = None
    app_state: Optional[AppState] = None

    # Cancel-conflict dialog
    # ======================
    cancel_conflict_movements: List[Movement] = []
    is_cancel_conflict_dialog_open: bool = False
    # ======================

    # Dynamic variables
    # ======================
    @rx.var
    def item_status(self) -> str:
        return movements_status_list[self.item.status] if self.item is not None else ""

    @rx.var
    def current_is_canceled(self) -> bool:
        return self.item is not None and self.item.status == MovementsStatus.CANCELED

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
    async def on_load(self, id: int):
        self.item = MovementDAO.get_by_id_with_product_storage_owner(id)
        if self.item is None:
            return [
                rx.redirect(routes.MOVEMENT_RETURNS),
                rx.toast.error("Запис не знайдено!"),
            ]

        self.products_movement_list_state = await self.get_state(
            ProductsMovementListState
        )
        await self.products_movement_list_state.on_load()
        self.products_movement_list_state.set_view_mode(True)

        all_products: List[Product] = []
        for product_category in self.item.products_catalog:
            for product in product_category.products:
                product.product_catalog = product_category.product
                all_products.append(product)
        self.products_movement_list_state.items = all_products

        if self.app_state is None:
            self.app_state = await self.get_state(AppState)


class AddReturnsState(LookupCreatorsMixin, rx.State):
    current_date: str = date.today().__str__()

    id_incoming_storage: str = ""
    id_destination_storage: str = ""
    status: str = ""
    comment: str = ""

    # Джерело — площадки/відділи; призначення — склади.
    list_source_storages: List[Tuple[str, str]] = []
    list_destination_storages: List[Tuple[str, str]] = []

    products_movement_list_state: Optional[ProductsMovementListState] = None
    app_state: Optional[AppState] = None

    # Backend only
    # ======================
    def _load_storages(self):
        sources = StorageDAO.get_all_by_type(
            StorageType.TECHNICAL_SITE
        ) + StorageDAO.get_all_by_type(StorageType.DEPARTMENT)
        self.list_source_storages = [(s.title, str(s.id)) for s in sources]
        self.list_destination_storages = [
            (s.title, str(s.id))
            for s in StorageDAO.get_all_by_type(StorageType.WAREHOUSE)
        ]

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
        # «Скасовано» виставляється лише кнопкою «Скасувати».
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
        self.id_destination_storage = ""
        self.status = ""
        self.comment = ""

        self._load_storages()

        self.products_movement_list_state = await self.get_state(
            ProductsMovementListState
        )
        self.products_movement_list_state.items = []
        await self.products_movement_list_state.on_load()
        self.products_movement_list_state.set_view_mode(False)
        # Повернення: власник не задається — фільтр лише за складом (площадкою/відділом),
        # кожна одиниця зберігає свого власника.
        self.products_movement_list_state.set_require_owner(False)

        # Передзаповнення складу-призначення за замовчуванням (TS-33).
        default_storage = StorageDAO.get_default_id(StorageType.WAREHOUSE)
        if default_storage is not None:
            self.id_destination_storage = str(default_storage)

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
    def on_change_id_destination_storage(self, value: str):
        self.id_destination_storage = value

    @rx.event
    def on_change_status(self, value: str):
        self.status = value

    @rx.event
    def on_change_date(self, value: str):
        self.current_date = value

    @rx.event
    def on_change_comment(self, value: str):
        self.comment = value

    # Inline-створення довідників
    # ======================
    def _after_create_storage(self, new_id: int):
        self._load_storages()
        if self.st_slot == "incoming":
            self.id_incoming_storage = str(new_id)
            if self.products_movement_list_state is not None:
                self.products_movement_list_state.filter_by_storage = new_id
                self.products_movement_list_state.items = []
        else:
            self.id_destination_storage = str(new_id)

    async def _reset_for_continue(self):
        keep = dict(
            current_date=self.current_date,
            id_incoming_storage=self.id_incoming_storage,
            id_destination_storage=self.id_destination_storage,
            status=self.status,
        )
        self.comment = ""

        self.current_date = keep["current_date"]
        self.id_incoming_storage = keep["id_incoming_storage"]
        self.id_destination_storage = keep["id_destination_storage"]
        self.status = keep["status"]

        self._load_storages()

        self.products_movement_list_state.items = []
        await self.products_movement_list_state.on_load()
        self.products_movement_list_state.set_view_mode(False)
        self.products_movement_list_state.set_require_owner(False)
        if keep["id_incoming_storage"] != "":
            self.products_movement_list_state.filter_by_storage = int(keep["id_incoming_storage"])

    @rx.event
    async def add_one(self, keep: bool = False):
        if not self.app_state.has_permission(ActionEnum.RETURNS_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        if self.id_incoming_storage == "" or self.id_destination_storage == "":
            return rx.toast.error("Не обрано місце повернення або склад призначення!")
        if (
            self.products_movement_list_state is None
            or len(self.products_movement_list_state.items) == 0
        ):
            return rx.toast.error("Список товарів для повернення порожній!")

        # Серверна перевірка типів місць: повернення з площадки/відділу на склад.
        if not StorageDAO.is_type(
            int(self.id_incoming_storage),
            (StorageType.TECHNICAL_SITE, StorageType.DEPARTMENT),
        ):
            return rx.toast.error("Повернення можливе лише з площадки або відділу!")
        if not StorageDAO.is_type(
            int(self.id_destination_storage), StorageType.WAREHOUSE
        ):
            return rx.toast.error("Повертати ТМЦ можна лише на склад!")

        # Розділення подільного ТМЦ: підсумковий перелік одиниць (з дочірніми частинами).
        ok, msg, products_list = (
            self.products_movement_list_state.resolve_movement_products()
        )
        if not ok:
            return rx.toast.error(msg)

        # Власник не задається — лишається той, що був при видачі (per-product),
        # тому owner-поля руху не заповнюємо.
        form_data = {
            "type": MovementsType.RETURN,
            "date": self.current_date,
            "id_incoming_storage": int(self.id_incoming_storage),
            "id_incoming_owner": None,
            "id_destination_storage": int(self.id_destination_storage),
            "id_destination_owner": None,
            "status": self._status_index(),
            "comment": self.comment,
            "movement_products_list": products_list,
            "id_user": (await self.get_state(AppState)).user.login,
        }

        list_id_products: List[int] = [p.id for p in products_list]
        flag, text, id = MovementDAO.add_one(form_data)
        if flag:
            # Повертаємо одиниці на склад призначення, не змінюючи власника.
            ProductDAO.update_storage(
                list_id_products, int(self.id_destination_storage)
            )
            if keep:
                await self._reset_for_continue()
                return rx.toast.success("Повернення проведено!")
            return [
                rx.toast.success("Повернення проведено!"),
                ListReturnsState.on_load(),
                rx.redirect(f"{routes.MOVEMENT_RETURNS_VIEW_ID}{id}"),
            ]
        return rx.toast.error(text)
    # ======================


class EditReturnsState(rx.State):
    item: Optional[Movement] = None
    status: str = ""

    products_movement_list_state: Optional[ProductsMovementListState] = None
    app_state: Optional[AppState] = None

    def _status_index(self) -> int:
        for index, status_text in enumerate(movements_status_list):
            if status_text == self.status:
                return index
        return MovementsStatus.CREATED

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
    async def on_load(self, id: int):
        self.item = MovementDAO.get_by_id_with_product_storage_owner(id)
        if self.item is None:
            return [
                rx.redirect(routes.MOVEMENT_RETURNS),
                rx.toast.error("Запис не знайдено!"),
            ]
        self.status = movements_status_list[self.item.status]

        self.products_movement_list_state = await self.get_state(
            ProductsMovementListState
        )
        await self.products_movement_list_state.on_load()
        self.products_movement_list_state.set_view_mode(True)

        all_products: List[Product] = []
        for product_category in self.item.products_catalog:
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
            self.item.comment = value

    @rx.event
    def edit_one(self):
        if not self.app_state.has_permission(ActionEnum.RETURNS_EDIT):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        if self.item is None:
            return rx.toast.error("Запис не завантажено!")
        if self.item.status == MovementsStatus.CANCELED:
            return rx.toast.error("Повернення вже скасовано!")

        status_index = self._status_index()
        if status_index == MovementsStatus.CANCELED:
            return rx.toast.error(
                "Скасування виконується кнопкою «Скасувати», а не через редагування!"
            )

        # Місця/позиції повернення не редагуються — лише статус і коментар.
        form_data = {
            "id": self.item.id,
            "status": status_index,
            "comment": self.item.comment,
        }
        flag, text, id = MovementDAO.edit_one(form_data)
        if flag:
            return [
                rx.toast.success("Повернення змінено!"),
                ListReturnsState.on_load(),
                rx.redirect(f"{routes.MOVEMENT_RETURNS_VIEW_ID}{id}"),
            ]
        return rx.toast.error(text)


class ReturnsState(rx.State):
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
            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                yield rx.redirect(routes.MOVEMENT_RETURNS)
                return

            if page == self.Pages.ADD:
                if not self.app_state.has_permission(ActionEnum.RETURNS_CREATE):
                    yield rx.redirect(routes.WELCOME)
                    return
                yield AddReturnsState.on_load()
            elif page == self.Pages.EDIT:
                if not self.app_state.has_permission(ActionEnum.RETURNS_EDIT):
                    yield rx.redirect(routes.WELCOME)
                    return
                id = self.router.page.params.get("id", "")
                if id != "":
                    yield EditReturnsState.on_load(int(id))
                else:
                    yield rx.redirect(routes.MOVEMENT_RETURNS)
                    return
            elif page == self.Pages.VIEW:
                if not self.app_state.has_permission(ActionEnum.RETURNS_VIEW):
                    yield rx.redirect(routes.WELCOME)
                    return
                id = self.router.page.params.get("id", "")
                if id != "":
                    yield ViewReturnsState.on_load(int(id))
                else:
                    yield rx.redirect(routes.MOVEMENT_RETURNS)
                    return

            self.current_page = page
        else:
            if not self.app_state.has_permission(ActionEnum.RETURNS_LIST):
                yield rx.redirect(routes.WELCOME)
                return
            yield ListReturnsState.on_load()
            self.current_page = self.Pages.LIST

    @rx.event
    async def on_load(self):
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
        return self._check_path()

    @rx.event
    async def delete_one(self):
        if not self.app_state.has_permission(ActionEnum.RETURNS_DELETE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")

        view_state = await self.get_state(ViewReturnsState)
        if view_state.item is None or view_state.products_movement_list_state is None:
            return rx.toast.error("Не обрано запис для скасування!")
        if view_state.item.status == MovementsStatus.CANCELED:
            return rx.toast.error("Повернення вже скасовано!")

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

        # Скасування повернення повертає кожну одиницю ТМЦ туди, куди її привів
        # попередній рух (видача на площадку/відділ) — за наскрізним номером.
        MovementDAO.restore_products_to_previous_location(
            list_id_products, view_state.item.id
        )
        return [
            rx.toast.success("Повернення скасовано!"),
            rx.redirect(f"{routes.MOVEMENT_RETURNS_VIEW_ID}{view_state.item.id}"),
        ]
