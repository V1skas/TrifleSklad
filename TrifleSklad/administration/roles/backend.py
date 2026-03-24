import reflex as rx
from typing import Optional, List, Tuple, Dict

from TrifleSklad.models import Role, Action
from TrifleSklad.dao import RoleDAO, ActionDAO
import TrifleSklad.routes as routes
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum

from TrifleSklad.administration.actions.backend import ActionsState


class ViewRoleState(rx.State):
    item: Role = Role(
        title="",
        description="",
        actions=[]
    )

    app_state: Optional[AppState] = None
    actions_state: Optional[ActionsState] = None

    # Frontend vars
    # ======================
    @rx.var
    def has_actions(self) -> bool:
        return len(self.item.actions) > 0
    # ======================

    # Actions handlers
    # ======================
    @rx.event
    async def on_load(self, id: int):
        self.app_state = await self.get_state(AppState)
        self.actions_state = await self.get_state(ActionsState)
        self.item = RoleDAO.get_by_id_with_relationships(id)
        if self.item is None:
            return [rx.redirect(routes.ADMIN_ROLES), rx.toast.error("Запис не було знайдено")]
        self.actions_state.on_load(self.item.actions)
    # ======================


class AddRoleState(rx.State):
    item: Role = Role(
        title="",
        description="",
        actions=[]
    )

    app_state: Optional[AppState] = None
    actions_state: Optional[ActionsState] = None

    # Frontend vars
    # ======================
    @rx.var
    def has_selected_actions(self) -> bool:
        return len(self.item.actions) > 0
    # ======================

    # Actions handlers
    # ======================
    @rx.event
    async def on_load(self):
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
        if self.actions_state is None:
            self.actions_state = await self.get_state(ActionsState)
        self.load_item()
        self.actions_state.on_load(self.item.actions)

    @rx.event
    def load_item(self):
        self.item = Role(
            title="",
            description="",
            actions=[]
        )

    @rx.event
    def change_title(self, title: str):
        self.item.title = title

    @rx.event
    def change_description(self, description: str):
        self.item.description = description

    @rx.event
    def change_actions(self):
        self.item.actions = self.actions_state._get_selected_items()

    @rx.event
    def open_actions(self):
        self.actions_state.on_load(self.item.actions)

    @rx.event
    def add_one(self):
        if not self.app_state.has_permission(ActionEnum.ROLES_CREATE):
            return rx.toast.error("У вас недостатньо прав для виконання цієї дії!")
        
        if len(self.item.actions) == 0 or self.item.title == "":
            return rx.toast.error("Заповніть всі обов'язкові поля!")
        
        flag, text, id = RoleDAO.add_one(self.item)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.ADMIN_ROLES_VIEW_ID}{id}")]
        return rx.toast.error(text)
    # ======================


class EditRoleState(rx.State):
    item: Role = Role(
        title="",
        description="",
        actions=[]
    )

    app_state: Optional[AppState] = None
    actions_state: Optional[ActionsState] = None

    # Frontend vars
    # ======================
    @rx.var
    def has_selected_actions(self) -> bool:
        return len(self.item.actions) > 0
    # ======================

    # Actions handlers
    # ======================
    @rx.event
    async def on_load(self, id: int):
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
        if self.actions_state is None:
            self.actions_state = await self.get_state(ActionsState)

        self.item = RoleDAO.get_by_id_with_relationships(id)
        if self.item is None:
            return [rx.redirect(routes.ADMIN_ROLES), rx.toast.error("Запис не було знайдено")]
        self.actions_state.on_load(self.item.actions)
    
    @rx.event
    def change_title(self, title: str):
        self.item.title = title

    @rx.event
    def change_description(self, description: str):
        self.item.description = description

    @rx.event
    def change_actions(self):
        print(self.actions_state._get_selected_items())
        self.item.actions = self.actions_state._get_selected_items()

    @rx.event
    def open_actions(self):
        self.actions_state.on_load(self.item.actions)

    @rx.event
    def edit_one(self):
        if not self.app_state.has_permission(ActionEnum.ROLES_EDIT):
            return rx.toast.error("У вас недостатньо прав для виконання цієї дії!")
        
        if len(self.item.actions) == 0 or self.item.title == "":
            return rx.toast.error("Заповніть всі обов'язкові поля!")
        
        print(self.item)

        flag, text, id = RoleDAO.edit_one(self.item)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.ADMIN_ROLES_VIEW_ID}{id}")]
        return rx.toast.error(text)
    # ======================


class ListRoleState(rx.State):
    items: List[Role] = []

    app_state: Optional[AppState] = None

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    # Actions handlers
    # ======================
    @rx.event
    async def on_load(self):
        self.app_state = await self.get_state(AppState)
        self.items = RoleDAO.get_all()
    # ======================


class RoleState(rx.State):
    class Pages:
        ADD = 'add'
        EDIT = 'edit'
        VIEW = 'view'
        LIST = 'list'

    current_page: str = Pages.LIST
    app_state: Optional[AppState] = None

    def _check_path(self):
        page = self.router.page.params.get("page", "")
        if page != "":
            id = -1
            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                return rx.redirect(routes.ADMIN_ROLES)
            
            # /roles/add
            if page == self.Pages.ADD:
                if not self.app_state.has_permission(ActionEnum.ROLES_CREATE):
                    return rx.redirect(routes.WELCOME)
                yield AddRoleState.on_load()
                
            # /roles/edit/[id]
            elif page == self.Pages.EDIT:
                if not self.app_state.has_permission(ActionEnum.ROLES_EDIT):
                    return rx.redirect(routes.WELCOME)
                id = self.router.page.params.get("id", "")
                if id != "":
                    yield EditRoleState.on_load(id)
                else:
                    return rx.redirect(routes.ADMIN_ROLES)
            # /roles/view/[id]
            elif page == self.Pages.VIEW:
                if not self.app_state.has_permission(ActionEnum.ROLES_VIEW):
                    return rx.redirect(routes.WELCOME)
                id = self.router.page.params.get("id", "")
                if id != "":
                    yield ViewRoleState.on_load(id)
                else:
                    return rx.redirect(routes.ADMIN_ROLES)
                
            self.current_page = page
        else:
            # /roles
            if not self.app_state.has_permission(ActionEnum.ROLES_LIST):
                    return rx.redirect(routes.WELCOME)
            yield ListRoleState.on_load()
            self.current_page = self.Pages.LIST
    
    @rx.event
    async def on_load(self):
        self.app_state = await self.get_state(AppState)
        return self._check_path()
    
    @rx.event
    def delete_one(self, id: int):
        if id is not None:
            if not self.app_state.has_permission(ActionEnum.ROLES_DELETE):
                return rx.toast.error("У вас недостатньо прав для виконання цієї дії!")

            flag, text = RoleDAO.delete_one(id)
            if flag:
                return [rx.toast.success(text), rx.redirect(routes.ADMIN_ROLES)]
            else:
                return [rx.toast.error(text)]
        return rx.toast.error("Не обрано запис для видалення")
    

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

    def _get_selected_items(self) -> List[Role]:
        return [self.items[index] for index in reversed(self.selected_items)] if len(self.selected_items) > 0 else []


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