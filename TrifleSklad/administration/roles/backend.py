import reflex as rx
from typing import Optional, List, Tuple, Dict

from TrifleSklad.models import Role, Action
from TrifleSklad.dao import RoleDAO, ActionDAO
import TrifleSklad.routes as routes

from TrifleSklad.administration.actions.backend import ActionsState

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

    def _check_path(self):
        print("RoleState._check_path")
        print(f"Params page: {self.router.page.params.get("page", "")}")
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
                    id = RoleDAO.get_by_id_with_relationships(id)
                    if id is None:
                        return [rx.redirect(routes.ADMIN_ROLES), rx.toast.error("Запись не была найдена")]
                else:
                    return rx.redirect(routes.ADMIN_ROLES)
            # /roles/view/[id]
            elif page == self.Pages.VIEW:
                id = self.router.page.params.get("id", "")
                if id != "":
                    id = RoleDAO.get_by_id_with_relationships(id)
                    if id is None:
                        return [rx.redirect(routes.ADMIN_ROLES), rx.toast.error("Запись не была найдена")]
                else:
                    return rx.redirect(routes.ADMIN_ROLES)
                
            self.items = []
            self.items.append(id)
            self.selected_item = 0
            self.selected_actions = id.actions
            self.current_page = page
        else:
            # /roles
            self.selected_item = -1
            self.current_page = self.Pages.LIST
            self.items = RoleDAO.get_all()
    
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
        return self._check_path()

    @rx.event
    def set_selected_actions(self, actions: List[str]):
        self.selected_actions = ActionDAO.get_by_list_id(actions)
    
    @rx.event
    def add_one(self, form_data: dict):
        form_data["actions"] = self.selected_actions
        print(f"RoleState.add_one: {form_data}")
        flag, text, id = RoleDAO.add_one(form_data)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.ADMIN_ROLES_VIEW_ID}{id}")]
        return rx.toast.error(text)
    
    @rx.event
    def edit_one(self, form_data: dict):
        form_data["id"] = self.items[self.selected_item].id
        form_data["actions"] = [action.id for action in self.selected_actions]
        flag, text, id = RoleDAO.edit_one(form_data)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.ADMIN_ROLES_VIEW_ID}{id}")]
        return rx.toast.error(text)
    
    @rx.event
    def delete_one(self):
        if self.selected_item != -1:
            flag, text = RoleDAO.delete_one(self.items[self.selected_item].id)
            if flag:
                return [rx.toast.success(text), rx.redirect(routes.ADMIN_ROLES)]
            return rx.toast.error(text)
        return rx.toast.error("Не выбрана запись для удаления")