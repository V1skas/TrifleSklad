import reflex as rx
from typing import Optional, List, Tuple

from TrifleSklad.models import Role, Action
from TrifleSklad.dao import RoleDAO
import TrifleSklad.routes as routes

class RoleState(rx.State):
    class Pages:
        ADD = 'add'
        EDIT = 'edit'
        VIEW = 'view'
        LIST = 'list'

    current_page: str = Pages.LIST

    items: List[Role] = []
    selected_item: int = -1

    selected_actions: List[Action] = []

    def _find_item(self, id: str) -> Optional[int]:
        for index, item in enumerate(self.items):
            if item.id == id:
                return index
        return None

    def _load_items(self):
        self.items = RoleDAO.get_all()

    def _check_path(self):
        print("RoleState._check_path")
        page = self.router.page.params.get("page", "")
        if page != "":
            id = -1
            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                return rx.redirect(routes.ADMIN_ROLES)
            
            # /roles/add
            # Дейсвтвий не требуется
            # /roles/edit/[id]
            if page == self.Pages.EDIT:
                id = self.router.page.params.get("id", "")
                if id != "":
                    id = self._find_item(id)
                    if id is None:
                        return [rx.redirect(routes.ADMIN_ROLES), rx.toast.error("Запись не была найдена")]
                else:
                    return rx.redirect(routes.ADMIN_ROLES)
            # /roles/view/[id]
            elif page == self.Pages.VIEW:
                id = self.router.page.params.get("id", "")
                if id != "":
                    id = self._find_item(id)
                    if id is None:
                        return [rx.redirect(routes.ADMIN_ROLES), rx.toast.error("Запись не была найдена")]
                else:
                    return rx.redirect(routes.ADMIN_ROLES)
                
            self.selected_item = id
            self.current_page = page
        else:
            # /roles
            self.selected_item = -1
            self.current_page = self.Pages.LIST
    
    @rx.var
    def has_items(self) -> bool:
        if self.items is not None:
            if len(self.items) > 0:
                return True
        return False

    @rx.var
    def get_items(self) -> List[Tuple[int, Role]]:
        return [(index, item) for index, item in enumerate(self.items)]
    
    @rx.var
    def has_selected_item(self) -> bool:
        if self.selected_item != -1:
            return True
        return False
    
    @rx.var
    def get_selected_item(self) -> Tuple[int, Role]:
        if self.selected_item != -1:
            return (self.selected_item, self.items[self.selected_item])
        return(-1, Role())
    
    @rx.var
    def has_selected_actions(self) -> bool:
        if len(self.selected_actions) > 0:
            return True
        return False
    
    @rx.event
    def on_load(self):
        print("RoleState.on_load")
        self._load_items()
        self._check_path()
        print(f"Current page: {self.current_page}")
        print(f"Selected item: {self.selected_item}\n")

    @rx.event
    def set_selected_actions(self, actions: List[Action]):
        self.selected_actions = actions
    
    @rx.event
    def add_one(self, form_data: dict):
        form_data["actions"] = self.selected_actions
        flag, text, id = RoleDAO.add_one(form_data)
        if flag:
            self.load_items()
            return [rx.toast.success(text), rx.redirect(routes.ADMIN_ROLES_VIEW_ID+str(id))]
        return rx.toast.error(text)
    
    @rx.event
    def edit_one(self, form_data: dict):
        form_data["id"] = self.selected_item.id
        flag, text, id = RoleDAO.edit_one(form_data)
        if flag:
            self.load_items()
            return [rx.toast.success(text), rx.redirect(routes.ADMIN_ROLES_VIEW_ID+str(id))]
        return rx.toast.error(text)