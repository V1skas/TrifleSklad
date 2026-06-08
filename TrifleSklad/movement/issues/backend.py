from datetime import date
from typing import List, Optional, Tuple

import reflex as rx

import TrifleSklad.routes as routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.dao import (
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
from TrifleSklad.movement.list_mixin import MovementListFilterMixin
from TrifleSklad.movement.products.backend import ProductsMovementListState
from TrifleSklad.state import AppState


class ListIssueState(MovementListFilterMixin, rx.State):
    items: List[Issue] = []

    # Backend methods
    # ======================
    def _reload(self):
        self._all_pages, self.items = IssueDAO.get_paginated(
            self._current_page,
            self._limit,
            self.filter_date_from,
            self.filter_date_to,
            self.selected_statuses,
        )

    @rx.event
    def on_load(self):
        self._reset_list_state()
        self._reload()

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

    app_state: Optional[AppState] = None

    # Cancel-conflict dialog
    # ======================
    cancel_conflict_movements: List[Movement] = []
    is_cancel_conflict_dialog_open: bool = False
    # ======================

    # Backend only
    # ======================
    @rx.event
    async def on_load(self, id: int):
        self.item = IssueDAO.get_by_id_with_movement_product_storage_owner_recipient(id)
        if self.item is None:
            return [
                rx.redirect(routes.MOVEMENT_ISSUES),
                rx.toast.error("Запис не знайдено!"),
            ]
        self.products_selector_state = await self.get_state(ProductsMovementListState)
        await self.products_selector_state.on_load()
        self.products_selector_state.set_view_mode(True)

        all_products: List[Product] = []
        for product_category in self.item.movement.products_catalog:
            for product in product_category.products:
                product.product_catalog = product_category.product
                all_products.append(product)

        self.products_selector_state.items = all_products

        if self.app_state is None:
            self.app_state = await self.get_state(AppState)

    # ======================

    # Getters for form fields
    # ======================
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
    # ======================

    @rx.event
    def set_cancel_conflict_dialog_open(self, value: bool):
        self.is_cancel_conflict_dialog_open = value


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

    # Формування видачі на основі заявки
    # ======================
    list_requests: List[Tuple[str, str]] = []
    selected_request_id: str = ""
    # позиції заявки для відображення (довідково): (назва, опис к-сті)
    request_positions: List[Tuple[str, str]] = []
    # ======================

    app_state: Optional[AppState] = None

    # Backend only
    # ======================
    def _load_incoming_storages(self):
        self.list_incoming_storages = [
            (item.title, str(item.id))
            for item in StorageDAO.get_all_by_type(StorageType.WAREHOUSE)
        ]

    def _load_destination_storages(self):
        # Призначення видачі — площадка або відділ.
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
        self.selected_request_id = ""
        self.request_positions = []

        self._load_incoming_storages()
        self._load_destination_storages()
        self._load_owners()
        self._load_workers()
        self._load_requests()

        self.products_selector_state = await self.get_state(ProductsMovementListState)
        await self.products_selector_state.on_load()
        self.products_selector_state.set_view_mode(False)
        # При видачі серійний номер ТМЦ обов'язковий для одиниць із серійним номером.
        self.products_selector_state.set_require_serial(True)

        if self.app_state is None:
            self.app_state = await self.get_state(AppState)

    # ======================

    # Формування на основі заявки
    # ======================
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
            return rx.toast.error("Заявку не знайдено!")
        # Предзаповнюємо отримувача та призначення із заявки.
        if request.id_responsible is not None:
            self.item.id_recipient = request.id_responsible
        if request.id_destination_storage is not None:
            self.item.movement.id_destination_storage = request.id_destination_storage
        # Перелік позицій заявки — довідково (заявка має рекомендаційний характер).
        self.request_positions = [
            (
                pc.product.title,
                format_request_qty(pc.count, pc.part_amount, pc.product.unit),
            )
            for pc in request.products_catalog
        ]
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
        self._load_destination_storages()

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

    @rx.var
    def editable_statuses(self) -> List[str]:
        # «Скасовано» виставляється лише кнопкою «Скасувати», не вручну.
        return [
            status
            for index, status in enumerate(movements_status_list)
            if index != MovementsStatus.CANCELED
        ]

    # ======================

    # Action handlers
    # ======================
    @rx.event
    async def add_one(self):
        if not self.app_state.has_permission(ActionEnum.ISSUES_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        if self.item.movement.id_incoming_storage == -1 or self.item.movement.id_incoming_owner == -1 \
            or self.item.id_recipient == -1 or self.products_selector_state is None or len(self.products_selector_state.items) == 0:
            return rx.toast.error("Не всі обов'язкові поля заповнені!")
        if self.item.movement.id_destination_storage == -1:
            return rx.toast.error("Не обрано майданчик призначення!")

        # Серверна перевірка типів місць: видача лише зі складу на площадку/відділ.
        if not StorageDAO.is_type(
            self.item.movement.id_incoming_storage, StorageType.WAREHOUSE
        ):
            return rx.toast.error("Видача можлива лише зі складу!")
        if not StorageDAO.is_type(
            self.item.movement.id_destination_storage,
            (StorageType.TECHNICAL_SITE, StorageType.DEPARTMENT),
        ):
            return rx.toast.error("Видача можлива лише на площадку або відділ!")

        self.item.movement.id_user = (await self.get_state(AppState)).user.login

        # Розділення подільного ТМЦ: підсумковий перелік одиниць (з дочірніми частинами).
        ok, msg, products_list = self.products_selector_state.resolve_movement_products()
        if not ok:
            return rx.toast.error(msg)

        products_catalog: List[ProductCatalog] = []
        movement_products_catalog: List[MovementProductsCatalog] = []

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

        list_id_products: List[int] = [p.id for p in products_list]
        flag, text, id = IssueDAO.add_one(self.item)
        if flag:
            # Зберігаємо серійні номери, введені/уточнені під час видачі.
            serials = {
                p.id: p.serial_number
                for p in products_list
                if p.product_catalog is not None and p.product_catalog.uniq
            }
            ProductDAO.update_serial_numbers(serials)
            # Видача: витратний (неунікальний) ТМЦ списується на місці (спожитий),
            # унікальний (серійний) — переміщується на призначення (відстежуване
            # обладнання). Окремий рух списання не формується.
            ProductDAO.apply_issue_relocation(
                products_list,
                int(self.item.movement.id_destination_owner),
                int(self.item.movement.id_destination_storage),
            )
            # Якщо видача формується на основі заявки — позначаємо її виконаною.
            if self.selected_request_id != "":
                RequestDAO.mark_completed(int(self.selected_request_id), id)
            return [
                rx.toast.success(text),
                rx.redirect(f"{routes.MOVEMENT_ISSUES_VIEW_ID}{id}"),
            ]
        return rx.toast.error(text)

    # ======================


class EditIssueState(rx.State):
    item: Optional[Issue] = None

    # Preloaded lists
    # ======================
    list_incoming_storages: List[Tuple[str, str]] = []
    list_destination_storages: List[Tuple[str, str]] = []
    list_owners: List[Tuple[str, str]] = []
    list_workers: List[Tuple[str, str]] = []
    # ======================

    # Filter fields
    # ======================
    search_name_destination_storage: str = ""
    # ======================

    # Interface logic variables
    # ======================
    is_open_product_dialog: bool = False
    # ======================

    # Nested form states
    # ======================
    products_selector_state: Optional[ProductsMovementListState] = None
    # ======================

    app_state: Optional[AppState] = None

    # Backend only
    # ======================
    def _load_incoming_storages(self):
        self.list_incoming_storages = [
            (item.title, str(item.id))
            for item in StorageDAO.get_all_by_type(StorageType.WAREHOUSE)
        ]

    def _load_destination_storages(self):
        # Призначення видачі — площадка або відділ.
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
    async def on_load(self, id: int):
        self.is_open_product_dialog = False
        self._load_incoming_storages()
        self._load_destination_storages()
        self._load_owners()
        self._load_workers()

        self.item = IssueDAO.get_by_id_with_all_relationship(id)
        if self.item is None:
            return [
                rx.redirect(routes.MOVEMENT_ISSUES),
                rx.toast.error("Запис не знайдено!"),
            ]

        self.products_selector_state = await self.get_state(ProductsMovementListState)
        await self.products_selector_state.on_load()
        self.products_selector_state.set_view_mode(True)

        # Завантажуємо позиції видачі для відображення (склад позицій не редагується).
        all_products: List[Product] = []
        for product_category in self.item.movement.products_catalog:
            for product in product_category.products:
                product.product_catalog = product_category.product
                all_products.append(product)
        self.products_selector_state.items = all_products

        if self.app_state is None:
            self.app_state = await self.get_state(AppState)

    # ======================

    # Getters for form fields
    # ======================
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
        # «Скасовано» виставляється лише кнопкою «Скасувати» (з поверненням залишків).
        return [
            status
            for index, status in enumerate(movements_status_list)
            if index != MovementsStatus.CANCELED
        ]
    # ======================

    # Event handlers for form fields
    # ======================
    @rx.event
    def on_change_search_name_destination_storage(self, value: str):
        self.search_name_destination_storage = value

    @rx.event
    def on_click_search_name_destination_storage(self):
        self._load_destination_storages()

    @rx.event
    def on_change_id_incoming_storage(self, value: str):
        if self.item is None or not value.lstrip("-").isdigit():
            return
        self.item.movement.id_incoming_storage = int(value)
        if self.products_selector_state is not None:
            self.products_selector_state.filter_by_storage = int(value)
            self.products_selector_state.items = []

    @rx.event
    def on_change_id_incoming_owner(self, value: str):
        if self.item is None or not value.lstrip("-").isdigit():
            return
        self.item.movement.id_incoming_owner = int(value)
        self.item.movement.id_destination_owner = int(value)
        if self.products_selector_state is not None:
            self.products_selector_state.filter_by_owner = int(value)
            self.products_selector_state.items = []

    @rx.event
    def on_change_id_destination_storage(self, value: str):
        if self.item is not None and value.lstrip("-").isdigit():
            self.item.movement.id_destination_storage = int(value)

    @rx.event
    def on_change_id_recipient(self, value: str):
        if self.item is not None and value.lstrip("-").isdigit():
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
        if self.item is not None:
            self.item.movement.date = value

    @rx.event
    def on_change_comment(self, value: str):
        if self.item is not None:
            self.item.movement.comment = value

    @rx.event
    def on_close_product_dialog(self):
        self.is_open_product_dialog = False
    # ======================

    # Action handlers
    # ======================
    @rx.event
    async def edit_one(self):
        if not self.app_state.has_permission(ActionEnum.ISSUES_EDIT):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        if self.item is None:
            return rx.toast.error("Запис не завантажено!")
        if self.item.movement.id_incoming_storage == -1 or self.item.movement.id_incoming_owner == -1 \
            or self.item.id_recipient == -1 or self.products_selector_state is None or len(self.products_selector_state.items) == 0:
            return rx.toast.error("Не всі обов'язкові поля заповнені!")
        if self.item.movement.status == MovementsStatus.CANCELED:
            return rx.toast.error("Скасування виконується кнопкою «Скасувати», а не через редагування!")

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

    current_page: str = Pages.LIST
    app_state: Optional[AppState] = None

    def _check_path(self):
        page = self.router.page.params.get("page", "")
        if page != "":
            id = -1
            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                yield rx.redirect(routes.MOVEMENT_ISSUES)
                return

            if page == self.Pages.ADD:
                if not self.app_state.has_permission(ActionEnum.ISSUES_CREATE):
                    yield rx.redirect(routes.WELCOME)
                    return
                yield AddIssueState.on_load()
            elif page == self.Pages.EDIT:
                if not self.app_state.has_permission(ActionEnum.ISSUES_EDIT):
                    yield rx.redirect(routes.WELCOME)
                    return
                id = self.router.page.params.get("id", "")
                if id != "":
                    yield EditIssueState.on_load(int(id))
                else:
                    yield rx.redirect(routes.MOVEMENT_ISSUES)
                    return
            elif page == self.Pages.VIEW:
                if not self.app_state.has_permission(ActionEnum.ISSUES_VIEW):
                    yield rx.redirect(routes.WELCOME)
                    return
                id = self.router.page.params.get("id", "")
                if id != "":
                    yield ViewIssueState.on_load(int(id))
                else:
                    yield rx.redirect(routes.MOVEMENT_ISSUES)
                    return

            self.current_page = page
        else:
            if not self.app_state.has_permission(ActionEnum.ISSUES_LIST):
                yield rx.redirect(routes.WELCOME)
                return
            yield ListIssueState.on_load()
            self.current_page = self.Pages.LIST

    @rx.event
    async def on_load(self):
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
        return self._check_path()

    @rx.event
    async def delete_one(self):
        if not self.app_state.has_permission(ActionEnum.ISSUES_DELETE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")

        view_state = await self.get_state(ViewIssueState)
        if view_state.item is None or view_state.products_selector_state is None:
            return rx.toast.error("Не обрано запис для скасування!")
        if view_state.item.movement.status == MovementsStatus.CANCELED:
            return rx.toast.error("Видачу вже скасовано!")

        list_id_products: List[int] = [
            p.id for p in view_state.products_selector_state.items
        ]

        # Якщо товар бере участь у пізніших рухах — скасування заборонено.
        # Показуємо перелік усіх рухів із цим товаром, починаючи з поточного.
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

        # Витратний (неунікальний) ТМЦ при видачі списувався (is_deleted) —
        # повертаємо його в обіг.
        ProductDAO.undelete_list(list_id_products)
        # Скасування видачі повертає кожну одиницю ТМЦ туди, куди її привів
        # попередній рух (за наскрізним номером), а не просто на склад відправлення.
        MovementDAO.restore_products_to_previous_location(
            list_id_products, view_state.item.id
        )
        # Якщо видача була сформована за заявкою — повертаємо заявку у стан «Нова».
        RequestDAO.revert_completion_by_movement(view_state.item.id)
        return [
            rx.toast.success("Видачу скасовано!"),
            rx.redirect(f"{routes.MOVEMENT_ISSUES_VIEW_ID}{view_state.item.id}"),
        ]
