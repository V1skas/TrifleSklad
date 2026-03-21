from datetime import date
from typing import List, Optional, Tuple

import reflex as rx

import TrifleSklad.routes as routes
from TrifleSklad.dao import IssueDAO, OwnerDAO, StorageDAO, WorkerDAO
from TrifleSklad.declared import (
    MovementsStatus,
    MovementsType,
    StorageType,
    movements_status_list,
)
from TrifleSklad.models import (
    Issue,
    Movement,
    MovementProductsCatalog,
    Product,
    ProductCatalog,
)
from TrifleSklad.movement.products.backend import ProductsMovementListState
from TrifleSklad.state import AppState


class ListIssueState(rx.State):
    items: List[Issue] = []

    # Backend methods
    # ======================
    def on_load(self):
        self.items = IssueDAO.get_all_with_all_relationship()

    # ======================

    # Dynamic variables
    # ======================
    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def get_items(self) -> List[Tuple[int, Issue]]:
        return [(index, item) for index, item in enumerate(self.items)]

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list

    # ======================


class ViewIssueState(rx.State):
    item: Issue = Issue(
        id_recipient=-1,
        movement=Movement(
            id_incoming_storage=-1,
            id_incoming_owner=-1,
            date=date.today().__str__(),
            comment="",
            status=MovementsStatus.CREATED,
            type=MovementsType.ISSUE,
            total_cost=0.0,
            products_catalog=[],
        ),
    )

    # Nested form states
    # ======================
    products_selector_state: Optional[ProductsMovementListState] = None
    # ======================

    # Backend only
    # ======================
    async def on_load(self, id: int):
        self.item = IssueDAO.get_by_id_with_movement_product_storage_owner_recipient(id)
        self.products_selector_state = await self.get_state(ProductsMovementListState)
        await self.products_selector_state.on_load()
        self.products_selector_state.set_view_mode(True)

        all_products: List[Product] = []
        for (
            product_category
        ) in self.item.movement.products_catalog:  # FUTURE: Оптимизировать
            for product in product_category.products:
                product.product_catalog = product_category.product
                all_products.append(product)

        self.products_selector_state.items = all_products

    # ======================

    # Getters for form fields
    # ======================
    @rx.var
    def item_status(self) -> str:
        return movements_status_list[self.item.movement.status]

    # ======================


class AddIssueState(rx.State):
    item: Issue = Issue(
        id_recipient=-1,
        movement=Movement(
            id_incoming_storage=-1,
            id_incoming_owner=-1,
            id_destination_storage=-1,
            id_destination_owner=-1,
            date=date.today().__str__(),
            comment="",
            status=MovementsStatus.CREATED,
            type=MovementsType.ISSUE,
            total_cost=0.0,
            products_catalog=[],
        ),
    )

    # Preloaded lists
    # ======================
    list_incoming_storages: List[Tuple[str, str]]
    list_destination_storages: List[Tuple[str, str]]
    list_owners: List[Tuple[str, str]]
    list_workers: List[Tuple[str, str]]
    # ======================

    # Filter fields
    # ======================
    search_name_destination_storage: str
    # ======================

    # Interface logic variables
    # ======================
    is_open_product_dialog: bool = False
    # ======================

    # Nested form states
    # ======================
    products_selector_state: Optional[ProductsMovementListState] = None
    # ======================

    # Backend only
    # ======================
    def __load_incoming_storages(self):
        self.list_incoming_storages = [
            (item.title, str(item.id))
            for item in StorageDAO.get_all_by_type(StorageType.WAREHOUSE)
        ]

    def __load_destination_storages(self):
        self.list_destination_storages = [
            (item.title, str(item.id))
            for item in StorageDAO.get_all()
            if self.search_name_destination_storage == ""
            or self.search_name_destination_storage.lower() in item.title.lower()
        ]

    def __load_owners(self):
        self.list_owners = [(item.title, str(item.id)) for item in OwnerDAO.get_all()]

    def __load_workers(self):
        self.list_workers = [(item.fio, str(item.id)) for item in WorkerDAO.get_all()]

    async def on_load(self):
        await self._on_load()

    async def _on_load(self):
        self.item = Issue(
            id_recipient=-1,
            movement=Movement(
                id_incoming_storage=-1,
                id_incoming_owner=-1,
                id_destination_storage=-1,
                id_destination_owner=-1,
                date=date.today().__str__(),
                comment="",
                status=MovementsStatus.CREATED,
                type=MovementsType.ISSUE,
                total_cost=0.0,
                products_catalog=[],
            ),
        )
        self.is_open_product_dialog = False

        self.__load_incoming_storages()
        self.__load_destination_storages()
        self.__load_owners()
        self.__load_workers()

        self.products_selector_state = await self.get_state(ProductsMovementListState)
        await self.products_selector_state.on_load()
        self.products_selector_state.set_view_mode(False)

    # ======================

    # Getters for form fields
    # ======================
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

    # ======================

    # Event handlers for form fields
    # ======================
    @rx.event
    def on_change_search_name_destination_storage(self, value: str):
        self.search_name_destination_storage = value

    @rx.event
    def on_click_search_name_destination_storage(self):
        self.__load_destination_storages()

    @rx.event
    def on_change_id_incoming_storage(self, value: str):
        self.item.movement.id_incoming_storage = int(value)
        self.products_selector_state.filter_by_storage = (
            int(self.item.movement.id_incoming_storage)
            if self.item.movement.id_incoming_storage != ""
            else -1
        )
        self.products_selector_state.items = []

    @rx.event
    def on_change_id_incoming_owner(self, value: str):
        self.item.movement.id_incoming_owner = int(value)
        self.item.movement.id_destination_owner = int(value)
        self.products_selector_state.filter_by_owner = (
            int(self.item.movement.id_incoming_owner)
            if self.item.movement.id_incoming_owner != ""
            else -1
        )
        self.products_selector_state.items = []

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

    # ======================

    # Dynamic variables
    # ======================
    @rx.var
    def item_status(self) -> str:
        return movements_status_list[self.item.movement.status]

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list

    # ======================

    # Action handlers
    # ======================
    @rx.event
    async def add_one(self):
        if self.item.movement.id_incoming_storage == -1 or self.item.movement.id_incoming_owner == -1 \
            or self.item.id_recipient == -1 or self.products_selector_state is None or len(self.products_selector_state.items) == 0:
            return rx.toast.error("Не всі обов'язкові поля заповнені!")

        self.item.movement.id_user = (await self.get_state(AppState)).user.login

        products_catalog: List[ProductCatalog] = []
        movement_products_catalog: List[MovementProductsCatalog] = []
        products_list: List[Product] = self.products_selector_state.items

        for product in products_list:
            if product.product_catalog not in products_catalog:
                products_catalog.append(
                    product.product_catalog
                )  # FUTURES: можно оптимизировать

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

        flag, text, id = IssueDAO.add_one(self.item)
        if flag:
            return [
                rx.toast.success(text),
                rx.redirect(f"{routes.MOVEMENT_ISSUES_VIEW_ID}{id}"),
            ]
        return rx.toast.error(text)

    # ======================


