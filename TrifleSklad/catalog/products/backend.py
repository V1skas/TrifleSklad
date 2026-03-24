import reflex as rx

from typing import List, Tuple, Optional

from reflex import route

import TrifleSklad.routes as routes
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum

from TrifleSklad.models import ProductCatalog, ProductCategory
from TrifleSklad.dao import ProductCatalogDAO, ProductCategoryDAO, ProductDAO


class ViewProductsState(rx.State):
    item: Optional[ProductCatalog] = None
    app_state: Optional[AppState] = None
    
    def _load_item(self, id: int):
        self.item = ProductCatalogDAO.get_by_id_with_relationships(id)
        
    # Vars
    # ====
    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""
        
    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""
        
    @rx.var
    def category(self) -> str:
        return self.item.category.title if self.item is not None and self.item.category is not None else "None"
        
    @rx.var
    def unit(self) -> str:
        return str(self.item.unit) if self.item is not None and self.item.unit is not None else "None"
        
    @rx.var
    def divisible(self) -> bool:
        return self.item.divisible if self.item is not None and self.item.divisible is not None else False
        
    @rx.var
    def uniq(self) -> bool:
        return self.item.uniq if self.item is not None and self.item.uniq is not None else False
        
    @rx.var
    def capacity(self) -> str:
        return str(self.item.capacity) if self.item is not None and self.item.capacity is not None else "None"
        
    @rx.var
    def count(self) -> str:
        return str(self.item.count) if self.item is not None and self.item.count is not None else "None"
    # ====
    
    # Action handlers
    # ===============
    @rx.event
    async def on_load(self, id: int):
        self._load_item(id)
        if self.item is None:
            return [
                rx.redirect(routes.CATALOG_PRODUCTS),
                rx.toast.error("Запис не знайдено!")
            ]
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
    # ===============


class AddProductsState(rx.State):
    item: Optional[ProductCatalog] = None
    app_state: Optional[AppState] = None
    list_categories: List[Tuple[str, str]] = []

    def _reload_item(self):
        self.item = ProductCatalog()

    def _load_categories(self):
        self.list_categories = [(str(item.id), item.title) for item in ProductCategoryDAO.get_all()]

    # Vars
    # ====
    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""
        
    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""
        
    @rx.var
    def category(self) -> str:
        return self.item.category.title if self.item is not None and self.item.category is not None else "None"
    
    @rx.var
    def category_id(self) -> str:
        return str(self.item.id_category) if self.item is not None and self.item.id_category is not None else ""
        
    @rx.var
    def unit(self) -> str:
        return str(self.item.unit) if self.item is not None and self.item.unit is not None else "None"
        
    @rx.var
    def divisible(self) -> bool:
        return self.item.divisible if self.item is not None and self.item.divisible is not None else False
        
    @rx.var
    def uniq(self) -> bool:
        return self.item.uniq if self.item is not None and self.item.uniq is not None else False
        
    @rx.var
    def capacity(self) -> str:
        return str(self.item.capacity) if self.item is not None and self.item.capacity is not None else "None"
        
    @rx.var
    def count(self) -> str:
        return str(self.item.count) if self.item is not None and self.item.count is not None else "None"
    # ====
    
    # Action handlers
    # ===============
    @rx.event
    async def on_load(self):
        self._reload_item()
        self._load_categories()
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)

    @rx.event
    def on_change_title(self, value: str):
        self.item.title = value if value != "" else None

    @rx.event
    def on_change_description(self, value: str):
        self.item.description = value if value != "" else None

    @rx.event
    def on_change_category(self, value: str):
        self.item.id_category = int(value) if int(value) > 0 else None

    @rx.event
    def on_change_unit(self, value: str):
        self.item.unit = value if value != "" else None

    @rx.event
    def on_change_divisible(self, value: bool):
        self.item.divisible = value

    @rx.event
    def on_change_capacity(self, value: str):
        self.item.capacity = int(value) if int(value) > 0 else 0

    @rx.event
    def on_change_uniq(self, value: bool):
        self.item.uniq = value

    @rx.event
    def add_one(self):
        if not self.app_state.has_permission(ActionEnum.PRODUCTS_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        
        if self.item.title is None or self.item.id_category is None:
            return rx.toast.error("Усі обов'язкові поля мають бути заповненими!")
        
        flag, text, id = ProductCatalogDAO.add_one(self.item)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_PRODUCTS_VIEW_ID}{id}")]
        return rx.toast.error(text)
    # ===============


