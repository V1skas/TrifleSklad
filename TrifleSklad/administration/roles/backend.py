import reflex as rx
from typing import Optional, List

from TrifleSklad.models import Role
from TrifleSklad.dao import RoleDAO

class RoleState(rx.State):
    class Pages:
        ADD = 'add'
        EDIT = 'edit'
        VIEW = 'view'

    current_page: str = Pages.VIEW

    items: Optional[List[Role]] = None
    selected_item: Optional[Role]

    @rx.var
    def get_current_page(self) -> str:
        return self.current_page

    @rx.var
    def has_items(self) -> bool:
        if self.items is not None:
            if len(self.items) > 0:
                return True
        return False
    
    @rx.var
    def has_selected_item(self) -> bool:
        if self.selected_item is not None:
            return True
        return False

    @rx.event
    def load_items(self):
        self.items = RoleDAO.get_all()

    @rx.event
    def set_select_item(self, item: Optional[Role]):
        self.selected_item = item

    @rx.event
    def set_current_page(self, new_page: str):
        self.current_page = new_page
    
    @rx.event
    def add_one(self, form_data: dict):
        flag, text = RoleDAO.add_one(form_data)
        if flag:
            self.load_items()
            return [rx.toast.success(text), RoleState.set_current_page(RoleState.Pages.VIEW)]
        return rx.toast.error(text)
    
    @rx.event
    def edit_one(self, form_data: dict):
        form_data["id"] = self.selected_item.id
        flag, text = RoleDAO.edit_one(form_data)
        if flag:
            self.load_items()
            return [rx.toast.success(text), RoleState.set_current_page(RoleState.Pages.VIEW)]
        return rx.toast.error(text)