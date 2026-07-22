from typing import List, Optional, Sequence, Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.models import ProductCatalog, ProductCategory
from TrifleSklad.services.errors import ServiceError
from TrifleSklad.services.product_catalog import ProductCatalogService
from TrifleSklad.services.product_category import ProductCategoryService
from TrifleSklad.states.app import AppState
from TrifleSklad.states.audit_mixin import AuditHistoryMixin

ALL = "all"


class CategoryCreateMixin(rx.State, mixin=True):
    """Створення нової категорії прямо з форми товару.

    Підмішується в Add/Edit стани товару — обидва мають `item`,
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
    def set_new_category_title(self, value: str):
        self.new_category_title = value

    @rx.event
    def set_new_category_description(self, value: str):
        self.new_category_description = value

    @rx.event
    def create_category(self):
        if not self.has_permission(Action.CATEGORIES_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")

        title = self.new_category_title.strip()
        if title == "":
            return rx.toast.error("Вкажіть назву категорії!")

        category = ProductCategory(title=title, description=self.new_category_description.strip() or None)
        try:
            new_category = ProductCategoryService().add_one(category, self.user.login)
        except ServiceError as e:
            return rx.toast.error(str(e))
        except Exception:
            return rx.toast.error("Під час виконання запиту трапилась помилка. Спробуйте ще раз.")

        # Перезавантажуємо список і одразу обираємо нову категорію в товарі.
        self._load_categories()
        self.item.id_category = new_category.id
        self.is_create_category_open = False
        self._reset_new_category()
        return rx.toast.success("Категорію створено та обрано!")


class ListProductsState(AppState):
    items: Optional[Sequence[ProductCatalog]] = None
    in_progress: bool = True

    _current_page: int = 1
    _all_pages: int = 1
    _limit_items: int = 20
    search_str: Optional[str] = None
    filter_category_id: str = ALL
    list_categories: List[Tuple[str, str]] = []

    def _load_items(self):
        self._all_pages, self.items = ProductCatalogService().get_page(
            page=self._current_page,
            limit=self._limit_items,
            search_str=self.search_str,
            category_id=self.filter_category_id,
        )

    @rx.var
    def get_current_page(self) -> str:
        return str(self._current_page)

    @rx.var
    def get_all_pages(self) -> str:
        return str(self._all_pages)

    @rx.var
    def get_search_str(self) -> str:
        return self.search_str if self.search_str is not None else ""

    @rx.var
    def has_items(self) -> bool:
        return self.items is not None and len(self.items) > 0

    @rx.event
    def on_load(self):
        if not self.has_permission(Action.PRODUCTS_LIST):
            yield rx.redirect(routes.WELCOME)
            yield rx.toast.error("У Вас немає дозволу на перегляд цієї сторінки!")
            return
        try:
            self.in_progress = True
            self._current_page = 1
            self.search_str = None
            self.filter_category_id = ALL
            # Формат (label, id) — інвертований відносно (id, label) сервісу,
            # бо селект фільтра тут рендерить value=id, label=назва.
            self.list_categories = [(label, id) for id, label in ProductCategoryService().get_hierarchy_options()]
            self._load_items()
            self.in_progress = False
        except Exception:
            self.in_progress = False
            yield rx.toast.error("Під час виконання запиту сталася помилка. Спробуйте знову.")

    @rx.event
    def set_search_str(self, value: str):
        # Гарячий пошук: фільтруємо одразу по вводу (з debounce у полі).
        self.search_str = value if value != "" else None
        self._current_page = 1
        self._load_items()

    @rx.event
    def set_filter_category_id(self, value: str):
        self.filter_category_id = value
        self._current_page = 1
        self._load_items()

    @rx.event
    def current_page_increment(self):
        if self._current_page + 1 <= self._all_pages:
            self._current_page += 1
            self._load_items()

    @rx.event
    def current_page_decrement(self):
        if self._current_page > 1:
            self._current_page -= 1
            self._load_items()

    @rx.event
    def on_change_current_page(self, value: str):
        if value != "" and 0 < int(value) <= self._all_pages:
            self._current_page = int(value)
            self._load_items()

    @rx.event
    def on_click_add(self):
        return rx.redirect(routes.CATALOG_PRODUCTS_ADD)


class AddProductsState(CategoryCreateMixin, AppState):
    item: ProductCatalog = ProductCatalog()
    in_process: bool = False
    list_categories: List[Tuple[str, str]] = []
    all_units_cache: List[str] = []

    def _load_categories(self):
        self.list_categories = ProductCategoryService().get_hierarchy_options()

    @rx.event
    def on_load(self):
        if not self.has_permission(Action.PRODUCTS_CREATE):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        self.item = ProductCatalog()
        self._load_categories()
        self.all_units_cache = ProductCatalogService().get_list_units()

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
        return self.item.unit if self.item is not None and self.item.unit is not None else ""

    @rx.var
    def divisible(self) -> bool:
        return bool(self.item.divisible) if self.item is not None else False

    @rx.var
    def uniq(self) -> bool:
        return bool(self.item.uniq) if self.item is not None else False

    @rx.var
    def capacity(self) -> str:
        return str(self.item.capacity) if self.item is not None and self.item.capacity is not None else ""

    @rx.event
    def set_title(self, value: str):
        self.item.title = value if value != "" else None

    @rx.event
    def set_description(self, value: str):
        self.item.description = value if value != "" else None

    @rx.event
    def set_category_id(self, value: str):
        self.item.id_category = int(value) if value.isdigit() and int(value) > 0 else None

    @rx.event
    def set_unit(self, value: str):
        self.item.unit = value if value != "" else None

    @rx.event
    def set_divisible(self, value: bool):
        # Товар із серійним номером (uniq) не може бути подільним.
        if self.item.uniq:
            self.item.divisible = False
            return
        self.item.divisible = value

    @rx.event
    def set_capacity(self, value: str):
        # Товар із серійним номером завжди має місткість 1.
        if self.item.uniq:
            self.item.capacity = 1
            return
        self.item.capacity = int(value) if value.isdigit() and int(value) > 0 else 0

    @rx.event
    def set_uniq(self, value: bool):
        self.item.uniq = value
        if value:
            # Серійний номер ⇒ неподільний, місткість = 1.
            self.item.divisible = False
            self.item.capacity = 1

    @rx.event
    def on_save(self):
        if not self.has_permission(Action.PRODUCTS_CREATE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if not self.item.title:
            yield rx.toast.warning("Вкажіть назву товару!")
            return
        if self.item.id_category is None:
            yield rx.toast.warning("Оберіть категорію товару!")
            return
        if self.item.uniq and self.item.divisible:
            yield rx.toast.warning("Товар із серійним номером не може бути подільним!")
            return
        if self.item.divisible and (self.item.capacity is None or self.item.capacity <= 0):
            yield rx.toast.warning("Для подільного ТМЦ потрібно вказати додатну місткість!")
            return
        if self.item.uniq:
            self.item.capacity = 1
        try:
            self.item = ProductCatalogService().add_one(self.item, self.user.login)
            yield rx.toast.success("Товар додано!")
            yield rx.redirect(routes.CATALOG_PRODUCTS_VIEW_ID + str(self.item.id))
        except ServiceError as e:
            yield rx.toast.warning(str(e))
        except Exception:
            yield rx.toast.error("Під час виконання запиту трапилась помилка. Спробуйте ще раз.")


class EditProductsState(CategoryCreateMixin, AppState):
    item: ProductCatalog = ProductCatalog()
    in_process: bool = False
    list_categories: List[Tuple[str, str]] = []
    all_units_cache: List[str] = []

    def _load_categories(self):
        self.list_categories = ProductCategoryService().get_hierarchy_options()

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(Action.PRODUCTS_EDIT):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        try:
            self.in_process = True
            item = ProductCatalogService().get_by_id(int(id))
            if item is None:
                self.in_process = False
                yield rx.redirect(routes.CATALOG_PRODUCTS)
                yield rx.toast.error("Запис не знайдено!")
                return
            self.item = item
            self._load_categories()
            self.all_units_cache = ProductCatalogService().get_list_units()
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
    def category_id(self) -> str:
        return str(self.item.id_category) if self.item is not None and self.item.id_category is not None else ""

    @rx.var
    def unit(self) -> str:
        return self.item.unit if self.item is not None and self.item.unit is not None else ""

    @rx.var
    def divisible(self) -> bool:
        return bool(self.item.divisible) if self.item is not None else False

    @rx.var
    def uniq(self) -> bool:
        return bool(self.item.uniq) if self.item is not None else False

    @rx.var
    def capacity(self) -> str:
        return str(self.item.capacity) if self.item is not None and self.item.capacity is not None else ""

    @rx.event
    def set_title(self, value: str):
        self.item.title = value if value != "" else None

    @rx.event
    def set_description(self, value: str):
        self.item.description = value if value != "" else None

    @rx.event
    def set_category_id(self, value: str):
        self.item.id_category = int(value) if value.isdigit() and int(value) > 0 else None

    @rx.event
    def set_unit(self, value: str):
        self.item.unit = value if value != "" else None

    @rx.event
    def set_divisible(self, value: bool):
        if self.item.uniq:
            self.item.divisible = False
            return
        self.item.divisible = value

    @rx.event
    def set_capacity(self, value: str):
        if self.item.uniq:
            self.item.capacity = 1
            return
        self.item.capacity = int(value) if value.isdigit() and int(value) > 0 else 0

    @rx.event
    def set_uniq(self, value: bool):
        self.item.uniq = value
        if value:
            self.item.divisible = False
            self.item.capacity = 1

    @rx.event
    def on_save(self):
        if not self.has_permission(Action.PRODUCTS_EDIT):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if not self.item.title:
            yield rx.toast.warning("Вкажіть назву товару!")
            return
        if self.item.id_category is None:
            yield rx.toast.warning("Оберіть категорію товару!")
            return
        if self.item.uniq and self.item.divisible:
            yield rx.toast.warning("Товар із серійним номером не може бути подільним!")
            return
        if self.item.divisible and (self.item.capacity is None or self.item.capacity <= 0):
            yield rx.toast.warning("Для подільного ТМЦ потрібно вказати додатну місткість!")
            return
        if self.item.uniq:
            self.item.capacity = 1
        try:
            self.item = ProductCatalogService().edit_one(self.item, self.user.login)
            yield rx.toast.success("Товар успішно змінено!")
            yield rx.redirect(routes.CATALOG_PRODUCTS_VIEW_ID + str(self.item.id))
        except ServiceError as e:
            yield rx.toast.warning(str(e))
        except Exception:
            yield rx.toast.error("Під час виконання запиту трапилась помилка. Спробуйте ще раз.")


class ViewProductsState(AuditHistoryMixin, AppState):
    HISTORY_TABLE = "products"
    HISTORY_ACTION = Action.PRODUCTS_HISTORY
    HISTORY_DETAIL_ACTION = Action.PRODUCTS_HISTORY_DETAIL

    item: Optional[ProductCatalog] = None
    in_process: bool = True

    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""

    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""

    @rx.var
    def category(self) -> str:
        return self.item.category.title if self.item is not None and self.item.category is not None else ""

    @rx.var
    def unit(self) -> str:
        return self.item.unit if self.item is not None and self.item.unit is not None else ""

    @rx.var
    def divisible(self) -> bool:
        return bool(self.item.divisible) if self.item is not None else False

    @rx.var
    def uniq(self) -> bool:
        return bool(self.item.uniq) if self.item is not None else False

    @rx.var
    def capacity(self) -> str:
        return str(self.item.capacity) if self.item is not None and self.item.capacity is not None else ""

    @rx.var
    def count(self) -> str:
        return str(self.item.count) if self.item is not None and self.item.count is not None else ""

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(Action.PRODUCTS_VIEW):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        try:
            self.in_process = True
            self.item = ProductCatalogService().get_by_id(int(id))
            self.in_process = False
            if self.item is None:
                yield rx.redirect(routes.CATALOG_PRODUCTS)
                yield rx.toast.error("Запис не знайдено!")
                return
            self._load_history(self.item.id)
        except Exception:
            self.in_process = False
            yield rx.toast.error("Під час виконання запиту сталася помилка. Спробуйте знову.")

    @rx.event
    def on_click_edit(self):
        if self.item is None:
            return
        return rx.redirect(routes.CATALOG_PRODUCTS_EDIT_ID + str(self.item.id))

    @rx.event
    def on_click_delete(self):
        if not self.has_permission(Action.PRODUCTS_DELETE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None:
            return
        if ProductCatalogService().delete_one(self.item.id, self.user.login):
            yield rx.toast.success("Товар видалено!")
            yield ListProductsState.on_load()
            yield rx.redirect(routes.CATALOG_PRODUCTS)
        else:
            yield rx.toast.error("Помилка! Товар не знайдено.")
