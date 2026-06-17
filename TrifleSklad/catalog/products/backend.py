import reflex as rx

from typing import List, Tuple, Optional

import TrifleSklad.routes as routes
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum

from TrifleSklad.models import ProductCatalog, ProductCategory
from TrifleSklad.dao import ProductCatalogDAO, ProductCategoryDAO, ProductDAO
from TrifleSklad.movement.list_mixin import ALL


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


class CategoryCreateMixin(rx.State, mixin=True):
    """Створення нової категорії прямо з форми товару.

    Підмішується в Add/Edit стани товару — обидва мають `item`, `app_state`,
    `list_categories` та метод `_load_categories`, на які спирається міксин.
    """

    is_create_category_open: bool = False
    new_category_title: str = ""
    new_category_description: str = ""

    def _reset_new_category(self):
        self.new_category_title = ""
        self.new_category_description = ""

    @rx.event
    def open_create_category(self):
        self._reset_new_category()
        self.is_create_category_open = True

    @rx.event
    def set_create_category_open(self, value: bool):
        self.is_create_category_open = value

    @rx.event
    def on_change_new_category_title(self, value: str):
        self.new_category_title = value

    @rx.event
    def on_change_new_category_description(self, value: str):
        self.new_category_description = value

    @rx.event
    def create_category(self):
        if not self.app_state.has_permission(ActionEnum.CATEGORIES_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")

        title = self.new_category_title.strip()
        if title == "":
            return rx.toast.error("Вкажіть назву категорії!")

        category = ProductCategory(
            title=title,
            description=self.new_category_description.strip() or None,
        )
        flag, text, new_id = ProductCategoryDAO.add_one(category)
        if not flag:
            return rx.toast.error(text)

        # Перезавантажуємо список і одразу обираємо нову категорію в товарі.
        self._load_categories()
        self.item.id_category = new_id
        self.is_create_category_open = False
        self._reset_new_category()
        return rx.toast.success("Категорію створено та обрано!")


class AddProductsState(CategoryCreateMixin, rx.State):
    item: Optional[ProductCatalog] = None
    app_state: Optional[AppState] = None
    list_categories: List[Tuple[str, str]] = []
    all_units_cache: list[str] = []

    def _reload_item(self):
        self.item = ProductCatalog()

    def _load_categories(self):
        self.list_categories = [(str(item.id), item.title) for item in ProductCategoryDAO.get_all()]
    
    def _load_all_units_cache(self):
        self.all_units_cache = ProductCatalogDAO.get_list_units()
        
    # Vars
    # ====
    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""
        
    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""
        
    @rx.var
    def category_id(self) -> str:
        return str(self.item.id_category) if self.item is not None and self.item.id_category is not None else ""

    @rx.var
    def unit(self) -> str:
        return str(self.item.unit) if self.item is not None and self.item.unit is not None else ""

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
        self._load_all_units_cache()
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
        self.item.id_category = int(value) if value.isdigit() and int(value) > 0 else None

    @rx.event
    def on_change_unit(self, value: str):
        self.item.unit = value if value != "" else None
        #self.filter_suggestions(value)

    @rx.event
    def on_change_divisible(self, value: bool):
        # Товар із серійним номером (uniq) не може бути подільним.
        if self.item.uniq:
            self.item.divisible = False
            return
        self.item.divisible = value

    @rx.event
    def on_change_capacity(self, value: str):
        # Товар із серійним номером завжди має місткість 1.
        if self.item.uniq:
            self.item.capacity = 1
            return
        self.item.capacity = int(value) if value.isdigit() and int(value) > 0 else 0

    @rx.event
    def on_change_uniq(self, value: bool):
        self.item.uniq = value
        if value:
            # Серійний номер ⇒ неподільний, місткість = 1.
            self.item.divisible = False
            self.item.capacity = 1

    @rx.event
    def add_one(self):
        if not self.app_state.has_permission(ActionEnum.PRODUCTS_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")

        if self.item.title is None or self.item.id_category is None:
            return rx.toast.error("Усі обов'язкові поля мають бути заповненими!")

        if self.item.uniq and self.item.divisible:
            return rx.toast.error("Товар із серійним номером не може бути подільним!")
        if self.item.uniq:
            self.item.capacity = 1

        flag, text, id = ProductCatalogDAO.add_one(self.item)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_PRODUCTS_VIEW_ID}{id}")]
        return rx.toast.error(text)
    # ===============


class EditProductsState(CategoryCreateMixin, rx.State):
    item: Optional[ProductCatalog] = None
    app_state: Optional[AppState] = None
    list_categories: List[Tuple[str, str]] = []
    all_units_cache: list[str] = []
    
    def _load_item(self, id: int):
        self.item = ProductCatalogDAO.get_by_id_with_relationships(id)

    def _load_categories(self):
        self.list_categories = [(str(item.id), item.title) for item in ProductCategoryDAO.get_all()]
        
    def _load_all_units_cache(self):
        self.all_units_cache = ProductCatalogDAO.get_list_units()

    # Vars
    # ====
    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""
        
    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""
        
    @rx.var
    def category_id(self) -> str:
        return str(self.item.id_category) if self.item is not None and self.item.id_category is not None else ""

    @rx.var
    def unit(self) -> str:
        return str(self.item.unit) if self.item is not None and self.item.unit is not None else ""

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
        self._load_all_units_cache()
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
        self.item.id_category = int(value) if value.isdigit() and int(value) > 0 else None

    @rx.event
    def on_change_unit(self, value: str):
        self.item.unit = value if value != "" else None

    @rx.event
    def on_change_divisible(self, value: bool):
        # Товар із серійним номером (uniq) не може бути подільним.
        if self.item.uniq:
            self.item.divisible = False
            return
        self.item.divisible = value

    @rx.event
    def on_change_capacity(self, value: str):
        # Товар із серійним номером завжди має місткість 1.
        if self.item.uniq:
            self.item.capacity = 1
            return
        self.item.capacity = int(value) if value.isdigit() and int(value) > 0 else 0

    @rx.event
    def on_change_uniq(self, value: bool):
        self.item.uniq = value
        if value:
            # Серійний номер ⇒ неподільний, місткість = 1.
            self.item.divisible = False
            self.item.capacity = 1

    @rx.event
    def edit_one(self):
        if not self.app_state.has_permission(ActionEnum.PRODUCTS_EDIT):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")

        if self.item.title is None or self.item.id_category is None:
            return rx.toast.error("Усі обов'язкові поля мають бути заповненими!")

        if self.item.uniq and self.item.divisible:
            return rx.toast.error("Товар із серійним номером не може бути подільним!")
        if self.item.uniq:
            self.item.capacity = 1

        flag, text, id = ProductCatalogDAO.edit_one(self.item)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_PRODUCTS_VIEW_ID}{id}")]
        return rx.toast.error(text)
    # ===============


