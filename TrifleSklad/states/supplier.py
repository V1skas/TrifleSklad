from typing import List, Optional, Sequence

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.models import Supplier
from TrifleSklad.services.errors import ServiceError
from TrifleSklad.services.supplier import SupplierService
from TrifleSklad.states.app import AppState
from TrifleSklad.states.audit_mixin import AuditHistoryMixin
from TrifleSklad.states.list_filter_mixin import SearchFilterMixin


class ListSupplierState(SearchFilterMixin, AppState):
    items: Optional[Sequence[Supplier]] = None
    in_progress: bool = True
    filter_title: str = ""

    @rx.var
    def filtered_items(self) -> List[Supplier]:
        if self.items is None:
            return []
        term = self.filter_title.strip().lower()
        if term == "":
            return list(self.items)
        return [s for s in self.items if term in (s.title or "").lower()]

    @rx.var
    def has_items(self) -> bool:
        return len(self.filtered_items) > 0

    @rx.var
    def has_active_filters(self) -> bool:
        return self.filter_title.strip() != ""

    @rx.event
    def on_load(self):
        if not self.has_permission(Action.SUPPLIERS_LIST):
            yield rx.redirect(routes.WELCOME)
            yield rx.toast.error("У Вас немає дозволу на перегляд цієї сторінки!")
            return
        try:
            self.in_progress = True
            self.filter_title = ""
            self.is_filter_open = False
            self.items = SupplierService().get_list_items()
            self.in_progress = False
        except Exception:
            yield rx.toast.error("Під час виконання запиту сталася помилка. Спробуйте знову.")

    @rx.event
    def set_filter_title(self, value: str):
        self.filter_title = value

    @rx.event
    def on_click_add(self):
        return rx.redirect(routes.CATALOG_SUPPLIERS_ADD)


