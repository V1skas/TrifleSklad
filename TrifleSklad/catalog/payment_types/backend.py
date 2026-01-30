import reflex as rx

from typing import List, Tuple

import TrifleSklad.routes as routes
from TrifleSklad.models import PaymentType
from TrifleSklad.dao import PaymentTypeDAO

class PaymentTypeState(rx.State):
    class Pages:
        ADD = "add"
        EDIT = "edit"
        VIEW = "view"
        LIST = "list"

    current_page: str = ""

    items: List[PaymentType] = []
    selected_item: int = -1

    def _check_path(self):
        page = self.router.page.params.get('page', '')
        if page != '':
            id = -1

            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                return rx.redirect(routes.CATALOG_PAYMENT_TYPES)

            # /payment_types/add
            if page == self.Pages.ADD:
                id = PaymentType()
            # /payment_types/edit/[id]
            elif page == self.Pages.EDIT:
                id = self.router.page.params.get('id', '')
                if id != '':
                    id = PaymentTypeDAO.get_by_id(id)
                    if id is None:
                        return [rx.redirect(routes.CATALOG_PAYMENT_TYPES), rx.toast.error("Запись не найдена")]
                else:
                    return rx.redirect(routes.CATALOG_PAYMENT_TYPES)
            # /payment_types/view/[id]
            elif page == self.Pages.VIEW:
                id = self.router.page.params.get('id', '')
                if id != '':
                    id = PaymentTypeDAO.get_by_id(id)
                    if id is None:
                        return [rx.redirect(routes.CATALOG_PAYMENT_TYPES), rx.toast.error("Запись не найдена")]
                else:
                    return rx.redirect(routes.CATALOG_PAYMENT_TYPES)

            self.items = []
            self.items.append(id)  # type: ignore
            self.selected_item = 0
            self.current_page = page
        else:
            # /payment_types
            self.selected_item = -1
            self.items = PaymentTypeDAO.get_all()
            self.current_page = self.Pages.LIST

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def get_items(self) -> List[Tuple[int, PaymentType]]:
        return [(index, item) for index, item in enumerate(self.items)]

    @rx.var
    def has_selected_item(self) -> bool:
        return self.selected_item != -1

    @rx.var
    def get_selected_item(self) -> Tuple[int, PaymentType]:
        if self.selected_item != -1:
            return (self.selected_item, self.items[self.selected_item])
        return (-1, PaymentType())

    @rx.event
    def on_load(self):
        self._check_path()

    @rx.event
    def add_one(self, form_data: dict):
        flag, text, id = PaymentTypeDAO.add_one(form_data)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_PAYMENT_TYPES_VIEW_ID}{id}")]
        return rx.toast.error(text)

    @rx.event
    def edit_one(self, form_data: dict):
        form_data["id"] = self.items[self.selected_item].id
        flag, text, id = PaymentTypeDAO.edit_one(form_data)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_PAYMENT_TYPES_VIEW_ID}{id}")]
        return rx.toast.error(text)

    @rx.event
    def delete_one(self):
        if self.selected_item != -1:
            flag, text = PaymentTypeDAO.delete_one(self.items[self.selected_item].id)
            if flag:
                return [rx.toast.success(text), rx.redirect(routes.CATALOG_PAYMENT_TYPES)]
            else:
                return [rx.toast.error(text)]
        return rx.toast.error("Не выбрана запись для удаления")