class ListProductsState(rx.State):
    items: List[ProductCatalog] = []
    
    _current_page: int = 1
    _all_pages: int = 1
    _limit_items: int = 20
    search_str: Optional[str] = None
    filter_category_id: str = ALL
    list_categories: List[Tuple[str, str]] = []

    def _load_items(self):
        self._all_pages, self.items = ProductCatalogDAO.get_all_with_relationships_by_page(
            page=self._current_page,
            count_items=ProductCatalogDAO.get_count_with_search(self.search_str, self.filter_category_id),
            limit=self._limit_items,
            search_str=self.search_str,
            category_id=self.filter_category_id,
        )

    # Vars
    # ====
    @rx.var
    def get_current_page(self) -> str:
        return str(self._current_page)
    
    @rx.var
    def get_all_pages(self) -> str:
        return str(self._all_pages)
    
    @rx.var
    def get_items(self) -> List[ProductCatalog]:
        return self.items
    
    @rx.var
    def get_search_str(self) -> str:
        return self.search_str if self.search_str is not None else ""
    # ====

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
        self._current_page = 1
        self.search_str = None
        self.filter_category_id = ALL
        self.list_categories = [
            (c.title, str(c.id)) for c in ProductCategoryDAO.get_all()
        ]
        self._load_items()

    @rx.event
    def on_change_filter_category(self, value: str):
        self.filter_category_id = value
        self._current_page = 1
        self._load_items()

    @rx.event
    def current_page_increment(self):
        if self._current_page+1 <= self._all_pages:
            self._current_page += 1
            self._load_items()

    @rx.event
    def current_page_decrement(self):
        if self._current_page > 1:
            self._current_page -= 1
            self._load_items()

    @rx.event
    def on_change_current_page(self, value: str):
        if value != "" and int(value) > 0 and int(value) <= self._all_pages:
            self._current_page = int(value)
            self._load_items()
    
    @rx.event
    def on_change_search_str(self, value: str):
        if value != "":
            self.search_str = value
        else:
            self.search_str = None

    @rx.event
    def on_click_search(self):
        self._current_page = 1
        self._load_items()
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
                yield rx.redirect(routes.CATALOG_PRODUCTS)
                return

            # /products/add
            if page == self.Pages.ADD:
                if not self.app_state.has_permission(ActionEnum.PRODUCTS_CREATE):
                    yield rx.redirect(routes.WELCOME)
                    return
                yield AddProductsState.on_load()
            # /products/edit/[id]
            elif page == self.Pages.EDIT:
                if not self.app_state.has_permission(ActionEnum.PRODUCTS_EDIT):
                    yield rx.redirect(routes.WELCOME)
                    return
                id = self.router.page.params.get('id', '')
                if id != '':
                    yield EditProductsState.on_load(int(id))
                else:
                    yield rx.redirect(routes.CATALOG_PRODUCTS)
                    return
            # /products/view/[id]
            elif page == self.Pages.VIEW:
                if not self.app_state.has_permission(ActionEnum.PRODUCTS_VIEW):
                    yield rx.redirect(routes.WELCOME)
                    return
                id = self.router.page.params.get('id', '')
                if id != '':
                    yield ViewProductsState.on_load(int(id))
                else:
                    yield rx.redirect(routes.CATALOG_PRODUCTS)
                    return

            self.current_page = page
        else:
            # /products
            if not self.app_state.has_permission(ActionEnum.PRODUCTS_LIST):
                yield rx.redirect(routes.WELCOME)
                return
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
            if not self.app_state.has_permission(ActionEnum.PRODUCTS_DELETE):
                return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            flag, text = ProductCatalogDAO.delete_one(id)
            if flag:
                return [rx.toast.success(text), rx.redirect(routes.CATALOG_PRODUCTS)]
            else:
                return [rx.toast.error(text)]
        return rx.toast.error("Не обрано запис для видалення!")