class EditProductsState(rx.State):
    item: Optional[ProductCatalog] = None
    app_state: Optional[AppState] = None
    list_categoties: List[Tuple[str, str]] = []

    def _load_item(self, id: int):
        self.item = ProductCatalogDAO.get_by_id_with_relationships(id)

    def _load_categories(self):
        self.list_categoties = [(str(item.id), item.title) for item in ProductCategoryDAO.get_all()]

    # Vars
    # ====
    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""
        
    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""
        
    @rx.var
    def category(self) -> str:
        return self.item.category.title if self.item is not None and self.item.category is not None else "None"
    
    @rx.var
    def category_id(self) -> str:
        return str(self.item.id_category) if self.item is not None and self.item.id_category is not None else ""
        
    @rx.var
    def unit(self) -> str:
        return str(self.item.unit) if self.item is not None and self.item.unit is not None else "None"
        
    @rx.var
    def divisible(self) -> bool:
        return self.item.divisible if self.item is not None and self.item.divisible is not None else False
        
    @rx.var
    def uniq(self) -> bool:
        return self.item.uniq if self.item is not None and self.item.uniq is not None else False
        
    @rx.var
    def capacity(self) -> str:
        return str(self.item.capacity) if self.item is not None and self.item.capacity is not None else "None"
        
    @rx.var
    def count(self) -> str:
        return str(self.item.count) if self.item is not None and self.item.count is not None else "None"
    # ====
    
    # Action handlers
    # ===============
    @rx.event
    async def on_load(self, id: int):
        self._load_item(id)
        if self.item is None:
            return [
                rx.redirect(routes.CATALOG_PRODUCTS),
                rx.toast.warning("Запис не знайдено!")
            ]
        self._load_categories()
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)

    @rx.event
    def on_change_title(self, value: str):
        self.item.title = value if value != "" else None

    @rx.event
    def on_change_description(self, value: str):
        self.item.description = value if value != "" else None

    @rx.event
    def on_change_category(self, value: str):
        self.item.id_category = int(value) if int(value) > 0 else None

    @rx.event
    def on_change_unit(self, value: str):
        self.item.unit = value if value != "" else None

    @rx.event
    def on_change_divisible(self, value: bool):
        self.item.divisible = value

    @rx.event
    def on_change_capacity(self, value: str):
        self.item.capacity = int(value) if int(value) > 0 else 0

    @rx.event
    def on_change_uniq(self, value: bool):
        self.item.uniq = value

    @rx.event
    def edit_one(self):
        if not self.app_state.has_permission(ActionEnum.PRODUCTS_EDIT):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        
        if self.item.title is None or self.item.id_category is None:
            return rx.toast.error("Усі обов'язкові поля мають бути заповненими!")
        
        flag, text, id = ProductCatalogDAO.edit_one(self.item)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_PRODUCTS_VIEW_ID}{id}")]
        return rx.toast.error(text)
    # ===============


class ListProductsState(rx.State):
    items: List[ProductCatalog] = []

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
        self.items = ProductCatalogDAO.get_all_with_relationships()
    # ===============

class ProductsState(rx.State):
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
                return rx.redirect(routes.CATALOG_PRODUCTS)

            # /products/add
            if page == self.Pages.ADD:
                if not self.app_state.has_permission(ActionEnum.PRODUCTS_CREATE):
                    return rx.redirect(routes.WELCOME)
                yield AddProductsState.on_load()
            # /products/edit/[id]
            elif page == self.Pages.EDIT:
                if not self.app_state.has_permission(ActionEnum.PRODUCTS_EDIT):
                    return rx.redirect(routes.WELCOME)
                id = self.router.page.params.get('id', '')
                if id != '':
                    yield EditProductsState.on_load(int(id))
                else:
                    return rx.redirect(routes.CATALOG_PRODUCTS)
            # /products/view/[id]
            elif page == self.Pages.VIEW:
                if not self.app_state.has_permission(ActionEnum.PRODUCTS_VIEW):
                    return rx.redirect(routes.WELCOME)
                id = self.router.page.params.get('id', '')
                if id != '':
                    yield ViewProductsState.on_load(int(id))
                else:
                    return rx.redirect(routes.CATALOG_PRODUCTS)

            self.current_page = page
        else:
            # /products
            if not self.app_state.has_permission(ActionEnum.PRODUCTS_LIST):
                return rx.redirect(routes.WELCOME)
            yield ListProductsState.on_load()
            self.current_page = self.Pages.LIST

    @rx.event
    async def on_load(self):
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
        return self._check_path()

    @rx.event
    def delete_one(self, id: int):
        if id > 0:
            flag, text = ProductCatalogDAO.delete_one(id)
            if flag:
                return [rx.toast.success(text), rx.redirect(routes.CATALOG_PRODUCTS)]
            else:
                return [rx.toast.error(text)]
        return rx.toast.error("Не обрано запис для видалення!")
