from tkinter import N

import reflex as rx

from typing import List, Tuple, Optional

import TrifleSklad.routes as routes
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum

from TrifleSklad.models import ProductCategory
from TrifleSklad.dao import ProductCatalogDAO, ProductCategoryDAO


class ViewCategoriesState(rx.State):
    item: Optional[ProductCategory] = None
    app_state: Optional[AppState] = None

    # Action handlers
    # ===============
    @rx.event
    async def on_load(self, id: int):
        self.item = ProductCategoryDAO.get_by_id_with_relationships(id)
        if self.item is None:
            return [
                rx.redirect(routes.CATALOG_CATEGORIES),
                rx.toast.error("Запис не знайдено!")
            ]
        self.app_state = await self.get_state(AppState)
    # ===============


class AddCategoriesState(rx.State):
    item: Optional[ProductCategory] = None
    app_state: Optional[AppState] = None

    def _reset_item(self):
        self.item: ProductCategory = ProductCategory()

    # Action handlers
    # ===============
    @rx.event
    async def on_load(self):
        self._reset_item()
        self.app_state = await self.get_state(AppState)

    @rx.event
    def on_change_title(self, new_title: str):
        self.item.title = new_title

    @rx.event
    def on_change_description(self, new_description: str):
        self.item.description = new_description

    @rx.event
    def add_one(self):
        if not self.app_state.has_permission(ActionEnum.CATEGORIES_CREATE):
            return rx.toast.error("У Вас немає дозвулу на виконання цієї дії!")

        if self.item.title is None or self.item.title == "":
            return rx.toast.error("Не заповнені обов'язкові поля!")

        flag, text, id = ProductCategoryDAO.add_one(self.item)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_CATEGORIES_VIEW_ID}{id}")]
        return rx.toast.error(text)
    # ===============


class EditCategoriesState(rx.State):
    item: Optional[ProductCategory] = None
    app_state: Optional[AppState] = None

    def _load_item(self, id: int):
        self.item = ProductCategoryDAO.get_by_id_with_relationships(id)

    # Action handlers
    # ===============
    @rx.event
    async def on_load(self, id: int):
        self._load_item(id)
        if self.item is None:
            return [
                rx.redirect(routes.CATALOG_CATEGORIES),
                rx.toast.error("Запис не знайдено!")
            ]
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)

    @rx.event
    def on_change_title(self, new_title: str):
        self.item.title = new_title

    @rx.event
    def on_change_description(self, new_description: str):
        self.item.description = new_description

    @rx.event
    def edit_one(self):
        if not self.app_state.has_permission(ActionEnum.CATEGORIES_EDIT):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")

        if self.item.title is None or self.item.title == "":
            return rx.toast.error("Не заповнені обов'язкові поля!")

        flag, text, id = ProductCategoryDAO.edit_one(self.item)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_CATEGORIES_VIEW_ID}{id}")]
        return rx.toast.error(text)
    # ===============


class ListCategoriesState(rx.State):
    items: List[ProductCategory] = []

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
        self.items = ProductCategoryDAO.get_all()
    # ===============


class CategoriesState(rx.State):
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
                return rx.redirect(routes.CATALOG_CATEGORIES)

            # /categories/add
            if page == self.Pages.ADD:
                if not self.app_state.has_permission(ActionEnum.CATEGORIES_CREATE):
                    return rx.redirect(routes.WELCOME)
                yield AddCategoriesState.on_load()
            # /categories/edit/[id]
            elif page == self.Pages.EDIT:
                if not self.app_state.has_permission(ActionEnum.CATEGORIES_EDIT):
                    return rx.redirect(routes.WELCOME)
                
                id = self.router.page.params.get('id', '')
                if id != '':
                    yield EditCategoriesState.on_load(id)
                else:
                    return rx.redirect(routes.CATALOG_CATEGORIES)
            # /categories/view/[id]
            elif page == self.Pages.VIEW:
                if not self.app_state.has_permission(ActionEnum.CATEGORIES_VIEW):
                    return rx.redirect(routes.WELCOME)

                id = self.router.page.params.get('id', '')
                if id != '':
                    yield ViewCategoriesState.on_load(id)
                else:
                    return rx.redirect(routes.CATALOG_CATEGORIES)

            self.current_page = page
        else:
            # /categories
            if not self.app_state.has_permission(ActionEnum.CATEGORIES_LIST):
                return rx.redirect(routes.WELCOME)
            yield ListCategoriesState.on_load()
            self.current_page = self.Pages.LIST

    @rx.event
    async def on_load(self):
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
        return self._check_path()

    @rx.event
    def delete_one(self, id: int):
        if id > -1:
            if not self.app_state.has_permission(ActionEnum.CATEGORIES_DELETE):
                return rx.toast.error("Ви не маєте дозволу на цю дію!")

            flag, text = ProductCategoryDAO.delete_one(id)
            if flag:
                return [rx.toast.success(text), rx.redirect(routes.CATALOG_CATEGORIES)]
            else:
                return [rx.toast.error(text)]
        return rx.toast.error("Не обрано запис для видалення!")
