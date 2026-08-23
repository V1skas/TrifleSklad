from datetime import date
from typing import Dict, List, Optional, Tuple

import reflex as rx

import TrifleSklad.routes as routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.dao_legacy import (
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
    format_amount,
    format_request_qty,
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
from TrifleSklad.states.app import AppState
from TrifleSklad.states.audit_mixin import AuditHistoryMixin
from TrifleSklad.utils.clock import now_local

# Типи заявки, які підтримуються (відділи/площадки = виды видачі).
REQUEST_TYPE_OPTIONS = [
    (str(MovementsType.ISSUE), movements_type_list[MovementsType.ISSUE]),
    (str(MovementsType.SALE), movements_type_list[MovementsType.SALE]),
]


class ListRequestsState(AppState):
    items: List[Request] = []

    _current_page: int = 1
    _all_pages: int = 1
    _limit: int = 20

    is_filter_open: bool = False
    selected_statuses: List[int] = [RequestStatus.NEW]

    can_see_all: bool = False

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

    def _reload(self):
        author = None if self.can_see_all else self.user.login
        self._all_pages, self.items = RequestDAO.get_paginated(
            self._current_page, self._limit, self.selected_statuses, author
        )

    @rx.event
    def on_load(self):
        if not (self.has_permission(ActionEnum.REQUESTS_LIST) or self.has_permission(ActionEnum.REQUESTS_CREATE)):
            yield rx.redirect(routes.WELCOME)
            yield rx.toast.error("У Вас немає дозволу на перегляд цієї сторінки!")
            return
        self.can_see_all = self.has_permission(ActionEnum.REQUESTS_LIST)
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

    @rx.event
    def on_click_add(self):
        return rx.redirect(routes.CATALOG_REQUESTS_ADD)


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
    # довідник характеристик каталогу: id -> (divisible, capacity, unit)
    _catalog_info: Dict[int, Tuple[bool, float, str]] = {}

    new_position_catalog: str = ""
    new_position_count: str = "1"
    new_position_part: str = ""
    is_position_dialog_open: bool = False
    # позиції: (id каталогу, назва, к-сть цілих, частина)
    positions: List[Tuple[int, str, int, int]] = []

    def _load_form_lists(self):
        self.list_workers = [(w.fio, str(w.id)) for w in WorkerDAO.get_all()]
        destinations = StorageDAO.get_all_by_type(
            StorageType.TECHNICAL_SITE
        ) + StorageDAO.get_all_by_type(StorageType.DEPARTMENT)
        self.list_destinations = [(s.title, str(s.id)) for s in destinations]
        catalog = ProductCatalogDAO.get_all()
        self.list_catalog = [(p.title, str(p.id)) for p in catalog]
        self._catalog_info = {
            p.id: (p.divisible, p.capacity, p.unit) for p in catalog
        }

    @rx.var
    def is_issue_type(self) -> bool:
        return self.request_type == str(MovementsType.ISSUE)

    @rx.var
    def type_options(self) -> List[Tuple[str, str]]:
        return REQUEST_TYPE_OPTIONS

    @rx.var
    def has_positions(self) -> bool:
        return len(self.positions) > 0

    @rx.var
    def new_position_is_divisible(self) -> bool:
        if self.new_position_catalog == "":
            return False
        info = self._catalog_info.get(int(self.new_position_catalog))
        return info[0] if info is not None else False

    @rx.var
    def new_position_capacity(self) -> float:
        if self.new_position_catalog == "":
            return 0
        info = self._catalog_info.get(int(self.new_position_catalog))
        return info[1] if info is not None else 0

    @rx.var
    def new_position_capacity_label(self) -> str:
        return format_amount(self.new_position_capacity)

    @rx.var
    def new_position_unit(self) -> str:
        if self.new_position_catalog == "":
            return ""
        info = self._catalog_info.get(int(self.new_position_catalog))
        return info[2] if info is not None else ""

    @rx.var
    def new_position_no_fixed_capacity(self) -> bool:
        # Подільний без опорної ємності (capacity == 0) — частину задати не можна,
        # заявка формується лише цілими одиницями.
        return self.new_position_is_divisible and self.new_position_capacity == 0

    @rx.var
    def positions_rows(self) -> List[Tuple[int, str, str]]:
        result: List[Tuple[int, str, str]] = []
        for index, (cid, title, count, part) in enumerate(self.positions):
            info = self._catalog_info.get(cid)
            unit = info[2] if info is not None else ""
            result.append((index, title, format_request_qty(count, part, unit)))
        return result

    @rx.event
    def set_request_type(self, value: str):
        self.request_type = value

    @rx.event
    def set_id_responsible(self, value: str):
        self.id_responsible = value

    @rx.event
    def set_id_destination_storage(self, value: str):
        self.id_destination_storage = value

    @rx.event
    def set_comment(self, value: str):
        self.comment = value

    @rx.event
    def open_position_dialog(self):
        self.new_position_catalog = ""
        self.new_position_count = "1"
        self.new_position_part = ""
        self.is_position_dialog_open = True

    @rx.event
    def set_position_dialog_open(self, value: bool):
        self.is_position_dialog_open = value

    @rx.event
    def set_new_position_catalog(self, value: str):
        self.new_position_catalog = value
        self.new_position_count = "1"
        self.new_position_part = ""

    @rx.event
    def set_new_position_count(self, value: str):
        self.new_position_count = value

    @rx.event
    def set_new_position_part(self, value: str):
        self.new_position_part = value

    @rx.event
    def add_position(self):
        if self.new_position_catalog == "":
            return rx.toast.error("Оберіть позицію!")
        catalog_id = int(self.new_position_catalog)
        if any(p[0] == catalog_id for p in self.positions):
            return rx.toast.error("Цю позицію вже додано!")

        info = self._catalog_info.get(catalog_id)
        divisible = info[0] if info is not None else False
        capacity = info[1] if info is not None else 0

        count = int(self.new_position_count) if self.new_position_count.isdigit() else 0
        part = int(self.new_position_part) if self.new_position_part.isdigit() else 0

        if divisible:
            # Без фіксованої ємності частина не застосовна — лише цілі одиниці.
            if capacity == 0:
                part = 0
            if part != 0 and (part < 1 or (capacity > 0 and part >= capacity)):
                return rx.toast.error(
                    f"Частина має бути від 1 до {capacity - 1}!"
                    if capacity > 0
                    else "Невірний обсяг частини!"
                )
            if count <= 0 and part <= 0:
                return rx.toast.error("Вкажіть кількість цілих одиниць або частину!")
            if count < 0:
                return rx.toast.error("Невірна кількість цілих одиниць!")
        else:
            if count <= 0:
                return rx.toast.error("Кількість має бути більше нуля!")
            part = 0

        title = next((t for t, cid in self.list_catalog if cid == str(catalog_id)), "")
        self.positions = self.positions + [(catalog_id, title, count, part)]
        self.new_position_catalog = ""
        self.new_position_count = "1"
        self.new_position_part = ""
        self.is_position_dialog_open = False

    @rx.event
    def remove_position(self, index: int):
        self.positions = [p for i, p in enumerate(self.positions) if i != index]

    def _build_positions(self) -> List[RequestProductsCatalog]:
        return [
            RequestProductsCatalog(id_product_catalog=cid, count=count, part_amount=(part or None))
            for cid, _title, count, part in self.positions
        ]

    def _validate(self) -> Optional[str]:
        if len(self.positions) == 0:
            return "Додайте хоча б одну позицію ТМЦ!"
        if self.is_issue_type and self.id_responsible == "":
            return "Для видачі оберіть отримувача!"
        if self.is_issue_type and self.id_destination_storage == "":
            return "Для видачі оберіть призначення!"
        return None


class AddRequestsState(_RequestFormState, AppState):
    @rx.event
    def on_load(self):
        if not self.has_permission(ActionEnum.REQUESTS_CREATE):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        self.request_type = str(MovementsType.ISSUE)
        self.id_responsible = ""
        self.id_destination_storage = ""
        self.comment = ""
        self.new_position_catalog = ""
        self.new_position_count = "1"
        self.new_position_part = ""
        self.positions = []
        self._load_form_lists()

    @rx.event
    def on_save(self):
        if not self.has_permission(ActionEnum.REQUESTS_CREATE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        error = self._validate()
        if error is not None:
            yield rx.toast.error(error)
            return

        is_issue = self.is_issue_type
        request = Request(
            type=int(self.request_type),
            id_author=self.user.login,
            id_responsible=int(self.id_responsible) if is_issue and self.id_responsible else None,
            id_destination_storage=int(self.id_destination_storage) if is_issue and self.id_destination_storage else None,
            date=now_local().date().__str__(),
            comment=self.comment or None,
            status=RequestStatus.NEW,
            products_catalog=self._build_positions(),
        )
        flag, text, id = RequestDAO.add_one(request, self.user.login)
        if flag:
            yield rx.toast.success(text)
            yield ListRequestsState.on_load()
            yield rx.redirect(routes.CATALOG_REQUESTS_VIEW_ID + str(id), replace=True)
        else:
            yield rx.toast.error(text)


class EditRequestsState(_RequestFormState, AppState):
    item: Optional[Request] = None

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(ActionEnum.REQUESTS_EDIT):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        self.item = RequestDAO.get_by_id_with_relationships(int(id))
        if self.item is None:
            yield rx.redirect(routes.CATALOG_REQUESTS)
            yield rx.toast.error("Заявку не знайдено!")
            return
        if self.item.status == RequestStatus.COMPLETED:
            yield rx.redirect(routes.CATALOG_REQUESTS_VIEW_ID + id)
            yield rx.toast.error("Виконану заявку не можна редагувати!")
            return

        self._load_form_lists()
        self.request_type = str(self.item.type)
        self.id_responsible = str(self.item.id_responsible) if self.item.id_responsible else ""
        self.id_destination_storage = (
            str(self.item.id_destination_storage) if self.item.id_destination_storage else ""
        )
        self.comment = self.item.comment or ""
        self.positions = [
            (pc.id_product_catalog, pc.product.title, pc.count, pc.part_amount or 0)
            for pc in self.item.products_catalog
        ]
        self.new_position_catalog = ""
        self.new_position_count = "1"
        self.new_position_part = ""

    @rx.event
    def on_save(self):
        if not self.has_permission(ActionEnum.REQUESTS_EDIT):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None:
            yield rx.toast.error("Заявку не завантажено!")
            return
        error = self._validate()
        if error is not None:
            yield rx.toast.error(error)
            return

        is_issue = self.is_issue_type
        form_data = {
            "id": self.item.id,
            "type": int(self.request_type),
            "id_responsible": int(self.id_responsible) if is_issue and self.id_responsible else None,
            "id_destination_storage": int(self.id_destination_storage) if is_issue and self.id_destination_storage else None,
            "comment": self.comment or None,
            "positions": [(cid, count, part) for cid, _title, count, part in self.positions],
        }
        flag, text, id = RequestDAO.edit_one(form_data, self.user.login)
        if flag:
            yield rx.toast.success(text)
            yield ListRequestsState.on_load()
            yield rx.redirect(routes.CATALOG_REQUESTS_VIEW_ID + str(id), replace=True)
        else:
            yield rx.toast.error(text)


class ViewRequestsState(AuditHistoryMixin, AppState):
    HISTORY_TABLE = "requests"
    HISTORY_ACTION = ActionEnum.REQUESTS_HISTORY
    HISTORY_DETAIL_ACTION = ActionEnum.REQUESTS_HISTORY_DETAIL

    item: Optional[Request] = None
    in_process: bool = True

    @rx.var
    def type_title(self) -> str:
        return movements_type_list.get(self.item.type, "—") if self.item is not None else ""

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
        return self.item.responsible.fio if self.item is not None and self.item.responsible is not None else "—"

    @rx.var
    def destination_name(self) -> str:
        return (
            self.item.destination_storage.title
            if self.item is not None and self.item.destination_storage is not None
            else "—"
        )

    @rx.var
    def positions_rows(self) -> List[Tuple[str, str]]:
        if self.item is None:
            return []
        return [
            (pc.product.title, format_request_qty(pc.count, pc.part_amount, pc.product.unit))
            for pc in self.item.products_catalog
        ]

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
            and self.has_permission(ActionEnum.REQUESTS_PROCESS)
        )

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(ActionEnum.REQUESTS_VIEW):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        self.in_process = True
        self.item = RequestDAO.get_by_id_with_relationships(int(id))
        self.in_process = False
        if self.item is None:
            yield rx.redirect(routes.CATALOG_REQUESTS)
            yield rx.toast.error("Заявку не знайдено!")
            return
        self._load_history(self.item.id)

    @rx.event
    def on_click_edit(self):
        if self.item is None:
            return
        return rx.redirect(routes.CATALOG_REQUESTS_EDIT_ID + str(self.item.id))

    @rx.event
    def on_click_process(self):
        if self.item is None:
            return
        return rx.redirect(routes.CATALOG_REQUESTS_PROCESS_ID + str(self.item.id))

    @rx.event
    def on_click_delete(self):
        if not self.has_permission(ActionEnum.REQUESTS_DELETE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None:
            return
        flag, text = RequestDAO.delete_one(self.item.id, self.user.login)
        if flag:
            yield rx.toast.success(text)
            yield ListRequestsState.on_load()
            yield rx.redirect(routes.CATALOG_REQUESTS)
        else:
            yield rx.toast.error(text)


class ProcessRequestsState(AppState):
    """Обробка заявки оператором: формування виданого/проданого руху ТМЦ.
    Оператор обирає склад/власника (+ ціни для продажу), конкретні одиниці,
    система перевіряє відповідність позиціям заявки і створює рух, після чого
    заявка позначається виконаною та зв'язується зі створеним рухом."""

    item: Optional[Request] = None
    in_process: bool = True
    id_incoming_storage: str = ""
    id_incoming_owner: str = ""
    id_responsible: str = ""  # для продажу — відповідальний оператор

    list_storages: List[Tuple[str, str]] = []
    list_owners: List[Tuple[str, str]] = []
    list_workers: List[Tuple[str, str]] = []

    _products_state: Optional[ProductsMovementListState] = None

    @rx.var
    def is_issue(self) -> bool:
        return self.item is not None and self.item.type == MovementsType.ISSUE

    @rx.var
    def type_title(self) -> str:
        return movements_type_list.get(self.item.type, "—") if self.item is not None else ""

    @rx.var
    def destination_name(self) -> str:
        return (
            self.item.destination_storage.title
            if self.item is not None and self.item.destination_storage is not None
            else "—"
        )

    @rx.var
    def responsible_name(self) -> str:
        return self.item.responsible.fio if self.item is not None and self.item.responsible is not None else "—"

    @rx.var
    def required_rows(self) -> List[Tuple[str, str]]:
        if self.item is None:
            return []
        return [
            (pc.product.title, format_request_qty(pc.count, pc.part_amount, pc.product.unit))
            for pc in self.item.products_catalog
        ]

    @rx.event
    async def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(ActionEnum.REQUESTS_PROCESS):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        self.in_process = True
        self.item = RequestDAO.get_by_id_with_relationships(int(id))
        if self.item is None:
            self.in_process = False
            yield rx.redirect(routes.CATALOG_REQUESTS)
            yield rx.toast.error("Заявку не знайдено!")
            return
        if self.item.status == RequestStatus.COMPLETED:
            self.in_process = False
            yield rx.redirect(routes.CATALOG_REQUESTS_VIEW_ID + id)
            yield rx.toast.error("Заявку вже виконано!")
            return

        self.id_incoming_storage = ""
        self.id_incoming_owner = ""
        self.id_responsible = ""
        self.list_storages = [(s.title, str(s.id)) for s in StorageDAO.get_all_by_type(StorageType.WAREHOUSE)]
        self.list_owners = [(o.title, str(o.id)) for o in OwnerDAO.get_all()]
        self.list_workers = [(w.fio, str(w.id)) for w in WorkerDAO.get_all()]

        self._products_state = await self.get_state(ProductsMovementListState)
        self._products_state.items = []
        await self._products_state.on_load()
        self._products_state.set_view_mode(False)
        # видача → обов'язковий s/n; продаж → ціни за позиції.
        if self.is_issue:
            self._products_state.set_require_serial(True)
        else:
            self._products_state.set_require_price(True)
        self.in_process = False

    @rx.event
    def set_id_incoming_storage(self, value: str):
        self.id_incoming_storage = value
        if self._products_state is not None:
            self._products_state.filter_by_storage = int(value) if value != "" else -1
            self._products_state.items = []

    @rx.event
    def set_id_incoming_owner(self, value: str):
        self.id_incoming_owner = value
        if self._products_state is not None:
            self._products_state.filter_by_owner = int(value) if value != "" else -1
            self._products_state.items = []

    @rx.event
    def set_id_responsible(self, value: str):
        self.id_responsible = value

    @rx.event
    async def process(self):
        if not self.has_permission(ActionEnum.REQUESTS_PROCESS):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None:
            yield rx.toast.error("Заявку не завантажено!")
            return
        if self.id_incoming_storage == "":
            yield rx.toast.error("Оберіть склад!")
            return
        if self.id_incoming_owner == "":
            yield rx.toast.error("Оберіть власника!")
            return
        if not self.is_issue and self.id_responsible == "":
            yield rx.toast.error("Оберіть відповідального за продаж!")
            return
        if self._products_state is None or len(self._products_state.items) == 0:
            yield rx.toast.error("Оберіть одиниці ТМЦ!")
            return

        # Серверна перевірка типів місць: рух лише зі складу; видача — на площадку/відділ.
        if not StorageDAO.is_type(int(self.id_incoming_storage), StorageType.WAREHOUSE):
            yield rx.toast.error("Рух можливий лише зі складу!")
            return
        if self.is_issue and not StorageDAO.is_type(
            self.item.id_destination_storage, (StorageType.TECHNICAL_SITE, StorageType.DEPARTMENT)
        ):
            yield rx.toast.error("Видача можлива лише на площадку або відділ!")
            return

        ok, msg, products_list = self._products_state.resolve_movement_products()
        if not ok:
            yield rx.toast.error(msg)
            return

        # Заявка має рекомендаційний характер: відповідність обраних одиниць
        # позиціям заявки не блокує формування руху (оператор видає фактично
        # наявне). Перелік «Потрібно за заявкою» показано для довідки.

        login = self.user.login
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
                    date=now_local().date().__str__(),
                    comment=self.item.comment,
                    status=MovementsStatus.CREATED,
                    total_cost=0.0,
                    products_catalog=movement_products_catalog,
                ),
            )
            flag, text, movement_id = IssueDAO.add_one(issue, login)
            if not flag:
                yield rx.toast.error(text)
                return
            serials = {p.id: p.serial_number for p in products_list}
            ProductDAO.update_serial_numbers(serials)
            # Видача: витратний (неунікальний) ТМЦ списується на місці (спожитий),
            # унікальний (серійний) — переміщується на призначення.
            ProductDAO.apply_issue_relocation(
                products_list, int(self.id_incoming_owner), int(self.item.id_destination_storage)
            )
        else:
            prices = self._products_state.get_prices()
            positions = {p.id_product_catalog for p in products_list}
            for catalog_id in positions:
                if prices.get(catalog_id, 0.0) <= 0:
                    yield rx.toast.error("Вкажіть вартість для кожної позиції!")
                    return
            form_data = {
                "id_responsible": int(self.id_responsible),
                "date": now_local().date().__str__(),
                "id_incoming_storage": int(self.id_incoming_storage),
                "id_incoming_owner": int(self.id_incoming_owner),
                "status": MovementsStatus.CREATED,
                "comment": self.item.comment,
                "movement_products_list": products_list,
                "prices": prices,
                "id_user": login,
            }
            flag, text, movement_id = SaleDAO.add_one(form_data, login)
            if not flag:
                yield rx.toast.error(text)
                return
            serials = {p.id: p.serial_number for p in products_list}
            ProductDAO.update_serial_numbers(serials)
            ProductDAO.delete_list(list_id_products)

        RequestDAO.mark_completed(self.item.id, movement_id, login)
        yield rx.toast.success("Заявку виконано, рух сформовано!")
        yield rx.redirect(routes.CATALOG_REQUESTS_VIEW_ID + str(self.item.id), replace=True)

    def _group_products(self, products_list) -> List[MovementProductsCatalog]:
        catalog_ids: List[int] = []
        for product in products_list:
            if product.id_product_catalog not in catalog_ids:
                catalog_ids.append(product.id_product_catalog)
        result: List[MovementProductsCatalog] = []
        for catalog_id in catalog_ids:
            mpc = MovementProductsCatalog(id_product_catalog=catalog_id, count=0, products=[])
            for product in products_list:
                if product.id_product_catalog == catalog_id:
                    mpc.products.append(product)
                    mpc.count += 1
            result.append(mpc)
        return result
