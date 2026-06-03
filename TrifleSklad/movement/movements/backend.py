from datetime import date
from typing import List, Optional, Tuple

import reflex as rx

import TrifleSklad.routes as routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.dao import MovementDAO, OwnerDAO, ProductDAO, StorageDAO
from TrifleSklad.declared import MovementsStatus, MovementsType, movements_status_list
from TrifleSklad.models import Movement, Product
from TrifleSklad.movement.products.backend import ProductsMovementListState
from TrifleSklad.state import AppState


class ListMovementsState(rx.State):
    items: List[Movement] = []

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

    # Action handlers
    # ======================
    @rx.event
    def on_load(self):
        self.items = MovementDAO.get_all_by_type_with_storage_owner(MovementsType.MOVEMENT)
    # ======================


class ViewMovementsState(rx.State):
    item: Optional[Movement] = None

    # Nested form states
    # ======================
    products_movement_list_state: Optional[ProductsMovementListState] = None
    # ======================

    app_state: Optional[AppState] = None

    # Dynamic variables
    # ======================
    @rx.var
    def item_status(self) -> str:
        return movements_status_list[self.item.status] if self.item is not None else ""

    @rx.var
    def current_is_canceled(self) -> bool:
        return self.item is not None and self.item.status == MovementsStatus.CANCELED
    # ======================

    # Action handlers
    # ======================
    @rx.event
    async def on_load(self, id: int):
        self.item = MovementDAO.get_by_id_with_product_storage_owner(id)
        if self.item is None:
            return [
                rx.redirect(routes.MOVEMENT_MOVEMENTS),
                rx.toast.error("Запис не знайдено!"),
            ]

        self.products_movement_list_state = await self.get_state(ProductsMovementListState)
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
    # ======================


