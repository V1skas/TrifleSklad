from typing import List, Optional, Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.dao_legacy import MovementDAO, OwnerDAO, ProductDAO, StorageDAO
from TrifleSklad.declared import (
    MovementsStatus,
    MovementsType,
    StorageType,
    movements_status_list,
    movements_type_list,
)
from TrifleSklad.models import Movement, Product
from TrifleSklad.movement.inline_creators import LookupCreatorsMixin
from TrifleSklad.movement.list_mixin import MovementListFilterMixin
from TrifleSklad.movement.products.backend import ProductsMovementListState
from TrifleSklad.states.app import AppState
from TrifleSklad.states.audit_mixin import AuditHistoryMixin
from TrifleSklad.utils.clock import now_local


class ListMovementsState(MovementListFilterMixin, AppState):
    items: List[Movement] = []
    in_progress: bool = True

    def _reload(self):
        self._all_pages, self.items = MovementDAO.get_by_type_paginated(
            MovementsType.MOVEMENT,
            self._current_page,
            self._limit,
            self._date_from_eff(),
            self._date_to_eff(),
            self.selected_statuses,
            incoming_storage=self.filter_incoming_storage,
            destination_storage=self.filter_destination_storage,
            incoming_owner=self.filter_incoming_owner,
            destination_owner=self.filter_destination_owner,
        )

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list

    @rx.event
    def on_load(self):
        if not self.has_permission(Action.MOVEMENTS_LIST):
            yield rx.redirect(routes.WELCOME)
            yield rx.toast.error("У Вас немає дозволу на перегляд цієї сторінки!")
            return
        self.in_progress = True
        self._reset_list_state()
        self._reload()
        self.in_progress = False

    @rx.event
    def on_click_add(self):
        return rx.redirect(routes.MOVEMENT_MOVEMENTS_ADD)


