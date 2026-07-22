from typing import List, Optional, Sequence, Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.models import ProductCategory
from TrifleSklad.services.errors import ServiceError
from TrifleSklad.services.product_category import ProductCategoryService
from TrifleSklad.states.app import AppState
from TrifleSklad.states.audit_mixin import AuditHistoryMixin

# Сентинел «без батьківської категорії» для селекту (Radix забороняє порожнє value item).
NONE = "none"


class ListCategoriesState(AppState):
    items: Optional[Sequence[ProductCategory]] = None
    in_progress: bool = True

    @rx.var
    def has_items(self) -> bool:
        return self.items is not None and len(self.items) > 0

    @rx.event
    def on_load(self):
        if not self.has_permission(Action.CATEGORIES_LIST):
            yield rx.redirect(routes.WELCOME)
            yield rx.toast.error("У Вас немає дозволу на перегляд цієї сторінки!")
            return
        try:
            self.in_progress = True
            self.items = ProductCategoryService().get_list_items()
            self.in_progress = False
        except Exception:
            yield rx.toast.error("Під час виконання запиту сталася помилка. Спробуйте знову.")

    @rx.event
    def on_click_add(self):
        return rx.redirect(routes.CATALOG_CATEGORIES_ADD)


class AddCategoriesState(AppState):
    item: ProductCategory = ProductCategory()
    in_process: bool = False
    list_parent_categories: List[Tuple[str, str]] = []
    parent_id: str = NONE

    @rx.event
    def on_load(self):
        if not self.has_permission(Action.CATEGORIES_CREATE):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        self.item = ProductCategory()
        self.parent_id = NONE
        self.list_parent_categories = ProductCategoryService().get_top_level_options()

    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""

    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""

    @rx.event
    def set_title(self, value: str):
        self.item.title = value

    @rx.event
    def set_description(self, value: str):
        self.item.description = value if value != "" else None

    @rx.event
    def set_parent_id(self, value: str):
        self.parent_id = value

    @rx.event
    def on_save(self):
        if not self.has_permission(Action.CATEGORIES_CREATE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if not self.item.title:
            yield rx.toast.warning("Не заповнені обов'язкові поля!")
            return
        self.item.id_parent = int(self.parent_id) if self.parent_id != NONE else None
        try:
            self.item = ProductCategoryService().add_one(self.item, self.user.login)
            yield rx.toast.success("Категорію успішно додано!")
            yield rx.redirect(routes.CATALOG_CATEGORIES_VIEW_ID + str(self.item.id))
        except ServiceError as e:
            yield rx.toast.warning(str(e))
        except Exception:
            yield rx.toast.error("Під час виконання запиту трапилась помилка. Спробуйте ще раз.")


class EditCategoriesState(AppState):
    item: ProductCategory = ProductCategory()
    in_process: bool = False
    list_parent_categories: List[Tuple[str, str]] = []
    parent_id: str = NONE
    can_set_parent: bool = True

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(Action.CATEGORIES_EDIT):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        try:
            self.in_process = True
            item = ProductCategoryService().get_by_id(int(id))
            if item is None:
                self.in_process = False
                yield rx.redirect(routes.CATALOG_CATEGORIES)
                yield rx.toast.error("Запис не було знайдено")
                return
            self.item = item
            self.parent_id = str(item.id_parent) if item.id_parent is not None else NONE
            self.can_set_parent = len(ProductCategoryService().get_children(item.id)) == 0
            self.list_parent_categories = ProductCategoryService().get_top_level_options(exclude_id=item.id)
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

    @rx.event
    def set_title(self, value: str):
        self.item.title = value

    @rx.event
    def set_description(self, value: str):
        self.item.description = value if value != "" else None

    @rx.event
    def set_parent_id(self, value: str):
        self.parent_id = value

    @rx.event
    def on_save(self):
        if not self.has_permission(Action.CATEGORIES_EDIT):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if not self.item.title:
            yield rx.toast.warning("Не заповнені обов'язкові поля!")
            return
        self.item.id_parent = int(self.parent_id) if self.can_set_parent and self.parent_id != NONE else None
        try:
            self.item = ProductCategoryService().edit_one(self.item, self.user.login)
            yield rx.toast.success("Категорію успішно змінено!")
            yield rx.redirect(routes.CATALOG_CATEGORIES_VIEW_ID + str(self.item.id))
        except ServiceError as e:
            yield rx.toast.warning(str(e))
        except Exception:
            yield rx.toast.error("Під час виконання запиту трапилась помилка. Спробуйте ще раз.")


class ViewCategoriesState(AuditHistoryMixin, AppState):
    HISTORY_TABLE = "categories"
    HISTORY_ACTION = Action.CATEGORIES_HISTORY
    HISTORY_DETAIL_ACTION = Action.CATEGORIES_HISTORY_DETAIL

    item: Optional[ProductCategory] = None
    in_process: bool = True
    parent_title: str = ""
    children: List[ProductCategory] = []

    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""

    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(Action.CATEGORIES_VIEW):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        try:
            self.in_process = True
            service = ProductCategoryService()
            self.item = service.get_by_id(int(id))
            if self.item is None:
                self.in_process = False
                yield rx.redirect(routes.CATALOG_CATEGORIES)
                yield rx.toast.error("Запис не було знайдено")
                return
            self.parent_title = ""
            if self.item.id_parent is not None:
                parent = service.get_by_id(self.item.id_parent)
                self.parent_title = parent.title if parent is not None else ""
            self.children = list(service.get_children(self.item.id))
            self._load_history(self.item.id)
            self.in_process = False
        except Exception:
            self.in_process = False
            yield rx.toast.error("Під час виконання запиту сталася помилка. Спробуйте знову.")

    @rx.event
    def on_click_edit(self):
        if self.item is None:
            return
        return rx.redirect(routes.CATALOG_CATEGORIES_EDIT_ID + str(self.item.id))

    @rx.event
    def on_click_delete(self):
        if not self.has_permission(Action.CATEGORIES_DELETE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None:
            return
        try:
            if ProductCategoryService().delete_one(self.item.id, self.user.login):
                yield rx.toast.success("Категорію видалено!")
                yield ListCategoriesState.on_load()
                yield rx.redirect(routes.CATALOG_CATEGORIES)
            else:
                yield rx.toast.error("Помилка! Категорію не знайдено.")
        except ServiceError as e:
            yield rx.toast.warning(str(e))
