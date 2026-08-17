from typing import List, Optional, Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.dao_legacy import MovementDAO, ProductDAO, StorageDAO
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
from TrifleSklad.services.errors import ServiceError
from TrifleSklad.services.movement_edit import FullEditPayload, MovementEditService
from TrifleSklad.states.app import AppState
from TrifleSklad.states.audit_mixin import AuditHistoryMixin
from TrifleSklad.states.movement_edit_mixin import FullEditMixin
from TrifleSklad.utils.clock import now_local


class ListReturnsState(MovementListFilterMixin, AppState):
    items: List[Movement] = []
    in_progress: bool = True

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

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list

    @rx.event
    def on_load(self):
        if not self.has_permission(Action.RETURNS_LIST):
            yield rx.redirect(routes.WELCOME)
            yield rx.toast.error("У Вас немає дозволу на перегляд цієї сторінки!")
            return
        self.in_progress = True
        self._reset_list_state()
        self._reload()
        self.in_progress = False

    @rx.event
    def on_click_add(self):
        return rx.redirect(routes.MOVEMENT_RETURNS_ADD)


class ViewReturnsState(AuditHistoryMixin, AppState):
    HISTORY_TABLE = "returns"
    HISTORY_ACTION = Action.RETURNS_HISTORY
    HISTORY_DETAIL_ACTION = Action.RETURNS_HISTORY_DETAIL

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
        if not self.has_permission(Action.RETURNS_VIEW):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        self.in_process = True
        self.item = MovementDAO.get_by_id_with_product_storage_owner(int(id))
        if self.item is None:
            self.in_process = False
            yield rx.redirect(routes.MOVEMENT_RETURNS)
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
        return rx.redirect(routes.MOVEMENT_RETURNS_EDIT_ID + str(self.item.id))

    @rx.event
    def on_click_cancel(self):
        if not self.has_permission(Action.RETURNS_DELETE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None or self._products_movement_list_state is None:
            yield rx.toast.error("Не обрано запис для скасування!")
            return
        if self.item.status == MovementsStatus.CANCELED:
            yield rx.toast.error("Повернення вже скасовано!")
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
        yield rx.toast.success("Повернення скасовано!")
        yield ListReturnsState.on_load()
        yield rx.redirect(f"{routes.MOVEMENT_RETURNS_VIEW_ID}{self.item.id}")


class AddReturnsState(LookupCreatorsMixin, AppState):
    current_date: str = ""

    id_incoming_storage: str = ""
    id_destination_storage: str = ""
    status: str = ""
    comment: str = ""

    list_source_storages: List[Tuple[str, str]] = []
    list_destination_storages: List[Tuple[str, str]] = []

    _products_movement_list_state: Optional[ProductsMovementListState] = None

    def _load_storages(self):
        sources = (
            StorageDAO.get_all_by_type(StorageType.TECHNICAL_SITE)
            + StorageDAO.get_all_by_type(StorageType.DEPARTMENT)
            + StorageDAO.get_all_by_type(StorageType.CLIENT)
        )
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
        if not self.has_permission(Action.RETURNS_CREATE):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return

        self.current_date = now_local().date().__str__()
        self.id_incoming_storage = ""
        self.id_destination_storage = ""
        self.status = ""
        self.comment = ""

        self._load_storages()

        self._products_movement_list_state = await self.get_state(ProductsMovementListState)
        self._products_movement_list_state.items = []
        await self._products_movement_list_state.on_load()
        self._products_movement_list_state.set_view_mode(False)
        self._products_movement_list_state.set_require_owner(False)

        default_storage = StorageDAO.get_default_id(StorageType.WAREHOUSE)
        if default_storage is not None:
            self.id_destination_storage = str(default_storage)

    @rx.event
    def on_change_id_incoming_storage(self, value: str):
        self.id_incoming_storage = value
        if self._products_movement_list_state is not None:
            self._products_movement_list_state.filter_by_storage = int(value) if value != "" else -1
            self._products_movement_list_state.items = []

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

    def _after_create_storage(self, new_id: int):
        self._load_storages()
        if self.st_slot == "incoming":
            self.id_incoming_storage = str(new_id)
            if self._products_movement_list_state is not None:
                self._products_movement_list_state.filter_by_storage = new_id
                self._products_movement_list_state.items = []
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

        self._products_movement_list_state.items = []
        await self._products_movement_list_state.on_load()
        self._products_movement_list_state.set_view_mode(False)
        self._products_movement_list_state.set_require_owner(False)
        if keep["id_incoming_storage"] != "":
            self._products_movement_list_state.filter_by_storage = int(keep["id_incoming_storage"])

    @rx.event
    async def add_one(self, keep: bool = False):
        if not self.has_permission(Action.RETURNS_CREATE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.id_incoming_storage == "":
            yield rx.toast.error("Не обрано місце повернення!")
            return
        if self.id_destination_storage == "":
            yield rx.toast.error("Не обрано склад призначення!")
            return
        if self._products_movement_list_state is None or len(self._products_movement_list_state.items) == 0:
            yield rx.toast.error("Список товарів для повернення порожній!")
            return

        if not StorageDAO.is_type(
            int(self.id_incoming_storage),
            (StorageType.TECHNICAL_SITE, StorageType.DEPARTMENT, StorageType.CLIENT),
        ):
            yield rx.toast.error("Повернення можливе лише з площадки, відділу або клієнта!")
            return
        if not StorageDAO.is_type(int(self.id_destination_storage), StorageType.WAREHOUSE):
            yield rx.toast.error("Повертати ТМЦ можна лише на склад!")
            return

        ok, msg, products_list = self._products_movement_list_state.resolve_movement_products()
        if not ok:
            yield rx.toast.error(msg)
            return

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
            "id_user": self.user.login,
        }

        list_id_products: List[int] = [p.id for p in products_list]
        flag, text, id = MovementDAO.add_one(form_data, self.user.login)
        if flag:
            ProductDAO.update_storage(list_id_products, int(self.id_destination_storage))
            if keep:
                await self._reset_for_continue()
                yield rx.toast.success("Повернення проведено!")
                return
            yield rx.toast.success("Повернення проведено!")
            yield ListReturnsState.on_load()
            yield rx.redirect(f"{routes.MOVEMENT_RETURNS_VIEW_ID}{id}", replace=True)
            return
        yield rx.toast.error(text)


class EditReturnsState(FullEditMixin, AppState):
    MOVEMENT_TYPE = MovementsType.RETURN

    item: Optional[Movement] = None
    in_process: bool = True
    status: str = ""

    id_incoming_storage: str = ""
    id_destination_storage: str = ""

    list_source_storages: List[Tuple[str, str]] = []
    list_destination_storages: List[Tuple[str, str]] = []

    _products_movement_list_state: Optional[ProductsMovementListState] = None

    def _load_storages(self):
        sources = (
            StorageDAO.get_all_by_type(StorageType.TECHNICAL_SITE)
            + StorageDAO.get_all_by_type(StorageType.DEPARTMENT)
            + StorageDAO.get_all_by_type(StorageType.CLIENT)
        )
        self.list_source_storages = [(s.title, str(s.id)) for s in sources]
        self.list_destination_storages = [
            (s.title, str(s.id)) for s in StorageDAO.get_all_by_type(StorageType.WAREHOUSE)
        ]

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
    async def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(Action.RETURNS_EDIT):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return

        self.in_process = True
        self.item = MovementDAO.get_by_id_with_product_storage_owner(int(id))
        if self.item is None:
            self.in_process = False
            yield rx.redirect(routes.MOVEMENT_RETURNS)
            yield rx.toast.error("Запис не знайдено!")
            return
        self.status = movements_status_list[self.item.status]
        self.id_incoming_storage = str(self.item.id_incoming_storage)
        self.id_destination_storage = str(self.item.id_destination_storage)

        self._load_storages()
        self._load_editability(self.item.id)

        self._products_movement_list_state = await self.get_state(ProductsMovementListState)
        await self._products_movement_list_state.on_load()
        self._products_movement_list_state.set_view_mode(not self.can_edit_full)
        # Повернення не задає власника — фільтр лише за місцем, кожна одиниця
        # зберігає свого власника.
        self._products_movement_list_state.set_require_owner(False)
        self._products_movement_list_state.filter_by_storage = self.item.id_incoming_storage

        all_products: List[Product] = []
        for product_category in self.item.products_catalog:
            for product in product_category.products:
                product.product_catalog = product_category.product
                all_products.append(product)
        self._products_movement_list_state.prefill_for_edit(all_products)
        self.in_process = False

    @rx.event
    def on_change_id_incoming_storage(self, value: str):
        if not self.can_edit_full:
            return
        self.id_incoming_storage = value
        if self._products_movement_list_state is not None:
            self._products_movement_list_state.filter_by_storage = int(value)
            self._products_movement_list_state.items = []
        yield rx.toast.warning("Перелік ТМЦ очищено — оберіть одиниці на новому місці!")

    @rx.event
    def on_change_id_destination_storage(self, value: str):
        if not self.can_edit_full:
            return
        self.id_destination_storage = value

    @rx.event
    def on_change_status(self, value: str):
        self.status = value

    @rx.event
    def on_change_comment(self, value: str):
        if self.item is not None:
            self.item.comment = value

    @rx.event
    def edit_one(self):
        if not self.has_permission(Action.RETURNS_EDIT):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None:
            yield rx.toast.error("Запис не завантажено!")
            return
        if self.item.status == MovementsStatus.CANCELED:
            yield rx.toast.error("Повернення вже скасовано!")
            return

        status_index = self._status_index()
        if status_index == MovementsStatus.CANCELED:
            yield rx.toast.error(
                "Скасування виконується кнопкою «Скасувати», а не через редагування!"
            )
            return

        if self.can_edit_full:
            error = self._require_reason()
            if error is not None:
                yield rx.toast.error(error)
                return
            if not StorageDAO.is_type(
                int(self.id_incoming_storage),
                (StorageType.TECHNICAL_SITE, StorageType.DEPARTMENT, StorageType.CLIENT),
            ):
                yield rx.toast.error("Повернення можливе лише з площадки, відділу або клієнта!")
                return
            if not StorageDAO.is_type(int(self.id_destination_storage), StorageType.WAREHOUSE):
                yield rx.toast.error("Повертати ТМЦ можна лише на склад!")
                return
            flag, text, plan = self._products_movement_list_state.collect_unit_plan()
            if not flag:
                yield rx.toast.error(text)
                return
            if len(plan) == 0:
                yield rx.toast.error("Оберіть ТМЦ для повернення!")
                return
            try:
                MovementEditService().save_full(
                    FullEditPayload(
                        movement_id=self.item.id,
                        movement_type=MovementsType.RETURN,
                        reason=self.edit_reason,
                        header={
                            "id_incoming_storage": int(self.id_incoming_storage),
                            "id_destination_storage": int(self.id_destination_storage),
                            "status": status_index,
                            "comment": self.item.comment,
                        },
                        unit_plan=plan,
                    ),
                    self.user.login,
                )
            except ServiceError as e:
                yield rx.toast.error(str(e))
                return
            yield rx.toast.success("Повернення змінено!")
            yield ListReturnsState.on_load()
            yield rx.redirect(f"{routes.MOVEMENT_RETURNS_VIEW_ID}{self.item.id}", replace=True)
            return

        form_data = {
            "id": self.item.id,
            "status": status_index,
            "comment": self.item.comment,
        }
        flag, text, id = MovementDAO.edit_one(form_data, self.user.login)
        if flag:
            yield rx.toast.success("Повернення змінено!")
            yield ListReturnsState.on_load()
            yield rx.redirect(f"{routes.MOVEMENT_RETURNS_VIEW_ID}{id}", replace=True)
            return
        yield rx.toast.error(text)