class AddMovementsState(rx.State):
    current_date: str = date.today().__str__()

    id_incoming_storage: str = ""
    id_incoming_owner: str = ""
    search_name_incoming_storage: str = ""

    id_destination_storage: str = ""
    id_destination_owner: str = ""
    search_name_destination_storage: str = ""
    status: str = ""
    comment: str = ""

    list_storages: List[Tuple[str, str]] = []
    list_owners: List[Tuple[str, str]] = []

    products_movement_list_state: Optional[ProductsMovementListState] = None
    app_state: Optional[AppState] = None

    # Backend only
    # ======================
    def _load_list_storages(self):
        self.list_storages = [(item.title, str(item.id)) for item in StorageDAO.get_all()]

    def _load_list_owners(self):
        self.list_owners = [(item.title, str(item.id)) for item in OwnerDAO.get_all()]

    def _status_index(self) -> int:
        for index, status_text in enumerate(movements_status_list):
            if status_text == self.status:
                return index
        return MovementsStatus.CREATED
    # ======================

    # Dynamic variables
    # ======================
    @rx.var
    def filtered_incoming_storages(self) -> List[Tuple[str, str]]:
        return [
            item for item in self.list_storages
            if self.search_name_incoming_storage == ""
            or self.search_name_incoming_storage.lower() in item[0].lower()
        ]

    @rx.var
    def filtered_destination_storages(self) -> List[Tuple[str, str]]:
        return [
            item for item in self.list_storages
            if self.search_name_destination_storage == ""
            or self.search_name_destination_storage.lower() in item[0].lower()
        ]

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list
    # ======================

    # Action handlers
    # ======================
    @rx.event
    async def on_load(self):
        self.current_date = date.today().__str__()
        self.id_incoming_storage = ""
        self.id_incoming_owner = ""
        self.id_destination_storage = ""
        self.id_destination_owner = ""
        self.search_name_incoming_storage = ""
        self.search_name_destination_storage = ""
        self.status = ""
        self.comment = ""

        self._load_list_storages()
        self._load_list_owners()

        self.products_movement_list_state = await self.get_state(ProductsMovementListState)
        self.products_movement_list_state.items = []
        await self.products_movement_list_state.on_load()
        self.products_movement_list_state.set_view_mode(False)

        if self.app_state is None:
            self.app_state = await self.get_state(AppState)

    @rx.event
    def on_change_id_incoming_storage(self, value: str):
        self.id_incoming_storage = value
        if self.products_movement_list_state is not None:
            self.products_movement_list_state.filter_by_storage = int(value) if value != "" else -1
            self.products_movement_list_state.items = []

    @rx.event
    def on_change_id_incoming_owner(self, value: str):
        self.id_incoming_owner = value
        if self.products_movement_list_state is not None:
            self.products_movement_list_state.filter_by_owner = int(value) if value != "" else -1
            self.products_movement_list_state.items = []

    @rx.event
    def on_change_id_destination_storage(self, value: str):
        self.id_destination_storage = value

    @rx.event
    def on_change_id_destination_owner(self, value: str):
        self.id_destination_owner = value

    @rx.event
    def on_change_search_name_incoming_storage(self, value: str):
        self.search_name_incoming_storage = value

    @rx.event
    def on_click_search_name_incoming_storage(self):
        self._load_list_storages()

    @rx.event
    def on_change_search_name_destination_storage(self, value: str):
        self.search_name_destination_storage = value

    @rx.event
    def on_click_search_name_destination_storage(self):
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
        if not self.app_state.has_permission(ActionEnum.MOVEMENTS_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        if self.id_destination_owner == "" or self.id_destination_storage == "":
            return rx.toast.error("Не обрано власника або склад призначення!")
        if self.products_movement_list_state is None or len(self.products_movement_list_state.items) == 0:
            return rx.toast.error("Список товарів для переміщення порожній!")

        form_data = {
            "type": MovementsType.MOVEMENT,
            "date": self.current_date,
            "id_incoming_storage": int(self.id_incoming_storage),
            "id_incoming_owner": int(self.id_incoming_owner),
            "id_destination_storage": int(self.id_destination_storage),
            "id_destination_owner": int(self.id_destination_owner),
            "status": self._status_index(),
            "comment": self.comment,
            "movement_products_list": self.products_movement_list_state.items,
            "id_user": (await self.get_state(AppState)).user.login,
        }

        list_id_products: List[int] = [p.id for p in self.products_movement_list_state.items]
        flag, text, id = MovementDAO.add_one(form_data)
        if flag:
            ProductDAO.update_owner_storage(
                list_id_products,
                self.id_destination_owner,
                self.id_destination_storage,
            )
            return [
                rx.toast.success("Переміщення проведено!"),
                rx.redirect(f"{routes.MOVEMENT_MOVEMENTS_VIEW_ID}{id}"),
            ]
        return rx.toast.error(text)
    # ======================


class EditMovementsState(rx.State):
    item: Optional[Movement] = None

    id_incoming_storage: str = ""
    id_incoming_owner: str = ""
    search_name_incoming_storage: str = ""

    id_destination_storage: str = ""
    id_destination_owner: str = ""
    search_name_destination_storage: str = ""
    status: str = ""

    list_storages: List[Tuple[str, str]] = []
    list_owners: List[Tuple[str, str]] = []

    products_movement_list_state: Optional[ProductsMovementListState] = None
    app_state: Optional[AppState] = None

    # Backend only
    # ======================
    def _load_list_storages(self):
        self.list_storages = [(item.title, str(item.id)) for item in StorageDAO.get_all()]

    def _load_list_owners(self):
        self.list_owners = [(item.title, str(item.id)) for item in OwnerDAO.get_all()]
    # ======================

    # Dynamic variables
    # ======================
    @rx.var
    def filtered_incoming_storages(self) -> List[Tuple[str, str]]:
        return [
            item for item in self.list_storages
            if self.search_name_incoming_storage == ""
            or self.search_name_incoming_storage.lower() in item[0].lower()
        ]

    @rx.var
    def filtered_destination_storages(self) -> List[Tuple[str, str]]:
        return [
            item for item in self.list_storages
            if self.search_name_destination_storage == ""
            or self.search_name_destination_storage.lower() in item[0].lower()
        ]

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list
    # ======================

    # Action handlers
    # ======================
    @rx.event
    async def on_load(self, id: int):
        self.search_name_incoming_storage = ""
        self.search_name_destination_storage = ""

        self.item = MovementDAO.get_by_id_with_product_storage_owner(id)
        if self.item is None:
            return [
                rx.redirect(routes.MOVEMENT_MOVEMENTS),
                rx.toast.error("Запис не знайдено!"),
            ]

        self.id_incoming_storage = str(self.item.id_incoming_storage)
        self.id_incoming_owner = str(self.item.id_incoming_owner)
        self.id_destination_storage = str(self.item.id_destination_storage)
        self.id_destination_owner = str(self.item.id_destination_owner)
        self.status = movements_status_list[self.item.status]

        self._load_list_storages()
        self._load_list_owners()

        self.products_movement_list_state = await self.get_state(ProductsMovementListState)
        await self.products_movement_list_state.on_load()
        self.products_movement_list_state.set_view_mode(False)

        all_products: List[Product] = []
        for product_category in self.item.products_catalog:
            for product in product_category.products:
                product.product_catalog = product_category.product
                all_products.append(product)
        self.products_movement_list_state.items = all_products

        if self.app_state is None:
            self.app_state = await self.get_state(AppState)

    @rx.event
    def on_change_id_incoming_storage(self, value: str):
        self.id_incoming_storage = value

    @rx.event
    def on_change_id_incoming_owner(self, value: str):
        self.id_incoming_owner = value

    @rx.event
    def on_change_id_destination_storage(self, value: str):
        self.id_destination_storage = value

    @rx.event
    def on_change_id_destination_owner(self, value: str):
        self.id_destination_owner = value

    @rx.event
    def on_change_search_name_incoming_storage(self, value: str):
        self.search_name_incoming_storage = value

    @rx.event
    def on_click_search_name_incoming_storage(self):
        self._load_list_storages()

    @rx.event
    def on_change_search_name_destination_storage(self, value: str):
        self.search_name_destination_storage = value

    @rx.event
    def on_click_search_name_destination_storage(self):
        self._load_list_storages()

    @rx.event
    def on_change_status(self, value: str):
        self.status = value

    @rx.event
    def on_change_comment(self, value: str):
        if self.item is not None:
            self.item.comment = value

    @rx.event
    def edit_one(self):
        if not self.app_state.has_permission(ActionEnum.MOVEMENTS_EDIT):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        return rx.toast.info("Редагування переміщення поки що не підтримується.")
    # ======================


class MovementsState(rx.State):
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
                yield rx.redirect(routes.MOVEMENT_MOVEMENTS)
                return

            if page == self.Pages.ADD:
                if not self.app_state.has_permission(ActionEnum.MOVEMENTS_CREATE):
                    yield rx.redirect(routes.WELCOME)
                    return
                yield AddMovementsState.on_load()
            elif page == self.Pages.EDIT:
                if not self.app_state.has_permission(ActionEnum.MOVEMENTS_EDIT):
                    yield rx.redirect(routes.WELCOME)
                    return
                id = self.router.page.params.get("id", "")
                if id != "":
                    yield EditMovementsState.on_load(int(id))
                else:
                    yield rx.redirect(routes.MOVEMENT_MOVEMENTS)
                    return
            elif page == self.Pages.VIEW:
                if not self.app_state.has_permission(ActionEnum.MOVEMENTS_VIEW):
                    yield rx.redirect(routes.WELCOME)
                    return
                id = self.router.page.params.get("id", "")
                if id != "":
                    yield ViewMovementsState.on_load(int(id))
                else:
                    yield rx.redirect(routes.MOVEMENT_MOVEMENTS)
                    return

            self.current_page = page
        else:
            if not self.app_state.has_permission(ActionEnum.MOVEMENTS_LIST):
                yield rx.redirect(routes.WELCOME)
                return
            yield ListMovementsState.on_load()
            self.current_page = self.Pages.LIST

    @rx.event
    async def on_load(self):
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
        return self._check_path()

    @rx.event
    def delete_one(self):
        if not self.app_state.has_permission(ActionEnum.MOVEMENTS_DELETE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        return rx.toast.info("Скасування переміщення поки що не підтримується.")
