import reflex as rx

from typing import List, Tuple

import TrifleSklad.routes as routes
from TrifleSklad.models import Supplier
from TrifleSklad.dao import SupplierDAO


class SupplierState(rx.State):
    class Pages:
        ADD = 'add'
        EDIT = 'edit'
        VIEW = 'view'
        LIST = 'list'

    current_page: str = Pages.LIST

    items: List[Supplier] = []
    selected_item: int = -1

    def _check_path(self):
        page = self.router.page.params.get('page', '')
        if page != '':
            id = -1
            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                return rx.redirect(routes.CATALOG_SUPPLIERS)

            # /suppliers/add
            if page == self.Pages.ADD:
                id = Supplier()
            # /suppliers/edit/[id]
            elif page == self.Pages.EDIT:
                id = self.router.page.params.get('id', '')
                if id != '':
                    id = SupplierDAO.get_by_id(id)
                    if id is None:
                        return [rx.redirect(routes.CATALOG_SUPPLIERS), rx.toast.error("Запись не была найдена")]
                else:
                    return rx.redirect(routes.CATALOG_SUPPLIERS)
            # /suppliers/view/[id]
            elif page == self.Pages.VIEW:
                id = self.router.page.params.get('id', '')
                if id != '':
                    id = SupplierDAO.get_by_id(id)
                    if id is None:
                        return [rx.redirect(routes.CATALOG_SUPPLIERS), rx.toast.error("Запись не была найдена")]
                else:
                    return rx.redirect(routes.CATALOG_SUPPLIERS)

            self.items = []
            self.items.append(id) # type: ignore
            self.selected_item = 0
            self.current_page = page
        else:
            # /suppliers
            self.selected_item = -1
            self.current_page = self.Pages.LIST
            self.items = SupplierDAO.get_all()

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def get_items(self) -> List[Tuple[int, Supplier]]:
        return [(index, item) for index, item in enumerate(self.items)]

    @rx.var
    def has_selected_item(self) -> bool:
        return self.selected_item != -1

    @rx.var
    def get_selected_item(self) -> Tuple[int, Supplier]:
        if self.selected_item != -1:
            return (self.selected_item, self.items[self.selected_item])
        return (-1, Supplier())

    @rx.event
    def on_load(self):
        self._check_path()

    @rx.event
    def add_one(self, form_data: dict):
        flag, text, id = SupplierDAO.add_one(form_data)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_SUPPLIERS_VIEW_ID}{id}")]
        return rx.toast.error(text)

    @rx.event
    def edit_one(self, form_data: dict):
        form_data["id"] = self.items[self.selected_item].id
        flag, text, id = SupplierDAO.edit_one(form_data)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_SUPPLIERS_VIEW_ID}{id}")]
        return rx.toast.error(text)

    @rx.event
    def delete_one(self):
        if self.selected_item != -1:
            flag, text = SupplierDAO.delete_one(self.items[self.selected_item].id)
            if flag:
                return [rx.toast.success(text), rx.redirect(routes.CATALOG_SUPPLIERS)]
            else:
                return [rx.toast.error(text)]
        return rx.toast.error("Не выбрана запись для удаления")
