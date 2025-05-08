import reflex as rx
from typing import Optional, List, Tuple

from TrifleSklad.models import Role
from TrifleSklad.dao import RoleDAO

class RoleState(rx.State):
    class Pages:
        ADD = 'add'
        EDIT = 'edit'
        VIEW = 'view'

    current_page: str = Pages.VIEW

    items: List[Role] = []
    selected_item: int = -1

    @rx.var
    def get_current_page(self) -> str:
        return self.current_page
    
    @rx.var
    def get_current_item(self) -> Tuple[int, Role]:
        return (self.selected_item, self.items[self.selected_item]) if self.selected_item != -1 else (-1, Role())
    
    @rx.var
    def get_items(self) -> List[Tuple[int, Role]]:
        return [(index, item) for index, item in enumerate(self.items)]

    @rx.var
    def has_items(self) -> bool:
        if self.items is not None:
            if len(self.items) > 0:
                return True
        return False
    
    @rx.var
    def has_selected_item(self) -> bool:
        if self.selected_item != -1:
            return True
        return False

    @rx.event
    def load_items(self):
        self.items = RoleDAO.get_all()

    @rx.event
    def set_select_item(self, item: int):
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