class EditIssueState(AddIssueState):
    # Backend only
    # ======================
    async def on_load(self, id: int):
        await super()._on_load()
        self.item = IssueDAO.get_by_id_with_all_relationship(id)

    # ======================

    # Action handlers
    # ======================
    @rx.event
    async def add_one(self):
        print("Use edit_one method instead of add_one in EditIssueState")

    @rx.event
    async def edit_one(self):
        if self.item.movement.id_incoming_storage == -1 or self.item.movement.id_incoming_owner == -1 \
            or self.item.id_recipient == -1 or self.products_selector_state is None or len(self.products_selector_state.items) == 0:
            return rx.toast.error("Не всі обов'язкові поля заповнені!")
        
        self.item.movement.id_user = (await self.get_state(AppState)).user.login

        flag, text, id = IssueDAO.edit_one(self.item)
        if flag:
            return [
                rx.toast.success(text),
                rx.redirect(f"{routes.MOVEMENT_ISSUES_VIEW_ID}{id}"),
            ]
        return rx.toast.error(text)

    # ======================


class IssueState(rx.State):
    class Pages:
        ADD = "add"
        EDIT = "edit"
        VIEW = "view"
        LIST = "list"
        NONE = "none"

    current_page: str = Pages.NONE

    isseues_list_state: Optional[ListIssueState]
    issues_add_state: Optional[AddIssueState]
    issues_view_state: Optional[ViewIssueState]
    issues_edit_state: Optional[EditIssueState]

    async def _check_path(self):
        page = self.router.page.params.get("page", "")
        if page != "":
            id = -1

            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                return rx.redirect(routes.MOVEMENT_ISSUES)

            # /issues/add
            if page == self.Pages.ADD:
                if self.issues_add_state is None:
                    return [
                        rx.redirect(routes.MOVEMENT_ISSUES),
                        rx.toast.error(
                            "Состояние добавления выдачи не инициализировано"
                        ),
                    ]
                await self.issues_add_state.on_load()
                self.current_page = self.Pages.ADD
                return None
            # /issues/edit/[id]
            elif page == self.Pages.EDIT:
                id = self.router.page.params.get("id", "")
                if id != "":
                    if self.issues_edit_state is None:
                        return [
                            rx.redirect(routes.MOVEMENT_ISSUES),
                            rx.toast.error(
                                "Состояние редактирования выдачи не инициализировано"
                            ),
                        ]
                    await self.issues_edit_state.on_load(id)
                    self.issues_edit_state.products_selector_state.set_view_mode(True)
                    self.current_page = self.Pages.EDIT
                    return None
                else:
                    return rx.redirect(routes.MOVEMENT_ISSUES)
            # /issues/view/[id]
            elif page == self.Pages.VIEW:
                id = self.router.page.params.get("id", "")
                if id != "":
                    if self.issues_view_state is None:
                        return [
                            rx.redirect(routes.MOVEMENT_ISSUES),
                            rx.toast.error(
                                "Состояние просмотра выдачи не инициализировано"
                            ),
                        ]
                    await self.issues_view_state.on_load(id)
                    self.current_page = self.Pages.VIEW
                    return None
                else:
                    return rx.redirect(routes.MOVEMENT_ISSUES)
        else:
            # /issues
            if self.isseues_list_state is None:
                return [
                    rx.redirect(routes.MOVEMENT_ISSUES),
                    rx.toast.error("Состояние списка выдачи не инициализировано"),
                ]
            self.isseues_list_state.on_load()
            self.current_page = self.Pages.LIST
            return None

    @rx.event
    async def on_load(self):
        self.isseues_list_state = await self.get_state(ListIssueState)
        self.issues_add_state = await self.get_state(AddIssueState)
        self.issues_view_state = await self.get_state(ViewIssueState)
        self.issues_edit_state = await self.get_state(EditIssueState)
        await self._check_path()

    @rx.event
    def delete_one(self, id):
        pass
