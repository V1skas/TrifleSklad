from datetime import date
from typing import List, Optional, Tuple

import reflex as rx

import TrifleSklad.routes as routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.dao import (
    IssueDAO,
    OwnerDAO,
    ProductCatalogDAO,
    ProductDAO,
    RequestDAO,
    SaleDAO,
    StorageDAO,
    WorkerDAO,
)
from TrifleSklad.declared import (
    MovementsStatus,
    MovementsType,
    RequestStatus,
    StorageType,
    movements_type_list,
    request_status_list,
)
from TrifleSklad.models import (
    Issue,
    Movement,
    MovementProductsCatalog,
    Request,
    RequestProductsCatalog,
)
from TrifleSklad.movement.products.backend import ProductsMovementListState
from TrifleSklad.state import AppState

# Типи заявки, які підтримуються (відділи/площадки = виды видачі).
REQUEST_TYPE_OPTIONS = [
    (str(MovementsType.ISSUE), movements_type_list[MovementsType.ISSUE]),
    (str(MovementsType.SALE), movements_type_list[MovementsType.SALE]),
]


class ListRequestsState(rx.State):
    items: List[Request] = []

    _current_page: int = 1
    _all_pages: int = 1
    _limit: int = 20

    is_filter_open: bool = False
    selected_statuses: List[int] = [RequestStatus.NEW]

    can_see_all: bool = False
    app_state: Optional[AppState] = None

    # Vars
    # ======================
    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def get_items(self) -> List[Tuple[int, Request]]:
        return [(index, item) for index, item in enumerate(self.items)]

    @rx.var
    def get_current_page(self) -> str:
        return str(self._current_page)

    @rx.var
    def get_all_pages(self) -> str:
        return str(self._all_pages)

    @rx.var
    def statuses_for_filter(self) -> List[Tuple[int, str, bool]]:
        return [
            (index, name, index in self.selected_statuses)
            for index, name in enumerate(request_status_list)
        ]

    @rx.var
    def status_titles(self) -> List[str]:
        return request_status_list

    @rx.var
    def type_titles(self) -> dict:
        return movements_type_list
    # ======================

    def _reload(self):
        author = None if self.can_see_all else self.app_state.user.login
        self._all_pages, self.items = RequestDAO.get_paginated(
            self._current_page, self._limit, self.selected_statuses, author
        )

    # Event handlers
    # ======================
    @rx.event
    async def on_load(self):
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
        self.can_see_all = self.app_state.has_permission(ActionEnum.REQUESTS_LIST)
        self._current_page = 1
        self.is_filter_open = False
        self.selected_statuses = [RequestStatus.NEW]
        self._reload()

    @rx.event
    def toggle_filter(self):
        self.is_filter_open = not self.is_filter_open

    @rx.event
    def set_status(self, index: int, checked: bool):
        if checked and index not in self.selected_statuses:
            self.selected_statuses = self.selected_statuses + [index]
        elif not checked and index in self.selected_statuses:
            self.selected_statuses = [s for s in self.selected_statuses if s != index]

    @rx.event
    def apply_filters(self):
        self._current_page = 1
        self._reload()

    @rx.event
    def reset_filters(self):
        self.selected_statuses = [RequestStatus.NEW]
        self._current_page = 1
        self._reload()

    @rx.event
    def current_page_increment(self):
        if self._current_page + 1 <= self._all_pages:
            self._current_page += 1
            self._reload()

    @rx.event
    def current_page_decrement(self):
        if self._current_page > 1:
            self._current_page -= 1
            self._reload()

    @rx.event
    def on_change_current_page(self, value: str):
        if value != "" and value.isdigit() and 0 < int(value) <= self._all_pages:
            self._current_page = int(value)
            self._reload()
    # ======================


