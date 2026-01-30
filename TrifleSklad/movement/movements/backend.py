import reflex as rx

from typing import List, Tuple, Optional
from datetime import date

from TrifleSklad.declared import movements_status_list, MovementsType, MovementsStatus

import TrifleSklad.routes as routes
from TrifleSklad.state import AppState

from TrifleSklad.models import Movement, Product
from TrifleSklad.dao import MovementDAO, StorageDAO, OwnerDAO, ProductDAO
from TrifleSklad.movement.products.backend import ProductsMovementListState

class MovementsState(rx.State):
    class Pages:
        ADD = "add"
        EDIT = "edit"
        VIEW = "view"
        LIST = "list"

    current_page: str = ""
    current_date: str = date.today().__str__()

    id_incoming_storage: str = ""
    id_incoming_owner: str = ""
    search_name_incoming_storage: str = ""

    id_destination_storage: str = ""
    id_destination_owner: str = ""
    search_name_destination_storage: str = ""
    status: str = ""

    list_storages: List[Tuple[str, str]] = []
    list_owners: List[Tuple[str, str]] = []

    items: List[Movement] = []
    selected_item: int = -1

    products_movement_list_state: Optional[ProductsMovementListState] = None

    def _check_path(self):
        page = self.router.page.params.get('page', '')
        if page != '':
            id = -1

            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                return rx.redirect(routes.MOVEMENT_MOVEMENTS)

            # /movements/add
            if page == self.Pages.ADD:
                id = Movement()

                self.__load_list_storages()
                self.__load_list_owners()

                self.id_incoming_storage = ""
                self.id_incoming_owner = ""
                self.id_destination_storage = ""
                self.id_destination_owner = ""
                self.status = ""
                self.search_name_incoming_storage = ""
                self.search_name_destination_storage = ""
            # /movements/edit/[id]
            elif page == self.Pages.EDIT:
                id = self.router.page.params.get('id', '')
                if id != '':
                    id = MovementDAO.get_by_id_with_product_storage_owner(id)
                    if id is None:
                        return [rx.redirect(routes.MOVEMENT_MOVEMENTS), rx.toast.error("Запись не найдена")]

                    self.__load_list_storages()
                    self.__load_list_owners()
                    self.id_incoming_storage = str(id.id_incoming_storage)
                    self.id_incoming_owner = str(id.id_incoming_owner)
                    self.id_destination_storage = str(id.id_destination_storage)
                    self.id_destination_owner = str(id.id_destination_owner)
                    self.status = movements_status_list[id.status]
                    self.search_name_incoming_storage = ""
                    self.search_name_destination_storage = ""
                else:
                    return rx.redirect(routes.MOVEMENT_MOVEMENTS)
            # /movements/view/[id]
            elif page == self.Pages.VIEW:
                id = self.router.page.params.get('id', '')
                if id != '':
                    id = MovementDAO.get_by_id_with_product_storage_owner(id)
                    if id is None:
                        return [rx.redirect(routes.MOVEMENT_MOVEMENTS), rx.toast.error("Запись не найдена")]
                else:
                    return rx.redirect(routes.MOVEMENT_MOVEMENTS)

            if page == MovementsState.Pages.VIEW:
                self.products_movement_list_state.set_view_mode(True)
            else:
                self.products_movement_list_state.set_view_mode(False)

            if page == MovementsState.Pages.ADD:
                self.products_movement_list_state.items = []
            else:
                all_products: List[Product] = []
                for product_category in id.products_catalog:  # FUTURE: Оптимизировать
                    for product in product_category.products:
                        product.product_catalog = product_category.product
                        all_products.append(product)
                self.products_movement_list_state.items = all_products

            self.items = []
            self.items.append(id)  # type: ignore
            self.selected_item = 0
            self.current_page = page

        else:
            # /movements
            self.current_page = self.Pages.LIST
            self.selected_item = -1
            self.selected_item = -1
            self.current_page = self.Pages.LIST
            self.items = MovementDAO.get_all_by_type_with_storage_owner(MovementsType.MOVEMENT)

    def __load_list_storages(self):
        self.list_storages = [(item.title, str(item.id)) for item in StorageDAO.get_all()]

    def __load_list_owners(self):
        self.list_owners = [(item.title, str(item.id)) for item in OwnerDAO.get_all()]

    @rx.var
    def filtered_incoming_storages(self) -> List[Tuple[str, str]]:
        return [item for item in self.list_storages if self.search_name_incoming_storage == "" or
                              self.search_name_incoming_storage.lower() in item[0].lower() ]

    @rx.var
    def filtered_destination_storages(self) -> List[Tuple[str, str]]:
        return [item for item in self.list_storages if self.search_name_destination_storage == "" or
                              self.search_name_destination_storage.lower() in item[0].lower() ]

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def current_is_canceled(self) -> bool:
        if self.selected_item != -1:
            return self.items[self.selected_item].status == MovementsStatus.CANCELED
        return False

    @rx.var
    def get_items(self) -> List[Tuple[int, Movement]]:
        return [(index, item) for index, item in enumerate(self.items)]

    @rx.var
    def has_selected_item(self) -> bool:
        return self.selected_item != -1

    @rx.var
    def get_selected_item(self) -> Tuple[int, Movement]:
        if self.selected_item != -1:
            return (self.selected_item, self.items[self.selected_item])
        return (-1, Movement())

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list

    @rx.var
    def get_selected_movement_status(self) -> str:
        if self.current_page == MovementsState.Pages.ADD:
            return ""
        return movements_status_list[self.items[self.selected_item].status] if self.selected_item >= 0 else ""

    @rx.event
    async def on_load(self):
        self.products_movement_list_state = (await self.get_state(ProductsMovementListState))
        self.products_movement_list_state.items = []
        await self.products_movement_list_state.on_load()
        self._check_path()

    @rx.event
    def on_change_id_incoming_storage(self, value: str):
        self.id_incoming_storage = value
        self.products_movement_list_state.filter_by_storage = int(
            self.id_incoming_storage) if self.id_incoming_storage != "" else -1
        self.products_movement_list_state.items = []

    @rx.event
    def on_change_id_incoming_owner(self, value: str):
        self.id_incoming_owner = value
        self.products_movement_list_state.filter_by_owner = int(
            self.id_incoming_owner) if self.id_incoming_owner != "" else -1
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
        self.__load_list_storages()

    @rx.event
    def on_change_search_name_destination_storage(self, value: str):
        self.search_name_destination_storage = value

    @rx.event
    def on_click_search_name_destination_storage(self):
        self.__load_list_storages()

    @rx.event
    def on_change_status(self, value: str):
        self.status = value

    @rx.event
    async def add_one(self, form_data: dict):
        if self.id_destination_owner == "" or self.id_destination_storage == "":
            return rx.toast.error("Не выбраны владелец или склад назначения!")

        if self.products_movement_list_state.items == []:
            return rx.toast.error("Список перемещаемых товаров пуст!")

        form_data["type"] = MovementsType.MOVEMENT
        form_data["movement_products_list"] = self.products_movement_list_state.items
        form_data["id_user"] = (await self.get_state(AppState)).user.login

        list_id_item_for_delete: List[int] = [product.id for product in self.products_movement_list_state.items]
        flag, text, id = MovementDAO.add_one(form_data)
        if flag:
            flat, text = ProductDAO.update_owner_storage(list_id_item_for_delete, self.id_destination_owner, self.id_destination_storage)
            if flag:
                return [rx.toast.success("Перемещение проведено!"),
                        rx.redirect(f"{routes.MOVEMENT_MOVEMENTS_VIEW_ID}{id}")]
        return rx.toast.error(text)

    @rx.event
    def delete_one(self):
        pass  # Implementation of deleting a movement would go here