import reflex as rx

from typing import List, Optional, Tuple

import TrifleSklad.routes as routes
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum

from TrifleSklad.models import ProductCategory, ProductCatalog
from TrifleSklad.dao import ProductCatalogDAO, ProductCategoryDAO


# Сентинел «без батьківської категорії» для селекту (Radix забороняє порожнє value item).
NONE = "none"


class ViewCategoriesState(rx.State):
    item: Optional[ProductCategory] = None
    app_state: Optional[AppState] = None
    parent_title: str = ""
    children: List[ProductCategory] = []

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
        self.parent_title = ""
        if self.item.id_parent is not None:
            parent = ProductCategoryDAO.get_by_id(self.item.id_parent)
            self.parent_title = parent.title if parent is not None else ""
        self.children = [
            c for c in ProductCategoryDAO.get_all() if c.id_parent == self.item.id
        ]
        self.app_state = await self.get_state(AppState)
    # ===============


class AddCategoriesState(rx.State):
    item: Optional[ProductCategory] = None
    app_state: Optional[AppState] = None
    list_parent_categories: List[Tuple[str, str]] = []
    parent_id: str = NONE

    def _reset_item(self):
        self.item: ProductCategory = ProductCategory()
        self.parent_id = NONE

    # Action handlers
    # ===============
    @rx.event
    async def on_load(self):
        self._reset_item()
        self.list_parent_categories = ProductCategoryDAO.get_top_level_options()
        self.app_state = await self.get_state(AppState)

    @rx.event
    def on_change_title(self, new_title: str):
        self.item.title = new_title

    @rx.event
    def on_change_description(self, new_description: str):
        self.item.description = new_description

    @rx.event
    def on_change_parent(self, value: str):
        self.parent_id = value

    @rx.event
    def add_one(self):
        if not self.app_state.has_permission(ActionEnum.CATEGORIES_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")

        if self.item.title is None or self.item.title == "":
            return rx.toast.error("Не заповнені обов'язкові поля!")

        self.item.id_parent = int(self.parent_id) if self.parent_id != NONE else None

        flag, text, id = ProductCategoryDAO.add_one(self.item)
        if flag:
            # Освіжаємо список одразу тут — інакше при поверненні на список
            # (через кнопку «Повернутись») можна побачити застарілі дані,
            # якщо on_load цільової сторінки з якоїсь причини не спрацює.
            return [rx.toast.success(text), ListCategoriesState.on_load(), rx.redirect(f"{routes.CATALOG_CATEGORIES_VIEW_ID}{id}")]
        return rx.toast.error(text)
    # ===============


class EditCategoriesState(rx.State):
    item: Optional[ProductCategory] = None
    app_state: Optional[AppState] = None
    list_parent_categories: List[Tuple[str, str]] = []
    parent_id: str = NONE
    can_set_parent: bool = True

    def _load_item(self, id: int):
        self.item = ProductCategoryDAO.get_by_id_with_relationships(id)
        if self.item is not None:
            self.parent_id = str(self.item.id_parent) if self.item.id_parent is not None else NONE
            self.can_set_parent = not ProductCategoryDAO.has_children(self.item.id)
            self.list_parent_categories = ProductCategoryDAO.get_top_level_options(exclude_id=self.item.id)

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
    def on_change_parent(self, value: str):
        self.parent_id = value

    @rx.event
    def edit_one(self):
        if not self.app_state.has_permission(ActionEnum.CATEGORIES_EDIT):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")

        if self.item.title is None or self.item.title == "":
            return rx.toast.error("Не заповнені обов'язкові поля!")

        self.item.id_parent = (
            int(self.parent_id) if self.can_set_parent and self.parent_id != NONE else None
        )

        flag, text, id = ProductCategoryDAO.edit_one(self.item)
        if flag:
            return [rx.toast.success(text), ListCategoriesState.on_load(), rx.redirect(f"{routes.CATALOG_CATEGORIES_VIEW_ID}{id}")]
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
        self.items = ProductCategoryDAO.get_all_ordered_for_tree()
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
                yield rx.redirect(routes.CATALOG_CATEGORIES)
                return

            # /categories/add
            if page == self.Pages.ADD:
                if not self.app_state.has_permission(ActionEnum.CATEGORIES_CREATE):
                    yield rx.redirect(routes.WELCOME)
                    return
                yield AddCategoriesState.on_load()
            # /categories/edit/[id]
            elif page == self.Pages.EDIT:
                if not self.app_state.has_permission(ActionEnum.CATEGORIES_EDIT):
                    yield rx.redirect(routes.WELCOME)
                    return

                id = self.router.page.params.get('id', '')
                if id != '':
                    yield EditCategoriesState.on_load(id)
                else:
                    yield rx.redirect(routes.CATALOG_CATEGORIES)
                    return
            # /categories/view/[id]
            elif page == self.Pages.VIEW:
                if not self.app_state.has_permission(ActionEnum.CATEGORIES_VIEW):
                    yield rx.redirect(routes.WELCOME)
                    return

                id = self.router.page.params.get('id', '')
                if id != '':
                    yield ViewCategoriesState.on_load(id)
                else:
                    yield rx.redirect(routes.CATALOG_CATEGORIES)
                    return

            self.current_page = page
        else:
            # /categories
            if not self.app_state.has_permission(ActionEnum.CATEGORIES_LIST):
                yield rx.redirect(routes.WELCOME)
                return
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
                
            products_in_category: List[ProductCatalog] = ProductCatalogDAO.get_by_category(id)

            if len(products_in_category) > 0:
                return rx.toast.error("Неможливо видалити категорію, у яку входить ТМЦ з каталогу!")

            if ProductCategoryDAO.has_children(id):
                return rx.toast.error("Неможливо видалити категорію, у якої є підкатегорії!")

            flag, text = ProductCategoryDAO.delete_one(id)
            if flag:
                return [rx.toast.success(text), ListCategoriesState.on_load(), rx.redirect(routes.CATALOG_CATEGORIES)]
            else:
                return [rx.toast.error(text)]
        return rx.toast.error("Не обрано запис для видалення!")