class AddSupplierState(AppState):
    item: Supplier = Supplier()
    in_process: bool = False

    @rx.event
    def on_load(self):
        if not self.has_permission(Action.SUPPLIERS_CREATE):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        self.item = Supplier()

    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""

    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""

    @rx.var
    def address(self) -> str:
        return self.item.address if self.item is not None and self.item.address is not None else ""

    @rx.var
    def email(self) -> str:
        return self.item.email if self.item is not None and self.item.email is not None else ""

    @rx.var
    def contact_person(self) -> str:
        return self.item.contact_person if self.item is not None and self.item.contact_person is not None else ""

    @rx.var
    def contact_phone(self) -> str:
        return self.item.contact_phone if self.item is not None and self.item.contact_phone is not None else ""

    @rx.var
    def edrpou(self) -> str:
        return self.item.edrpou if self.item is not None and self.item.edrpou is not None else ""

    @rx.event
    def set_title(self, value: str):
        self.item.title = value

    @rx.event
    def set_description(self, value: str):
        self.item.description = value if value != "" else None

    @rx.event
    def set_address(self, value: str):
        self.item.address = value if value != "" else None

    @rx.event
    def set_email(self, value: str):
        self.item.email = value if value != "" else None

    @rx.event
    def set_contact_person(self, value: str):
        self.item.contact_person = value if value != "" else None

    @rx.event
    def set_contact_phone(self, value: str):
        self.item.contact_phone = value if value != "" else None

    @rx.event
    def set_edrpou(self, value: str):
        self.item.edrpou = value if value != "" else None

    @rx.event
    def on_save(self):
        if not self.has_permission(Action.SUPPLIERS_CREATE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if not self.item.title:
            yield rx.toast.warning("Поле назви повинно бути заповненим!")
            return
        try:
            self.item = SupplierService().add_one(self.item, self.user.login)
            yield rx.toast.success("Постачальника додано!")
            yield rx.redirect(routes.CATALOG_SUPPLIERS_VIEW_ID + str(self.item.id))
        except ServiceError as e:
            yield rx.toast.warning(str(e))
        except Exception:
            yield rx.toast.error("Під час виконання запиту трапилась помилка. Спробуйте ще раз.")


class EditSupplierState(AppState):
    item: Supplier = Supplier()
    in_process: bool = False

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(Action.SUPPLIERS_EDIT):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        try:
            self.in_process = True
            item = SupplierService().get_by_id(int(id))
            if item is None:
                self.in_process = False
                yield rx.redirect(routes.CATALOG_SUPPLIERS)
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
    def address(self) -> str:
        return self.item.address if self.item is not None and self.item.address is not None else ""

    @rx.var
    def email(self) -> str:
        return self.item.email if self.item is not None and self.item.email is not None else ""

    @rx.var
    def contact_person(self) -> str:
        return self.item.contact_person if self.item is not None and self.item.contact_person is not None else ""

    @rx.var
    def contact_phone(self) -> str:
        return self.item.contact_phone if self.item is not None and self.item.contact_phone is not None else ""

    @rx.var
    def edrpou(self) -> str:
        return self.item.edrpou if self.item is not None and self.item.edrpou is not None else ""

    @rx.event
    def set_title(self, value: str):
        self.item.title = value

    @rx.event
    def set_description(self, value: str):
        self.item.description = value if value != "" else None

    @rx.event
    def set_address(self, value: str):
        self.item.address = value if value != "" else None

    @rx.event
    def set_email(self, value: str):
        self.item.email = value if value != "" else None

    @rx.event
    def set_contact_person(self, value: str):
        self.item.contact_person = value if value != "" else None

    @rx.event
    def set_contact_phone(self, value: str):
        self.item.contact_phone = value if value != "" else None

    @rx.event
    def set_edrpou(self, value: str):
        self.item.edrpou = value if value != "" else None

    @rx.event
    def on_save(self):
        if not self.has_permission(Action.SUPPLIERS_EDIT):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if not self.item.title:
            yield rx.toast.warning("Поле назви повинно бути заповненим!")
            return
        try:
            self.item = SupplierService().edit_one(self.item, self.user.login)
            yield rx.toast.success("Інформація про постачальника змінена!")
            yield rx.redirect(routes.CATALOG_SUPPLIERS_VIEW_ID + str(self.item.id))
        except ServiceError as e:
            yield rx.toast.warning(str(e))
        except Exception:
            yield rx.toast.error("Під час виконання запиту трапилась помилка. Спробуйте ще раз.")


class ViewSupplierState(AuditHistoryMixin, AppState):
    HISTORY_TABLE = "suppliers"
    HISTORY_ACTION = Action.SUPPLIERS_HISTORY
    HISTORY_DETAIL_ACTION = Action.SUPPLIERS_HISTORY_DETAIL

    item: Optional[Supplier] = None
    in_process: bool = True

    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""

    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""

    @rx.var
    def address(self) -> str:
        return self.item.address if self.item is not None and self.item.address is not None else ""

    @rx.var
    def email(self) -> str:
        return self.item.email if self.item is not None and self.item.email is not None else ""

    @rx.var
    def contact_person(self) -> str:
        return self.item.contact_person if self.item is not None and self.item.contact_person is not None else ""

    @rx.var
    def contact_phone(self) -> str:
        return self.item.contact_phone if self.item is not None and self.item.contact_phone is not None else ""

    @rx.var
    def edrpou(self) -> str:
        return self.item.edrpou if self.item is not None and self.item.edrpou is not None else ""

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(Action.SUPPLIERS_VIEW):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        try:
            self.in_process = True
            self.item = SupplierService().get_by_id(int(id))
            self.in_process = False
            if self.item is None:
                yield rx.redirect(routes.CATALOG_SUPPLIERS)
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
        return rx.redirect(routes.CATALOG_SUPPLIERS_EDIT_ID + str(self.item.id))

    @rx.event
    def on_click_delete(self):
        if not self.has_permission(Action.SUPPLIERS_DELETE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None:
            return
        if SupplierService().delete_one(self.item.id, self.user.login):
            yield rx.toast.success("Постачальника видалено!")
            yield ListSupplierState.on_load()
            yield rx.redirect(routes.CATALOG_SUPPLIERS)
        else:
            yield rx.toast.error("Помилка! Постачальника не знайдено.")
