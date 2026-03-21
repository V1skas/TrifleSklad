import reflex as rx

from typing import List, Optional

import TrifleSklad.routes as routes
from TrifleSklad.models import Owner
from TrifleSklad.dao import OwnerDAO

from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum

class ViewOwnerstate(rx.State):
    item: Optional[Owner] = None
    app_state: Optional[AppState] = None

    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""
    
    # Action handlers
    # ===============
    @rx.event
    async def on_load(self, id: int):
        self.item = OwnerDAO.get_by_id(id)
        if self.item is None:
            return [
                rx.redirect(routes.CATALOG_OWNERS),
                rx.toast.error("Запис не знайдено!")
            ]
        self.app_state = await self.get_state(AppState)
    # ===============

    
class AddOwnerState(rx.State):
    item: Optional[Owner] = None
    app_state: Optional[AppState] = None

    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""
    
    def _reset_item(self):
        self.item: Owner = Owner()
        
    # Action handlers
    # ==============
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
        self.item.description = description
        
    @rx.event
    def add_one(self):
        if not self.app_state.has_permission(ActionEnum.OWNERS_CREATE):
            return rx.toast.error("У Вас нема дозволу на виконання цієї дії!")
        
        if self.item.title is None:
            return rx.toast.error("Усі обов'язкові поля повинні бути заповнені!")

        flag, text, id = OwnerDAO.add_one(self.item)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_OWNERS_VIEW_ID}{id}")]
        return rx.toast.error(text)
    # ==============


class EditOwnerState(rx.State):
    item: Optional[Owner] = None
    app_state: Optional[AppState] = None

    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""

    def _load_item(self, id: int):
        self.item = OwnerDAO.get_by_id(id)

    # Action handlers
    # ===============
    @rx.event
    async def on_load(self, id: int):
        self._load_item(id)
        if self.item is None:
            return [
                rx.redirect(routes.CATALOG_OWNERS),
                rx.toast.error("Запис не знайдено!")
            ]
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)

    @rx.event
    def on_change_title(self, title: str):
        self.item.title = title if title != "" else None

    @rx.event
    def on_change_description(self, description: str):
        self.item.description = description

    @rx.event
    def edit_one(self):
        if not self.app_state.has_permission(ActionEnum.OWNERS_EDIT):
            return rx.toast.error("У Вас нема дозволу на виконання цієї дії!")
        
        if self.item.title is None:
            return rx.toast.error("Усі обов'язкові поля повинні бути заповнені!")

        flag, text, id = OwnerDAO.edit_one(self.item)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_OWNERS_VIEW_ID}{id}")]
        return rx.toast.error(text)
    # ===============


class ListOwnerState(rx.State):
    items: List[Owner] = []

    # Frontend vars
    # =============
    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0
    # =============

    # Actions handlers
    # ================
    @rx.event
    async def on_load(self):
        self.items = OwnerDAO.get_all()
    # ================
    
    
class OwnerState(rx.State):
    class Pages:
        ADD = "add"
        EDIT = "edit"
        VIEW = "view"
        LIST = "list"

    current_page: str = Pages.LIST
    app_state: Optional[AppState] = None

    def _check_path(self):
        page = self.router.page.params.get('page', '')
        if page != '':
            id = -1
            
            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                return rx.redirect(routes.CATALOG_OWNERS)

            # /owners/add
            if page == self.Pages.ADD:
                if not self.app_state.has_permission(ActionEnum.OWNERS_CREATE):
                    return rx.redirect(routes.WELCOME)
                yield AddOwnerState.on_load()
            # /owners/edit/[id]
            elif page == self.Pages.EDIT:
                if not self.app_state.has_permission(ActionEnum.OWNERS_EDIT):
                    return rx.redirect(routes.WELCOME)
                id = self.router.page.params.get('id', '')
                if id != '':
                    yield EditOwnerState.on_load(id)
                else:
                    return rx.redirect(routes.CATALOG_OWNERS)
            # /owners/view/[id]
            elif page == self.Pages.VIEW:
                id = self.router.page.params.get('id', '')
                if not self.app_state.has_permission(ActionEnum.OWNERS_VIEW):
                    return rx.redirect(routes.WELCOME)
                if id != '':
                    yield ViewOwnerstate.on_load(id)
                else:
                    return rx.redirect(routes.CATALOG_OWNERS)

            self.current_page = page
        else:
            # /owners
            if not self.app_state.has_permission(ActionEnum.OWNERS_LIST):
                return rx.redirect(routes.WELCOME)
            yield ListOwnerState.on_load()
            self.current_page = self.Pages.LIST

    @rx.event
    async def on_load(self):
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
        return self._check_path()

    @rx.event
    def delete_one(self, id: int):
        if id > -1:
            if not self.app_state.has_permission(ActionEnum.OWNERS_DELETE):
                return rx.toast.error("У Вас немає дозвулу на виконання цієї дії!")

            flag, text = OwnerDAO.delete_one(id)
            if flag:
                return [rx.toast.success(text), rx.redirect(routes.CATALOG_OWNERS)]
            else:
                return [rx.toast.error(text)]
        return rx.toast.error("Не обрано запис для видалення!")
