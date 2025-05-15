import reflex as rx
from typing import Optional, List, Tuple, Dict
import hashlib
import os

from TrifleSklad.models import User, Role, Action, Worker
from TrifleSklad.dao import UserDAO, RoleDAO, ActionDAO, WorkerDAO
import TrifleSklad.routes as routes

from TrifleSklad.administration.actions.backend import ActionsState

class UserState(rx.State):
    class Pages:
        ADD = 'add'
        EDIT = 'edit'
        VIEW = 'view'
        LIST = 'list'

    current_page: str = Pages.LIST

    items: List[User] = []
    selected_item: int = -1

    selected_roles: List[Role] = []
    selected_actions: List[Action] = []

    def _check_path(self):
        page = self.router.page.params.get('page', '')
        if page != '':
            id = -1
            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                return rx.redirect(routes.ADMIN_USERS)
            
            # /users/add
            if page == self.Pages.ADD:
                id = User()
            # /users/edit/[id]
            elif page == self.Pages.EDIT:
                id = self.router.page.params.get('id', '')
                if id != '':
                    id = UserDAO.get_user_by_id_with_relationships(id)
                    if id is None:
                        return [rx.redirect(routes.ADMIN_USERS), rx.toast.error("Запись не была найдена")]
                else:
                    return rx.redirect(routes.ADMIN_USERS)
            # /users/view/[id]
            elif page == self.Pages.VIEW:
                id = self.router.page.params.get('id', '')
                if id != '':
                    id = UserDAO.get_user_by_id_with_relationships(id)
                    if id is None:
                        return [rx.redirect(routes.ADMIN_USERS), rx.toast.error("Запись не была найдена")]
                else:
                    return rx.redirect(routes.ADMIN_USERS)
                
            self.items = []
            self.items.append(id)
            self.selected_item = 0
            self.selected_roles = id.roles
            self.selected_actions = id.actions
            self.current_page = page
        else:
            # /users
            self.selected_item = -1
            self.current_page = self.Pages.LIST
            self.items = UserDAO.get_all_with_relationships()
        
    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0
    
    @rx.var
    def get_items(self) -> List[Tuple[int, User]]:
        return [(index, item) for index, item in enumerate(self.items)]
    
    @rx.var
    def has_selected_item(self) -> bool:
        return self.selected_item != -1
    
    @rx.var
    def get_selected_item(self) -> Tuple[int, User]:
        if self.selected_item != -1:
            return (self.selected_item, self.items[self.selected_item])
        return (-1, User())
    
    @rx.var
    def has_selected_roles(self) -> bool:
        return len(self.selected_roles) > 0
    
    @rx.var
    def has_selected_actions(self) -> bool:
        return len(self.selected_actions) > 0
    
    @rx.event
    def on_load(self):
        return self._check_path()
    
    @rx.event
    def set_selected_roles(self, roles: List[str]):
        self.selected_roles = RoleDAO.get_by_list_id(roles)

    @rx.event
    def set_selected_actions(self, actions: List[str]):
        self.selected_actions = ActionDAO.get_by_list_id(actions)

    @rx.event
    def add_one(self, form_data: dict):
        worker = WorkerDAO.get_by_fio(form_data['worker'])
        if worker is None:
            return rx.toast.error("Не удалось добавить пользователя. Сотрудник не найден.")
        
        # --- Проверка и хеширование пароля ---
        password = form_data.get('password')
        if password is not None:
            # Проверка на запрещённые символы
            forbidden = set(' абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ')
            if any(ch in forbidden for ch in password):
                return rx.toast.error("Пароль содержит недопустимые символы.")
            salt = os.urandom(16).hex()
            hash_obj = hashlib.sha256((password + salt).encode('utf-8'))
            password_hash = hash_obj.hexdigest()
            form_data.pop('password')
            form_data['salt'] = salt
            form_data['password_hash'] = password_hash
        else:
            return rx.toast.error("Пароль не указан.")
        # --- конец блока проверки и хеширования ---

        form_data['worker'] = worker
        form_data['roles'] = self.selected_roles
        form_data['actions'] = self.selected_actions

        flag, text, id = UserDAO.add_one(form_data)
        if flag:
            return [rx.redirect(f"{routes.ADMIN_USERS_VIEW_ID}{id}"), rx.toast.success(text)]
        else:
            return [rx.toast.error(text)]
        
    @rx.event
    def edit_one(self, form_data: dict):
        worker = WorkerDAO.get_by_fio(form_data['worker'])
        if worker is None:
            return rx.toast.error("Не удалось изменить пользователя. Сотрудник не найден.")
        
        # --- Проверка и хеширование пароля при необходимости ---
        password = form_data.get('password')
        if password is not None and password != "":
            forbidden = set(' абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ')
            if any(ch in forbidden for ch in password):
                return rx.toast.error("Пароль содержит недопустимые символы.")
            salt = os.urandom(16).hex()
            hash_obj = hashlib.sha256((password + salt).encode('utf-8'))
            password_hash = hash_obj.hexdigest()
            form_data.pop('password')
            form_data['salt'] = salt
            form_data['password_hash'] = password_hash
        # --- конец блока проверки и хеширования ---

        form_data['worker'] = worker
        form_data['login'] = self.items[self.selected_item].login
        form_data['roles'] = [role.id for role in self.selected_roles]
        form_data['actions'] = [action.id for action in self.selected_actions]
        flag, text, id = UserDAO.edit_one(form_data)
        if flag:
            return [rx.redirect(f"{routes.ADMIN_USERS_VIEW_ID}{id}"), rx.toast.success(text)]
        else:
            return [rx.toast.error(text)]
        
    @rx.event
    def delete_one(self):
        if self.selected_item != -1:
            flag, text = UserDAO.delete_one(self.items[self.selected_item].login)
            if flag:
                return [rx.redirect(routes.ADMIN_USERS), rx.toast.success(text)]
            else:
                return [rx.toast.error(text)]
        else:
            return [rx.toast.error("Не выбрана запись для удаления")]