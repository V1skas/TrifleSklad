import reflex as rx

from typing import List, Tuple, Optional

import TrifleSklad.routes as routes
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum

from TrifleSklad.models import PaymentType
from TrifleSklad.dao import PaymentTypeDAO


class ViewPaymentTypeState(rx.State):
    item: Optional[PaymentType] = None
    app_state: Optional[AppState] = None

    # Vars
    # ====
    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""

    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""
    # ====

    # Action handlers
    # ===============
    @rx.event
    async def on_load(self, id: int):
        self.item = PaymentTypeDAO.get_by_id(id)
        if self.item is None:
            return [
                rx.redirect(routes.CATALOG_PAYMENT_TYPES),
                rx.toast.error("Запис не знайдено!")
            ]
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
    # ===============


class AddPaymentTypeState(rx.State):
    item: Optional[PaymentType] = None
    app_state: Optional[AppState] = None

    def _reset_item(self):
        self.item: PaymentType = PaymentType()

    # Dinamic var
    # ===========
    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""
    
    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""
    # ===========

    # Action handlers
    # ===============
    @rx.event
    async def on_load(self):
        self._reset_item()
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)

    @rx.event
    def on_change_title(self, title: str):
        self.item.title = title if title != "" else None

    @rx.event
    def on_change_description(self, description: str):
        self.item.description = description if description != "" else None

    @rx.event
    def add_one(self):
        if not self.app_state.has_permission(ActionEnum.PAYMENT_TYPE_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        
        if self.item.title is None:
            return rx.toast.error("Усі обов'язкові поля мають бути заповнені!")

        flag, text, id = PaymentTypeDAO.add_one(self.item)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_PAYMENT_TYPES_VIEW_ID}{id}")]
        return rx.toast.error(text)
    # ===============


class EditPaymentTypeState(rx.State):
    item: Optional[PaymentType] = None
    app_state: Optional[AppState] = None

    def _load_item(self, id: int):
        self.item = PaymentTypeDAO.get_by_id(id)

    # Vars
    # ====
    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""
    
    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""
    # ====

    # Action handlers
    # ===============
    @rx.event
    async def on_load(self, id: int):
        self._load_item(id)
        if self.item is None:
            return [
                rx.redirect(routes.CATALOG_PAYMENT_TYPES),
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
    def edit_one(self):
        if not self.app_state.has_permission(ActionEnum.PAYMENT_TYPE_EDIT):
            return rx.touas.error("У Вас немає дозволу на виконання цієї дії!")
        
        if self.item.title is None:
            return rx.toast.error("Усі обов'язкові поля мають бути заповнені!")
        
        flag, text, id = PaymentTypeDAO.edit_one(self.item)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_PAYMENT_TYPES_VIEW_ID}{id}")]
        return rx.toast.error(text)
    # ===============


class ListPaymentTypeState(rx.State):
    items: List[PaymentType] = []

    # Frontend vars
    # =============
    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0
    # =============

    # Action handlers
    # ===============
    @rx.event
    def on_load(self):
        self.items = PaymentTypeDAO.get_all()
    # ===============


class PaymentTypeState(rx.State):
    class Pages:
        ADD = "add"
        EDIT = "edit"
        VIEW = "view"
        LIST = "list"

    current_page: str = ""
    app_state: Optional[AppState] = None

    def _check_path(self):
        page = self.router.page.params.get('page', '')
        if page != '':
            id = -1

            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                return rx.redirect(routes.CATALOG_PAYMENT_TYPES)

            # /payment_types/add
            if page == self.Pages.ADD:
                if not self.app_state.has_permission(ActionEnum.PAYMENT_TYPE_CREATE):
                    return rx.redirect(routes.WELCOME)
                yield AddPaymentTypeState.on_load()
            # /payment_types/edit/[id]
            elif page == self.Pages.EDIT:
                if not self.app_state.has_permission(ActionEnum.PAYMENT_TYPE_EDIT):
                    return rx.redirect(routes.WELCOME)

                id = self.router.page.params.get('id', '')
                if id != '':
                    yield EditPaymentTypeState.on_load(id)
                else:
                    return rx.redirect(routes.CATALOG_PAYMENT_TYPES)
            # /payment_types/view/[id]
            elif page == self.Pages.VIEW:
                if not self.app_state.has_permission(ActionEnum.PAYMENT_TYPE_VIEW):
                    return rx.redirect(routes.WELCOME)

                id = self.router.page.params.get('id', '')
                if id != '':
                    yield ViewPaymentTypeState.on_load(id)
                else:
                    return rx.redirect(routes.CATALOG_PAYMENT_TYPES)

            self.current_page = page
        else:
            # /payment_types
            if not self.app_state.has_permission(ActionEnum.PAYMENT_TYPE_LIST):
                return rx.redirect(routes.WELCOME)
            yield ListPaymentTypeState.on_load()
            self.current_page = self.Pages.LIST

    @rx.event
    async def on_load(self):
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
        return self._check_path()

    @rx.event
    def delete_one(self, id: int):
        if not self.app_state.has_permission(ActionEnum.PAYMENT_TYPE_DELETE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")

        if id > -1:
            flag, text = PaymentTypeDAO.delete_one(id)
            if flag:
                return [rx.toast.success(text), rx.redirect(routes.CATALOG_PAYMENT_TYPES)]
            else:
                return [rx.toast.error(text)]
        return rx.toast.error("Не обрано запис для видалення!")