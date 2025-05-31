import reflex as rx

from typing import List, Tuple

import TrifleSklad.routes as routes
from TrifleSklad.models import Owner
from TrifleSklad.dao import OwnerDAO

class OwnerState(rx.State):
    class Pages:
        ADD = "add"
        EDIT = "edit"
        VIEW = "view"
        LIST = "list"

    current_page: str = Pages.LIST

    items: List[Owner] = []
    selected_item: int = -1

    def _check_path(self):
        page = self.router.page.params.get('page', '')
        if page != '':
            id = -1
            
            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                return rx.redirect(routes.CATALOG_OWNERS)

            # /owners/add
            if page == self.Pages.ADD:
                id = Owner()
            # /owners/edit/[id]
            elif page == self.Pages.EDIT:
                id = self.router.page.params.get('id', '')
                if id != '':
                    id = OwnerDAO.get_by_id(id)
                    if id is None:
                        return [rx.redirect(routes.CATALOG_OWNERS), rx.toast.error("Запись не найдена")]
                else:
                    return rx.redirect(routes.CATALOG_OWNERS)
            # /owners/view/[id]
            elif page == self.Pages.VIEW:
                id = self.router.page.params.get('id', '')
                if id != '':
                    id = OwnerDAO.get_by_id(id)
                    if id is None:
                        return [rx.redirect(routes.CATALOG_OWNERS), rx.toast.error("Запись не найдена")]
                else:
                    return rx.redirect(routes.CATALOG_OWNERS)

            self.items = []
            self.items.append(id) # type: ignore
            self.selected_item = 0
            self.current_page = page
        else:
            # /owners
            self.selected_item = -1
            self.current_page = self.Pages.LIST
            self.items = OwnerDAO.get_all()

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def get_items(self) -> List[Tuple[int, Owner]]:
        return [(index, item) for index, item in enumerate(self.items)]

    @rx.var
    def has_selected_item(self) -> bool:
        return self.selected_item != -1

    @rx.var
    def get_selected_item(self) -> Tuple[int, Owner]:
        if self.selected_item != -1:
            return (self.selected_item, self.items[self.selected_item])
        return (-1, Owner())

    @rx.event
    def on_load(self):
        self._check_path()

    @rx.event
    def add_one(self, form_data: dict):
        flag, text, id = OwnerDAO.add_one(form_data)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_OWNERS_VIEW_ID}{id}")]
        return rx.toast.error(text)

    @rx.event
    def edit_one(self, form_data: dict):
        form_data["id"] = self.items[self.selected_item].id
        flag, text, id = OwnerDAO.edit_one(form_data)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_OWNERS_VIEW_ID}{id}")]
        return rx.toast.error(text)

    @rx.event
    def delete_one(self):
        if self.selected_item != -1:
            flag, text = OwnerDAO.delete_one(self.items[self.selected_item].id)
            if flag:
                return [rx.toast.success(text), rx.redirect(routes.CATALOG_OWNERS)]
            else:
                return [rx.toast.error(text)]
        return rx.toast.error("Не выбрана запись для удаления")