class _RequestFormState(rx.State, mixin=True):
    """Спільна логіка форм заявки (додавання/редагування): тип, отримувач,
    призначення, коментар і перелік позицій каталогу."""

    request_type: str = str(MovementsType.ISSUE)
    id_responsible: str = ""
    id_destination_storage: str = ""
    comment: str = ""

    list_workers: List[Tuple[str, str]] = []
    list_destinations: List[Tuple[str, str]] = []
    list_catalog: List[Tuple[str, str]] = []

    new_position_catalog: str = ""
    new_position_count: str = "1"
    # позиції: (id каталогу, назва, кількість)
    positions: List[Tuple[int, str, int]] = []

    def _load_form_lists(self):
        self.list_workers = [(w.fio, str(w.id)) for w in WorkerDAO.get_all()]
        destinations = StorageDAO.get_all_by_type(
            StorageType.TECHNICAL_SITE
        ) + StorageDAO.get_all_by_type(StorageType.DEPARTMENT)
        self.list_destinations = [(s.title, str(s.id)) for s in destinations]
        self.list_catalog = [(p.title, str(p.id)) for p in ProductCatalogDAO.get_all()]

    @rx.var
    def is_issue_type(self) -> bool:
        return self.request_type == str(MovementsType.ISSUE)

    @rx.var
    def type_options(self) -> List[Tuple[str, str]]:
        return REQUEST_TYPE_OPTIONS

    @rx.var
    def has_positions(self) -> bool:
        return len(self.positions) > 0

    @rx.event
    def on_change_type(self, value: str):
        self.request_type = value

    @rx.event
    def on_change_responsible(self, value: str):
        self.id_responsible = value

    @rx.event
    def on_change_destination(self, value: str):
        self.id_destination_storage = value

    @rx.event
    def on_change_comment(self, value: str):
        self.comment = value

    @rx.event
    def on_change_new_position_catalog(self, value: str):
        self.new_position_catalog = value

    @rx.event
    def on_change_new_position_count(self, value: str):
        self.new_position_count = value

    @rx.event
    def add_position(self):
        if self.new_position_catalog == "" or not self.new_position_count.isdigit():
            return rx.toast.error("Оберіть позицію та вкажіть кількість!")
        catalog_id = int(self.new_position_catalog)
        count = int(self.new_position_count)
        if count <= 0:
            return rx.toast.error("Кількість має бути більше нуля!")
        if any(p[0] == catalog_id for p in self.positions):
            return rx.toast.error("Цю позицію вже додано!")
        title = next((t for cid, t in self.list_catalog if cid == str(catalog_id)), "")
        self.positions = self.positions + [(catalog_id, title, count)]
        self.new_position_catalog = ""
        self.new_position_count = "1"

    @rx.event
    def remove_position(self, index: int):
        self.positions = [p for i, p in enumerate(self.positions) if i != index]

    def _build_positions(self) -> List[RequestProductsCatalog]:
        return [
            RequestProductsCatalog(id_product_catalog=cid, count=count)
            for cid, _title, count in self.positions
        ]

    def _validate(self) -> Optional[str]:
        if len(self.positions) == 0:
            return "Додайте хоча б одну позицію ТМЦ!"
        if self.is_issue_type and (
            self.id_responsible == "" or self.id_destination_storage == ""
        ):
            return "Для видачі оберіть отримувача та призначення!"
        return None


