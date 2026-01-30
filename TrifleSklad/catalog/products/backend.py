import reflex as rx

from typing import List, Tuple, Optional

import TrifleSklad.routes as routes
from TrifleSklad.models import ProductCatalog, ProductCategory
from TrifleSklad.dao import ProductCatalogDAO, ProductCategoryDAO

class ProductsState(rx.State):
    class Pages:
        ADD = 'add'
        EDIT = 'edit'
        VIEW = 'view'
        LIST = 'list'

    current_page: str = Pages.LIST

    items: List[ProductCatalog] = []
    selected_item: int = -1

    selected_product_category_id: str = ""
    product_category_list: List[Tuple[str, str]] = []

    def _load_product_category_list(self):
        self.product_category_list = [
            (category.title, str(category.id))
            for category in ProductCategoryDAO.get_all()
        ]

    def _check_path(self):
        page = self.router.page.params.get('page', '')
        if page != '':
            id = -1
            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                return rx.redirect(routes.CATALOG_PRODUCTS)

            # /products/add
            if page == self.Pages.ADD:
                id = ProductCatalog()
                self._load_product_category_list()
                self.selected_product_category_id = ""
            # /products/edit/[id]
            elif page == self.Pages.EDIT:
                id = self.router.page.params.get('id', '')
                if id != '':
                    id = ProductCatalogDAO.get_by_id_with_relationships(id)
                    if id is None:
                        return [rx.redirect(routes.CATALOG_PRODUCTS), rx.toast.error("Запись не была найдена")]
                    self._load_product_category_list()
                    self.selected_product_category_id = str(id.id_category) if id.id_category else ""
                else:
                    return rx.redirect(routes.CATALOG_PRODUCTS)
            # /products/view/[id]
            elif page == self.Pages.VIEW:
                id = self.router.page.params.get('id', '')
                if id != '':
                    id = ProductCatalogDAO.get_by_id_with_relationships(id)
                    if id is None:
                        return [rx.redirect(routes.CATALOG_PRODUCTS), rx.toast.error("Запись не была найдена")]
                else:
                    return rx.redirect(routes.CATALOG_PRODUCTS)

            self.items = []
            self.items.append(id) # type: ignore
            self.selected_item = 0
            self.current_page = page
        else:
            # /products
            self.selected_item = -1
            self.current_page = self.Pages.LIST
            self.items = ProductCatalogDAO.get_all_with_relationships()

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def get_items(self) -> List[Tuple[int, ProductCatalog]]:
        return [(index, item) for index, item in enumerate(self.items)]

    @rx.var
    def has_selected_item(self) -> bool:
        return self.selected_item != -1

    @rx.var
    def get_selected_item(self) -> Tuple[int, ProductCatalog]:
        if self.selected_item != -1:
            return (self.selected_item, self.items[self.selected_item])
        return (-1, ProductCatalog())

    @rx.event
    def on_load(self):
        return self._check_path()

    @rx.event
    def on_change_product_category(self, value: str):
        self.selected_product_category_id = value

    @rx.event
    def add_one(self, form_data: dict):
        form_data["id_category"] = self.selected_product_category_id

        flag, text, id = ProductCatalogDAO.add_one(form_data)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_PRODUCTS_VIEW_ID}{id}")]
        return rx.toast.error(text)

    @rx.event
    def edit_one(self, form_data: dict):
        form_data["id"] = self.items[self.selected_item].id
        form_data["id_category"] = self.selected_product_category_id
            
        flag, text, id = ProductCatalogDAO.edit_one(form_data)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_PRODUCTS_VIEW_ID}{id}")]
        return rx.toast.error(text)

    @rx.event
    def delete_one(self):
        if self.selected_item != -1:
            flag, text = ProductCatalogDAO.delete_one(self.items[self.selected_item].id)
            if flag:
                return [rx.toast.success(text), rx.redirect(routes.CATALOG_PRODUCTS)]
            else:
                return [rx.toast.error(text)]
        return rx.toast.error("Не выбрана запись для удаления")
