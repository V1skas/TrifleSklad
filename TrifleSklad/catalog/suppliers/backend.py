import reflex as rx

from typing import List, Tuple, Optional

import TrifleSklad.routes as routes
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum

from TrifleSklad.models import Supplier
from TrifleSklad.dao import SupplierDAO


class ViewSupplierState(rx.State):
    item: Optional[Supplier] = None
    app_state: Optional[AppState] = None

    def _load_item(self, id: int):
        self.item = SupplierDAO.get_by_id(id)

    # Vars
    # ====
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
    # ====

    # Action handlers
    # ===============
    @rx.event
    async def on_load(self, id: int):
        self._load_item(id)
        if self.item is None:
            return [
                rx.redirect(routes.CATALOG_SUPPLIERS),
                rx.toast.error("Запис не знайдено!")
            ]
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
    # ===============


class AddSupplierState(rx.State):
    item: Optional[Supplier] = None
    app_state: Optional[AppState] = None

    def _reset_item(self):
        self.item: Supplier = Supplier()

    # Vars
    # ====
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
    # ====

    # Action handlers
    # ===============
    @rx.event
    async def on_load(self):
        self._reset_item()
        if self.item is None:
            return [
                rx.redirect(routes.CATALOG_SUPPLIERS),
                rx.toast.error("Запис не знайдено!")
            ]
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)

    @rx.event
    def on_change_title(self, title: str):
        self.item.title = title if title != "" else None

    @rx.event
    def on_change_description(self, description: str):
        self.item.description = description if description != "" else None

    @rx.event
    def on_change_address(self, address: str):
        self.item.address = address if address != "" else None

    @rx.event
    def on_change_email(self, email: str):
        self.item.email = email if email != "" else None

    @rx.event
    def on_change_contact_person(self, contact_person: str):
        self.item.contact_person = contact_person if contact_person != "" else None

    @rx.event
    def on_change_contact_phone(self, contact_phone: str):
        self.item.contact_phone = contact_phone if contact_phone != "" else None

    @rx.event
    def on_change_edrpou(self, edrpou: str):
        self.item.edrpou = edrpou if edrpou != "" else None

    @rx.event
    def add_one(self):
        if not self.app_state.has_permission(ActionEnum.SUPPLIERS_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        
        if self.item.title is None:
            return rx.toast.error("Обов'язкові поля повинні бути заповненими!")

        flag, text, id = SupplierDAO.add_one(self.item)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_SUPPLIERS_VIEW_ID}{id}")]
        return rx.toast.error(text)
    # ===============


class EditSupplierState(rx.State):
    item: Optional[Supplier] = None
    app_state: Optional[AppState] = None

    def _load_item(self, id: int):
        self.item = SupplierDAO.get_by_id(id)

    # Vars
    # ====
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
    # ====

    # Action handlers
    # ===============
    @rx.event
    async def on_load(self, id: int):
        self._load_item(id)
        if self.item is None:
            return [
                rx.redirect(routes.CATALOG_SUPPLIERS),
                rx.toast.error("Запис не знайдено!")
            ]
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)

    @rx.event
    def on_change_title(self, title: str):
        self.item.title = title if title != "" else None

    @rx.event
    def on_change_description(self, description: str):
        self.item.description = description if description != "" else None

    @rx.event
    def on_change_address(self, address: str):
        self.item.address = address if address != "" else None

    @rx.event
    def on_change_email(self, email: str):
        self.item.email = email if email != "" else None

    @rx.event
    def on_change_contact_person(self, contact_person: str):
        self.item.contact_person = contact_person if contact_person != "" else None

    @rx.event
    def on_change_contact_phone(self, contact_phone: str):
        self.item.contact_phone = contact_phone if contact_phone != "" else None

    @rx.event
    def on_change_edrpou(self, edrpou: str):
        self.item.edrpou = edrpou if edrpou != "" else None

    @rx.event
    def edit_one(self):
        if not self.app_state.has_permission(ActionEnum.SUPPLIERS_EDIT):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        
        if self.item.title is None:
            return rx.toast.error("Обов'язкові поля повинні бути заповненими!")

        flag, text, id = SupplierDAO.edit_one(self.item)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_SUPPLIERS_VIEW_ID}{id}")]
        return rx.toast.error(text)
    # ===============


class ListSupplierState(rx.State):
    items: List[Supplier] = []

    # Фільтр (клієнтський — список завантажується цілком).
    filter_title: str = ""

    # Frontend vars
    # =============
    @rx.var
    def filtered_items(self) -> List[Supplier]:
        term = self.filter_title.strip().lower()
        if term == "":
            return self.items
        return [s for s in self.items if term in (s.title or "").lower()]

    @rx.var
    def has_items(self) -> bool:
        return len(self.filtered_items) > 0
    # =============

    # Action handlers
    # ===============
    @rx.event
    def on_load(self):
        self.filter_title = ""
        self.items = SupplierDAO.get_all()

    @rx.event
    def on_change_filter_title(self, value: str):
        self.filter_title = value
    # ===============


class SupplierState(rx.State):
    class Pages:
        ADD = 'add'
        EDIT = 'edit'
        VIEW = 'view'
        LIST = 'list'

    current_page: str = Pages.LIST
    app_state: Optional[AppState] = None

    def _check_path(self):
        page = self.router.page.params.get('page', '')
        if page != '':
            id = -1
            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                yield rx.redirect(routes.CATALOG_SUPPLIERS)
                return

            # /suppliers/add
            if page == self.Pages.ADD:
                if not self.app_state.has_permission(ActionEnum.SUPPLIERS_CREATE):
                    yield rx.redirect(routes.WELCOME)
                    return
                yield AddSupplierState.on_load()
            # /suppliers/edit/[id]
            elif page == self.Pages.EDIT:
                if not self.app_state.has_permission(ActionEnum.SUPPLIERS_EDIT):
                    yield rx.redirect(routes.WELCOME)
                    return
                id = self.router.page.params.get('id', '')
                if id != '':
                    yield EditSupplierState.on_load(id)
                else:
                    yield rx.redirect(routes.CATALOG_SUPPLIERS)
                    return
            # /suppliers/view/[id]
            elif page == self.Pages.VIEW:
                if not self.app_state.has_permission(ActionEnum.SUPPLIERS_VIEW):
                    yield rx.redirect(routes.WELCOME)
                    return
                id = self.router.page.params.get('id', '')
                if id != '':
                    yield ViewSupplierState.on_load(id)
                else:
                    yield rx.redirect(routes.CATALOG_SUPPLIERS)
                    return

            self.current_page = page
        else:
            # /suppliers
            if not self.app_state.has_permission(ActionEnum.SUPPLIERS_LIST):
                yield rx.redirect(routes.WELCOME)
                return
            yield ListSupplierState.on_load()
            self.current_page = self.Pages.LIST

    @rx.event
    async def on_load(self):
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
        return self._check_path()

    @rx.event
    def delete_one(self, id):
        if id != -1:
            if not self.app_state.has_permission(ActionEnum.SUPPLIERS_DELETE):
                return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            flag, text = SupplierDAO.delete_one(id)
            if flag:
                return [rx.toast.success(text), rx.redirect(routes.CATALOG_SUPPLIERS)]
            else:
                return [rx.toast.error(text)]
        return rx.toast.error("Не обрано запис для видалення!")