class AddRequestsState(_RequestFormState, rx.State):
    app_state: Optional[AppState] = None

    @rx.event
    async def on_load(self):
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
        self.request_type = str(MovementsType.ISSUE)
        self.id_responsible = ""
        self.id_destination_storage = ""
        self.comment = ""
        self.new_position_catalog = ""
        self.new_position_count = "1"
        self.positions = []
        self._load_form_lists()

    @rx.event
    def add_one(self):
        if not self.app_state.has_permission(ActionEnum.REQUESTS_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        error = self._validate()
        if error is not None:
            return rx.toast.error(error)

        is_issue = self.is_issue_type
        request = Request(
            type=int(self.request_type),
            id_author=self.app_state.user.login,
            id_responsible=int(self.id_responsible) if is_issue and self.id_responsible else None,
            id_destination_storage=int(self.id_destination_storage)
            if is_issue and self.id_destination_storage
            else None,
            date=date.today().__str__(),
            comment=self.comment or None,
            status=RequestStatus.NEW,
            products_catalog=self._build_positions(),
        )
        flag, text, id = RequestDAO.add_one(request)
        if flag:
            return [
                rx.toast.success(text),
                rx.redirect(f"{routes.CATALOG_REQUESTS_VIEW_ID}{id}"),
            ]
        return rx.toast.error(text)


class EditRequestsState(_RequestFormState, rx.State):
    item: Optional[Request] = None
    app_state: Optional[AppState] = None

    @rx.event
    async def on_load(self, id: int):
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
        self.item = RequestDAO.get_by_id_with_relationships(id)
        if self.item is None:
            return [
                rx.redirect(routes.CATALOG_REQUESTS),
                rx.toast.error("Заявку не знайдено!"),
            ]
        if self.item.status == RequestStatus.COMPLETED:
            return [
                rx.redirect(f"{routes.CATALOG_REQUESTS_VIEW_ID}{id}"),
                rx.toast.error("Виконану заявку не можна редагувати!"),
            ]

        self._load_form_lists()
        self.request_type = str(self.item.type)
        self.id_responsible = (
            str(self.item.id_responsible) if self.item.id_responsible else ""
        )
        self.id_destination_storage = (
            str(self.item.id_destination_storage)
            if self.item.id_destination_storage
            else ""
        )
        self.comment = self.item.comment or ""
        self.positions = [
            (pc.id_product_catalog, pc.product.title, pc.count)
            for pc in self.item.products_catalog
        ]
        self.new_position_catalog = ""
        self.new_position_count = "1"

    @rx.event
    def edit_one(self):
        if not self.app_state.has_permission(ActionEnum.REQUESTS_EDIT):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        if self.item is None:
            return rx.toast.error("Заявку не завантажено!")
        error = self._validate()
        if error is not None:
            return rx.toast.error(error)

        is_issue = self.is_issue_type
        form_data = {
            "id": self.item.id,
            "type": int(self.request_type),
            "id_responsible": int(self.id_responsible)
            if is_issue and self.id_responsible
            else None,
            "id_destination_storage": int(self.id_destination_storage)
            if is_issue and self.id_destination_storage
            else None,
            "comment": self.comment or None,
            "positions": [(cid, count) for cid, _title, count in self.positions],
        }
        flag, text, id = RequestDAO.edit_one(form_data)
        if flag:
            return [
                rx.toast.success(text),
                rx.redirect(f"{routes.CATALOG_REQUESTS_VIEW_ID}{id}"),
            ]
        return rx.toast.error(text)


class ViewRequestsState(rx.State):
    item: Optional[Request] = None
    app_state: Optional[AppState] = None

    # Vars
    # ======================
    @rx.var
    def type_title(self) -> str:
        return (
            movements_type_list.get(self.item.type, "—") if self.item is not None else ""
        )

    @rx.var
    def status_title(self) -> str:
        return request_status_list[self.item.status] if self.item is not None else ""

    @rx.var
    def comment_display(self) -> str:
        return self.item.comment if self.item is not None and self.item.comment else "—"

    @rx.var
    def is_completed(self) -> bool:
        return self.item is not None and self.item.status == RequestStatus.COMPLETED

    @rx.var
    def author_name(self) -> str:
        if self.item is None or self.item.author is None:
            return "—"
        if self.item.author.worker is not None:
            return self.item.author.worker.fio
        return self.item.author.login

    @rx.var
    def responsible_name(self) -> str:
        return (
            self.item.responsible.fio
            if self.item is not None and self.item.responsible is not None
            else "—"
        )

    @rx.var
    def destination_name(self) -> str:
        return (
            self.item.destination_storage.title
            if self.item is not None and self.item.destination_storage is not None
            else "—"
        )

    @rx.var
    def positions_rows(self) -> List[Tuple[str, int]]:
        if self.item is None:
            return []
        return [(pc.product.title, pc.count) for pc in self.item.products_catalog]

    @rx.var
    def movement_link(self) -> str:
        if self.item is None or self.item.id_movement is None:
            return ""
        return routes.movement_view_url(self.item.type, self.item.id_movement)

    @rx.var
    def can_process(self) -> bool:
        return (
            self.item is not None
            and self.item.status == RequestStatus.NEW
            and self.app_state is not None
            and self.app_state.has_permission(ActionEnum.REQUESTS_PROCESS)
        )
    # ======================

    @rx.event
    async def on_load(self, id: int):
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
        self.item = RequestDAO.get_by_id_with_relationships(id)
        if self.item is None:
            return [
                rx.redirect(routes.CATALOG_REQUESTS),
                rx.toast.error("Заявку не знайдено!"),
            ]


class ProcessRequestsState(rx.State):
    """Обробка заявки оператором: формування виданого/проданого руху ТМЦ.
    Оператор обирає склад/власника (+ ціни для продажу), конкретні одиниці,
    система перевіряє відповідність позиціям заявки і створює рух, після чого
    заявка позначається виконаною та зв'язується зі створеним рухом."""

    item: Optional[Request] = None
    id_incoming_storage: str = ""
    id_incoming_owner: str = ""
    id_responsible: str = ""  # для продажу — відповідальний оператор

    list_storages: List[Tuple[str, str]] = []
    list_owners: List[Tuple[str, str]] = []
    list_workers: List[Tuple[str, str]] = []

    products_state: Optional[ProductsMovementListState] = None
    app_state: Optional[AppState] = None

    # Vars
    # ======================
    @rx.var
    def is_issue(self) -> bool:
        return self.item is not None and self.item.type == MovementsType.ISSUE

    @rx.var
    def type_title(self) -> str:
        return (
            movements_type_list.get(self.item.type, "—") if self.item is not None else ""
        )

    @rx.var
    def destination_name(self) -> str:
        return (
            self.item.destination_storage.title
            if self.item is not None and self.item.destination_storage is not None
            else "—"
        )

    @rx.var
    def responsible_name(self) -> str:
        return (
            self.item.responsible.fio
            if self.item is not None and self.item.responsible is not None
            else "—"
        )

    @rx.var
    def required_rows(self) -> List[Tuple[str, int]]:
        if self.item is None:
            return []
        return [(pc.product.title, pc.count) for pc in self.item.products_catalog]
    # ======================

    @rx.event
    async def on_load(self, id: int):
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
        self.item = RequestDAO.get_by_id_with_relationships(id)
        if self.item is None:
            return [
                rx.redirect(routes.CATALOG_REQUESTS),
                rx.toast.error("Заявку не знайдено!"),
            ]
        if self.item.status == RequestStatus.COMPLETED:
            return [
                rx.redirect(f"{routes.CATALOG_REQUESTS_VIEW_ID}{id}"),
                rx.toast.error("Заявку вже виконано!"),
            ]

        self.id_incoming_storage = ""
        self.id_incoming_owner = ""
        self.id_responsible = ""
        self.list_storages = [
            (s.title, str(s.id))
            for s in StorageDAO.get_all_by_type(StorageType.WAREHOUSE)
        ]
        self.list_owners = [(o.title, str(o.id)) for o in OwnerDAO.get_all()]
        self.list_workers = [(w.fio, str(w.id)) for w in WorkerDAO.get_all()]

        self.products_state = await self.get_state(ProductsMovementListState)
        self.products_state.items = []
        await self.products_state.on_load()
        self.products_state.set_view_mode(False)
        # видача → обов'язковий s/n; продаж → ціни за позиції.
        if self.is_issue:
            self.products_state.set_require_serial(True)
        else:
            self.products_state.set_require_price(True)

    @rx.event
    def on_change_id_incoming_storage(self, value: str):
        self.id_incoming_storage = value
        if self.products_state is not None:
            self.products_state.filter_by_storage = int(value) if value != "" else -1
            self.products_state.items = []

    @rx.event
    def on_change_id_incoming_owner(self, value: str):
        self.id_incoming_owner = value
        if self.products_state is not None:
            self.products_state.filter_by_owner = int(value) if value != "" else -1
            self.products_state.items = []

    @rx.event
    def on_change_id_responsible(self, value: str):
        self.id_responsible = value

    def _check_positions_match(self, products_list) -> Optional[str]:
        # Кількість обраних одиниць за позицією каталогу має дорівнювати замовленій.
        required = {pc.id_product_catalog: pc.count for pc in self.item.products_catalog}
        selected = {}
        for p in products_list:
            selected[p.id_product_catalog] = selected.get(p.id_product_catalog, 0) + 1
        for catalog_id, count in required.items():
            if selected.get(catalog_id, 0) != count:
                title = next(
                    (pc.product.title for pc in self.item.products_catalog
                     if pc.id_product_catalog == catalog_id),
                    str(catalog_id),
                )
                return (
                    f"За позицією «{title}» потрібно {count} од., "
                    f"обрано {selected.get(catalog_id, 0)}."
                )
        for catalog_id in selected:
            if catalog_id not in required:
                return "Обрано ТМЦ, якого немає в заявці."
        return None

    @rx.event
    async def process(self):
        if not self.app_state.has_permission(ActionEnum.REQUESTS_PROCESS):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        if self.item is None:
            return rx.toast.error("Заявку не завантажено!")
        if self.id_incoming_storage == "" or self.id_incoming_owner == "":
            return rx.toast.error("Оберіть склад і власника!")
        if not self.is_issue and self.id_responsible == "":
            return rx.toast.error("Оберіть відповідального за продаж!")
        if self.products_state is None or len(self.products_state.items) == 0:
            return rx.toast.error("Оберіть одиниці ТМЦ!")

        ok, msg, products_list = self.products_state.resolve_movement_products()
        if not ok:
            return rx.toast.error(msg)

        mismatch = self._check_positions_match(products_list)
        if mismatch is not None:
            return rx.toast.error(mismatch)

        login = self.app_state.user.login
        list_id_products = [p.id for p in products_list]

        if self.is_issue:
            movement_products_catalog = self._group_products(products_list)
            issue = Issue(
                id_recipient=self.item.id_responsible,
                movement=Movement(
                    type=MovementsType.ISSUE,
                    id_user=login,
                    id_incoming_storage=int(self.id_incoming_storage),
                    id_incoming_owner=int(self.id_incoming_owner),
                    id_destination_storage=self.item.id_destination_storage,
                    id_destination_owner=int(self.id_incoming_owner),
                    date=date.today().__str__(),
                    comment=self.item.comment,
                    status=MovementsStatus.CREATED,
                    total_cost=0.0,
                    products_catalog=movement_products_catalog,
                ),
            )
            flag, text, movement_id = IssueDAO.add_one(issue)
            if not flag:
                return rx.toast.error(text)
            serials = {p.id: p.serial_number for p in products_list}
            ProductDAO.update_serial_numbers(serials)
            ProductDAO.update_owner_storage(
                list_id_products,
                int(self.id_incoming_owner),
                int(self.item.id_destination_storage),
            )
        else:
            prices = self.products_state.get_prices()
            positions = {p.id_product_catalog for p in products_list}
            for catalog_id in positions:
                if prices.get(catalog_id, 0.0) <= 0:
                    return rx.toast.error("Вкажіть вартість для кожної позиції!")
            form_data = {
                "id_responsible": int(self.id_responsible),
                "date": date.today().__str__(),
                "id_incoming_storage": int(self.id_incoming_storage),
                "id_incoming_owner": int(self.id_incoming_owner),
                "status": MovementsStatus.CREATED,
                "comment": self.item.comment,
                "movement_products_list": products_list,
                "prices": prices,
                "id_user": login,
            }
            flag, text, movement_id = SaleDAO.add_one(form_data)
            if not flag:
                return rx.toast.error(text)
            serials = {p.id: p.serial_number for p in products_list}
            ProductDAO.update_serial_numbers(serials)
            ProductDAO.delete_list(list_id_products)

        RequestDAO.mark_completed(self.item.id, movement_id)
        return [
            rx.toast.success("Заявку виконано, рух сформовано!"),
            rx.redirect(f"{routes.CATALOG_REQUESTS_VIEW_ID}{self.item.id}"),
        ]

    def _group_products(self, products_list) -> List[MovementProductsCatalog]:
        catalog_ids: List[int] = []
        for product in products_list:
            if product.id_product_catalog not in catalog_ids:
                catalog_ids.append(product.id_product_catalog)
        result: List[MovementProductsCatalog] = []
        for catalog_id in catalog_ids:
            mpc = MovementProductsCatalog(
                id_product_catalog=catalog_id, count=0, products=[]
            )
            for product in products_list:
                if product.id_product_catalog == catalog_id:
                    mpc.products.append(product)
                    mpc.count += 1
            result.append(mpc)
        return result


class RequestsState(rx.State):
    class Pages:
        ADD = "add"
        EDIT = "edit"
        VIEW = "view"
        PROCESS = "process"
        LIST = "list"

    current_page: str = Pages.LIST
    app_state: Optional[AppState] = None

    def _check_path(self):
        page = self.router.page.params.get("page", "")
        if page != "":
            if page not in [
                self.Pages.ADD,
                self.Pages.EDIT,
                self.Pages.VIEW,
                self.Pages.PROCESS,
            ]:
                yield rx.redirect(routes.CATALOG_REQUESTS)
                return

            if page == self.Pages.ADD:
                if not self.app_state.has_permission(ActionEnum.REQUESTS_CREATE):
                    yield rx.redirect(routes.WELCOME)
                    return
                yield AddRequestsState.on_load()
            elif page == self.Pages.EDIT:
                if not self.app_state.has_permission(ActionEnum.REQUESTS_EDIT):
                    yield rx.redirect(routes.WELCOME)
                    return
                id = self.router.page.params.get("id", "")
                if id != "":
                    yield EditRequestsState.on_load(int(id))
                else:
                    yield rx.redirect(routes.CATALOG_REQUESTS)
                    return
            elif page == self.Pages.VIEW:
                if not self.app_state.has_permission(ActionEnum.REQUESTS_VIEW):
                    yield rx.redirect(routes.WELCOME)
                    return
                id = self.router.page.params.get("id", "")
                if id != "":
                    yield ViewRequestsState.on_load(int(id))
                else:
                    yield rx.redirect(routes.CATALOG_REQUESTS)
                    return
            elif page == self.Pages.PROCESS:
                if not self.app_state.has_permission(ActionEnum.REQUESTS_PROCESS):
                    yield rx.redirect(routes.WELCOME)
                    return
                id = self.router.page.params.get("id", "")
                if id != "":
                    yield ProcessRequestsState.on_load(int(id))
                else:
                    yield rx.redirect(routes.CATALOG_REQUESTS)
                    return

            self.current_page = page
        else:
            if not (
                self.app_state.has_permission(ActionEnum.REQUESTS_LIST)
                or self.app_state.has_permission(ActionEnum.REQUESTS_CREATE)
            ):
                yield rx.redirect(routes.WELCOME)
                return
            yield ListRequestsState.on_load()
            self.current_page = self.Pages.LIST

    @rx.event
    async def on_load(self):
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
        return self._check_path()

    @rx.event
    async def delete_one(self, id: int):
        if not self.app_state.has_permission(ActionEnum.REQUESTS_DELETE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        flag, text = RequestDAO.delete_one(id)
        if flag:
            return [rx.toast.success(text), rx.redirect(routes.CATALOG_REQUESTS)]
        return rx.toast.error(text)
