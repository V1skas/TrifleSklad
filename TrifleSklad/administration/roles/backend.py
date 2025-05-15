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
            if page == self.Pages.ADD:
                id = Role()
            # /roles/edit/[id]
            elif page == self.Pages.EDIT:
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
            else:
                return [rx.toast.error(text)]
        return rx.toast.error("Не выбрана запись для удаления")
    

class RoleSelectorState(rx.State):
    items: List[Role] = []
    unselected_items: List[int] = []
    selected_items: List[int] = []
    unselected_items_filtered: List[int] = []
    selected_items_filtered: List[int] = []
    filter: str = ""
    
    def _load_items(self) -> None:
        self.items = RoleDAO.get_all()
        self.filter = ""

    def _set_selected_items(self, items: List[Role]) -> None:
        self.selected_items = [i for i in range(len(self.items)) if self.items[i] in items]
        self.unselected_items = [i for i in range(len(self.items)) if self.items[i] not in items]
        self.set_filter("")

    @rx.var
    def get_id_selected_items(self) -> List[int]:
        return [self.items[index].id for index in reversed(self.selected_items)] if len(self.selected_items) > 0 else []

    @rx.var
    def get_selected_items(self) -> List[Tuple[int, Role]]:
        if self.filter != "":
            return [(index, self.items[index]) for index in reversed(self.selected_items_filtered)]
        else:
            return [(index, self.items[index]) for index in reversed(self.selected_items)]
    
    @rx.var
    def get_unselected_items(self) -> List[Tuple[int, Role]]:
        if self.filter != "":
            return [(index, self.items[index]) for index in reversed(self.unselected_items_filtered)]
        else:
            return [(index, self.items[index]) for index in self.unselected_items]
    
    @rx.event
    def on_load(self, selected_items: List[Role]) -> None:
        self._load_items()
        self._set_selected_items(selected_items)
        self.set_filter("")
    
    @rx.event
    def select_item(self, item: int) -> None:
        if item in self.selected_items:
            self.unselected_items.append(item)
            self.unselected_items.sort()
            self.selected_items.remove(item)
        else:
            self.selected_items.append(item)
            self.unselected_items.remove(item)
        self.set_filter(self.filter)

    @rx.event
    def set_filter(self, filter: str) -> None:
        self.filter = filter
        self.unselected_items_filtered = [i for i in self.unselected_items if self.items[i].title.lower().find(filter.lower()) != -1]
        self.selected_items_filtered = [i for i in self.selected_items if self.items[i].title.lower().find(filter.lower()) != -1]