class ViewMovementsState(AuditHistoryMixin, AppState):
    HISTORY_TABLE = "movements"
    HISTORY_ACTION = Action.MOVEMENTS_HISTORY
    HISTORY_DETAIL_ACTION = Action.MOVEMENTS_HISTORY_DETAIL

    item: Optional[Movement] = None
    in_process: bool = True

    _products_movement_list_state: Optional[ProductsMovementListState] = None

    cancel_conflict_movements: List[Movement] = []
    is_cancel_conflict_dialog_open: bool = False

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

    @rx.event
    def set_cancel_conflict_dialog_open(self, value: bool):
        self.is_cancel_conflict_dialog_open = value

    @rx.event
    async def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(Action.MOVEMENTS_VIEW):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        self.in_process = True
        self.item = MovementDAO.get_by_id_with_product_storage_owner(int(id))
        if self.item is None:
            self.in_process = False
            yield rx.redirect(routes.MOVEMENT_MOVEMENTS)
            yield rx.toast.error("Запис не знайдено!")
            return

        self._products_movement_list_state = await self.get_state(ProductsMovementListState)
        await self._products_movement_list_state.on_load()
        self._products_movement_list_state.set_view_mode(True)

        all_products: List[Product] = []
        for product_category in self.item.products_catalog:
            for product in product_category.products:
                product.product_catalog = product_category.product
                all_products.append(product)
        self._products_movement_list_state.items = all_products
        self._load_history(self.item.id)
        self.in_process = False

    @rx.event
    def on_click_edit(self):
        if self.item is None:
            return
        return rx.redirect(routes.MOVEMENT_MOVEMENTS_EDIT_ID + str(self.item.id))

    @rx.event
    def on_click_cancel(self):
        if not self.has_permission(Action.MOVEMENTS_DELETE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None or self._products_movement_list_state is None:
            yield rx.toast.error("Не обрано запис для скасування!")
            return
        if self.item.status == MovementsStatus.CANCELED:
            yield rx.toast.error("Переміщення вже скасовано!")
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

        MovementDAO.restore_products_to_previous_location(list_id_products, self.item.id)
        yield rx.toast.success("Переміщення скасовано!")
        yield ListMovementsState.on_load()
        yield rx.redirect(f"{routes.MOVEMENT_MOVEMENTS_VIEW_ID}{self.item.id}")


class AddMovementsState(LookupCreatorsMixin, AppState):
    current_date: str = ""

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

    _products_movement_list_state: Optional[ProductsMovementListState] = None

    def _load_list_storages(self):
        self.list_storages = [
            (item.title, str(item.id))
            for item in StorageDAO.get_all_by_type(StorageType.WAREHOUSE)
        ]

    def _load_list_owners(self):
        self.list_owners = [(item.title, str(item.id)) for item in OwnerDAO.get_all()]

    def _status_index(self) -> int:
        for index, status_text in enumerate(movements_status_list):
            if status_text == self.status:
                return index
        return MovementsStatus.CREATED

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

    @rx.var
    def editable_statuses(self) -> List[str]:
        return [
            status
            for index, status in enumerate(movements_status_list)
            if index != MovementsStatus.CANCELED
        ]

    @rx.event
    async def on_load(self):
        if not self.has_permission(Action.MOVEMENTS_CREATE):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return

        self.current_date = now_local().date().__str__()
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

        self._products_movement_list_state = await self.get_state(ProductsMovementListState)
        self._products_movement_list_state.items = []
        await self._products_movement_list_state.on_load()
        self._products_movement_list_state.set_view_mode(False)
        self._products_movement_list_state.set_show_serial(True)

        default_storage = StorageDAO.get_default_id(StorageType.WAREHOUSE)
        if default_storage is not None:
            self.id_incoming_storage = str(default_storage)
            self._products_movement_list_state.filter_by_storage = default_storage
        default_owner = OwnerDAO.get_default_id()
        if default_owner is not None:
            self.id_incoming_owner = str(default_owner)
            self.id_destination_owner = str(default_owner)
            self._products_movement_list_state.filter_by_owner = default_owner

    @rx.event
    def on_change_id_incoming_storage(self, value: str):
        self.id_incoming_storage = value
        if self._products_movement_list_state is not None:
            self._products_movement_list_state.filter_by_storage = int(value) if value != "" else -1
            self._products_movement_list_state.items = []

    @rx.event
    def on_change_id_incoming_owner(self, value: str):
        self.id_incoming_owner = value
        if self._products_movement_list_state is not None:
            self._products_movement_list_state.filter_by_owner = int(value) if value != "" else -1
            self._products_movement_list_state.items = []

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

    def _after_create_storage(self, new_id: int):
        self._load_list_storages()
        if self.st_slot == "incoming":
            self.id_incoming_storage = str(new_id)
            if self._products_movement_list_state is not None:
                self._products_movement_list_state.filter_by_storage = new_id
                self._products_movement_list_state.items = []
        else:
            self.id_destination_storage = str(new_id)

    def _after_create_owner(self, new_id: int):
        self._load_list_owners()
        if self.owner_slot == "incoming":
            self.id_incoming_owner = str(new_id)
            if self._products_movement_list_state is not None:
                self._products_movement_list_state.filter_by_owner = new_id
                self._products_movement_list_state.items = []
        else:
            self.id_destination_owner = str(new_id)

    async def _reset_for_continue(self):
        keep = dict(
            current_date=self.current_date,
            id_incoming_storage=self.id_incoming_storage,
            id_incoming_owner=self.id_incoming_owner,
            id_destination_storage=self.id_destination_storage,
            id_destination_owner=self.id_destination_owner,
            status=self.status,
        )
        self.search_name_incoming_storage = ""
        self.search_name_destination_storage = ""
        self.comment = ""

        self.current_date = keep["current_date"]
        self.id_incoming_storage = keep["id_incoming_storage"]
        self.id_incoming_owner = keep["id_incoming_owner"]
        self.id_destination_storage = keep["id_destination_storage"]
        self.id_destination_owner = keep["id_destination_owner"]
        self.status = keep["status"]

        self._load_list_storages()
        self._load_list_owners()

        self._products_movement_list_state.items = []
        await self._products_movement_list_state.on_load()
        self._products_movement_list_state.set_view_mode(False)
        self._products_movement_list_state.set_show_serial(True)
        if keep["id_incoming_storage"] != "":
            self._products_movement_list_state.filter_by_storage = int(keep["id_incoming_storage"])
        if keep["id_incoming_owner"] != "":
            self._products_movement_list_state.filter_by_owner = int(keep["id_incoming_owner"])

    @rx.event
    async def add_one(self, keep: bool = False):
        if not self.has_permission(Action.MOVEMENTS_CREATE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.id_incoming_storage == "":
            yield rx.toast.error("Не обрано склад відправлення!")
            return
        if self.id_incoming_owner == "":
            yield rx.toast.error("Не обрано власника відправлення!")
            return
        if self.id_destination_storage == "":
            yield rx.toast.error("Не обрано склад призначення!")
            return
        if self.id_destination_owner == "":
            yield rx.toast.error("Не обрано власника призначення!")
            return
        if not StorageDAO.is_type(int(self.id_incoming_storage), StorageType.WAREHOUSE) \
                or not StorageDAO.is_type(int(self.id_destination_storage), StorageType.WAREHOUSE):
            yield rx.toast.error("Переміщення можливе лише між складами!")
            return
        if self._products_movement_list_state is None or len(self._products_movement_list_state.items) == 0:
            yield rx.toast.error("Список товарів для переміщення порожній!")
            return

        ok, msg, products_list = self._products_movement_list_state.resolve_movement_products()
        if not ok:
            yield rx.toast.error(msg)
            return

        form_data = {
            "type": MovementsType.MOVEMENT,
            "date": self.current_date,
            "id_incoming_storage": int(self.id_incoming_storage),
            "id_incoming_owner": int(self.id_incoming_owner),
            "id_destination_storage": int(self.id_destination_storage),
            "id_destination_owner": int(self.id_destination_owner),
            "status": self._status_index(),
            "comment": self.comment,
            "movement_products_list": products_list,
            "id_user": self.user.login,
        }

        list_id_products: List[int] = [p.id for p in products_list]
        flag, text, id = MovementDAO.add_one(form_data, self.user.login)
        if flag:
            serials = {
                p.id: p.serial_number
                for p in products_list
                if p.product_catalog is not None and p.product_catalog.uniq
                and p.serial_number not in (None, "")
            }
            ProductDAO.update_serial_numbers(serials)
            ProductDAO.update_owner_storage(
                list_id_products,
                int(self.id_destination_owner),
                int(self.id_destination_storage),
            )
            if keep:
                await self._reset_for_continue()
                yield rx.toast.success("Переміщення проведено!")
                return
            yield rx.toast.success("Переміщення проведено!")
            yield ListMovementsState.on_load()
            yield rx.redirect(f"{routes.MOVEMENT_MOVEMENTS_VIEW_ID}{id}")
            return
        yield rx.toast.error(text)


class EditMovementsState(AppState):
    item: Optional[Movement] = None
    in_process: bool = True

    id_incoming_storage: str = ""
    id_incoming_owner: str = ""
    search_name_incoming_storage: str = ""

    id_destination_storage: str = ""
    id_destination_owner: str = ""
    search_name_destination_storage: str = ""
    status: str = ""

    list_storages: List[Tuple[str, str]] = []
    list_owners: List[Tuple[str, str]] = []

    _products_movement_list_state: Optional[ProductsMovementListState] = None

    def _load_list_storages(self):
        self.list_storages = [(item.title, str(item.id)) for item in StorageDAO.get_all()]

    def _load_list_owners(self):
        self.list_owners = [(item.title, str(item.id)) for item in OwnerDAO.get_all()]

    def _status_index(self) -> int:
        for index, status_text in enumerate(movements_status_list):
            if status_text == self.status:
                return index
        return MovementsStatus.CREATED

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
        if not self.has_permission(Action.MOVEMENTS_EDIT):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return

        self.in_process = True
        self.search_name_incoming_storage = ""
        self.search_name_destination_storage = ""

        self.item = MovementDAO.get_by_id_with_product_storage_owner(int(id))
        if self.item is None:
            self.in_process = False
            yield rx.redirect(routes.MOVEMENT_MOVEMENTS)
            yield rx.toast.error("Запис не знайдено!")
            return

        self.id_incoming_storage = str(self.item.id_incoming_storage)
        self.id_incoming_owner = str(self.item.id_incoming_owner)
        self.id_destination_storage = str(self.item.id_destination_storage)
        self.id_destination_owner = str(self.item.id_destination_owner)
        self.status = movements_status_list[self.item.status]

        self._load_list_storages()
        self._load_list_owners()

        self._products_movement_list_state = await self.get_state(ProductsMovementListState)
        await self._products_movement_list_state.on_load()
        self._products_movement_list_state.set_view_mode(True)

        all_products: List[Product] = []
        for product_category in self.item.products_catalog:
            for product in product_category.products:
                product.product_catalog = product_category.product
                all_products.append(product)
        self._products_movement_list_state.items = all_products
        self.in_process = False

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
        if not self.has_permission(Action.MOVEMENTS_EDIT):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None:
            yield rx.toast.error("Запис не завантажено!")
            return
        if self.item.status == MovementsStatus.CANCELED:
            yield rx.toast.error("Переміщення вже скасовано!")
            return

        status_index = self._status_index()
        if status_index == MovementsStatus.CANCELED:
            yield rx.toast.error(
                "Скасування виконується кнопкою «Скасувати», а не через редагування!"
            )
            return

        form_data = {
            "id": self.item.id,
            "status": status_index,
            "comment": self.item.comment,
        }
        flag, text, id = MovementDAO.edit_one(form_data, self.user.login)
        if flag:
            yield rx.toast.success("Переміщення змінено!")
            yield ListMovementsState.on_load()
            yield rx.redirect(f"{routes.MOVEMENT_MOVEMENTS_VIEW_ID}{id}")
            return
        yield rx.toast.error(text)
