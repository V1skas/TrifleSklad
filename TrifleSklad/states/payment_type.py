from typing import Optional, Sequence

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.models import PaymentType
from TrifleSklad.services.errors import ServiceError
from TrifleSklad.services.payment_type import PaymentTypeService
from TrifleSklad.states.app import AppState
from TrifleSklad.states.audit_mixin import AuditHistoryMixin


class ListPaymentTypeState(AppState):
    items: Optional[Sequence[PaymentType]] = None
    in_progress: bool = True

    @rx.var
    def has_items(self) -> bool:
        return self.items is not None and len(self.items) > 0

    @rx.event
    def on_load(self):
        guard = self.access_guard(Action.PAYMENT_TYPE_LIST)
        if guard is not None:
            yield guard
            return
        try:
            self.in_progress = True
            self.items = PaymentTypeService().get_list_items()
            self.in_progress = False
        except Exception:
            yield rx.toast.error("Під час виконання запиту сталася помилка. Спробуйте знову.")

    @rx.event
    def on_click_add(self):
        return rx.redirect(routes.CATALOG_PAYMENT_TYPES_ADD)


class AddPaymentTypeState(AppState):
    item: PaymentType = PaymentType()
    in_process: bool = False

    @rx.event
    def on_load(self):
        guard = self.access_guard(Action.PAYMENT_TYPE_CREATE)
        if guard is not None:
            yield guard
            return
        self.item = PaymentType()

    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""

    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""

    @rx.var
    def is_default(self) -> bool:
        return bool(self.item.is_default) if self.item is not None else False

    @rx.event
    def set_title(self, value: str):
        self.item.title = value

    @rx.event
    def set_description(self, value: str):
        self.item.description = value if value != "" else None

    @rx.event
    def set_is_default(self, value: bool):
        self.item.is_default = value

    @rx.event
    def on_save(self):
        if not self.has_permission(Action.PAYMENT_TYPE_CREATE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if not self.item.title:
            yield rx.toast.warning("Поле назви повинно бути заповненим!")
            return
        try:
            self.item = PaymentTypeService().add_one(self.item, self.user.login)
            yield rx.toast.success("Тип оплати додано!")
            yield rx.redirect(routes.CATALOG_PAYMENT_TYPES_VIEW_ID + str(self.item.id), replace=True)
        except ServiceError as e:
            yield rx.toast.warning(str(e))
        except Exception:
            yield rx.toast.error("Під час виконання запиту трапилась помилка. Спробуйте ще раз.")


class EditPaymentTypeState(AppState):
    item: PaymentType = PaymentType()
    in_process: bool = False

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        guard = self.access_guard(Action.PAYMENT_TYPE_EDIT)
        if guard is not None:
            yield guard
            return
        try:
            self.in_process = True
            item = PaymentTypeService().get_by_id(int(id))
            if item is None:
                self.in_process = False
                yield rx.redirect(routes.CATALOG_PAYMENT_TYPES)
                yield rx.toast.error("Запис не було знайдено")
                return
            self.item = item
            self.in_process = False
        except Exception:
            self.in_process = False
            yield rx.toast.error("Під час виконання запиту сталася помилка. Спробуйте знову.")

    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""

    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""

    @rx.var
    def is_default(self) -> bool:
        return bool(self.item.is_default) if self.item is not None else False

    @rx.event
    def set_title(self, value: str):
        self.item.title = value

    @rx.event
    def set_description(self, value: str):
        self.item.description = value if value != "" else None

    @rx.event
    def set_is_default(self, value: bool):
        self.item.is_default = value

    @rx.event
    def on_save(self):
        if not self.has_permission(Action.PAYMENT_TYPE_EDIT):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if not self.item.title:
            yield rx.toast.warning("Поле назви повинно бути заповненим!")
            return
        try:
            self.item = PaymentTypeService().edit_one(self.item, self.user.login)
            yield rx.toast.success("Тип оплати змінено!")
            yield rx.redirect(routes.CATALOG_PAYMENT_TYPES_VIEW_ID + str(self.item.id), replace=True)
        except ServiceError as e:
            yield rx.toast.warning(str(e))
        except Exception:
            yield rx.toast.error("Під час виконання запиту трапилась помилка. Спробуйте ще раз.")


class ViewPaymentTypeState(AuditHistoryMixin, AppState):
    HISTORY_TABLE = "payment_types"
    HISTORY_ACTION = Action.PAYMENT_TYPE_HISTORY
    HISTORY_DETAIL_ACTION = Action.PAYMENT_TYPE_HISTORY_DETAIL

    item: Optional[PaymentType] = None
    in_process: bool = True

    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""

    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""

    @rx.var
    def is_default(self) -> bool:
        return bool(self.item.is_default) if self.item is not None else False

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        guard = self.access_guard(Action.PAYMENT_TYPE_VIEW)
        if guard is not None:
            yield guard
            return
        try:
            self.in_process = True
            self.item = PaymentTypeService().get_by_id(int(id))
            self.in_process = False
            if self.item is None:
                yield rx.redirect(routes.CATALOG_PAYMENT_TYPES)
                yield rx.toast.error("Запис не було знайдено")
                return
            self._load_history(self.item.id)
        except Exception:
            self.in_process = False
            yield rx.toast.error("Під час виконання запиту сталася помилка. Спробуйте знову.")

    @rx.event
    def on_click_edit(self):
        if self.item is None:
            return
        return rx.redirect(routes.CATALOG_PAYMENT_TYPES_EDIT_ID + str(self.item.id))

    @rx.event
    def on_click_delete(self):
        if not self.has_permission(Action.PAYMENT_TYPE_DELETE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None:
            return
        if PaymentTypeService().delete_one(self.item.id, self.user.login):
            yield rx.toast.success("Тип оплати видалено!")
            yield ListPaymentTypeState.on_load()
            yield rx.redirect(routes.CATALOG_PAYMENT_TYPES)
        else:
            yield rx.toast.error("Помилка! Тип оплати не знайдено.")
