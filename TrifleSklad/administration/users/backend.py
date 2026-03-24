import hashlib
import os
from typing import Dict, List, Optional, Tuple

import reflex as rx

import TrifleSklad.routes as routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.administration.actions.backend import ActionsState
from TrifleSklad.administration.roles.backend import RoleSelectorState
from TrifleSklad.dao import UserDAO, WorkerDAO
from TrifleSklad.models import User
from TrifleSklad.state import AppState


def check_pass(password: str) -> bool:
    forbidden = set(
        " абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ"
    )
    return any(ch in forbidden for ch in password)


def gen_salt() -> str:
    return os.urandom(16).hex()


def gen_hash(password: str, salt: str) -> str:
    hash_obj = hashlib.sha256((password + salt).encode("utf-8"))
    return hash_obj.hexdigest()


class ViewUserState(rx.State):
    item: Optional[User] = None
    app_state: Optional[AppState] = None
    actions_state: Optional[ActionsState] = None
    roles_state: Optional[RoleSelectorState] = None

    # Frontend vars
    # =============
    @rx.var
    def has_roles(self) -> bool:
        return self.item is not None and len(self.item.roles) > 0

    @rx.var
    def has_actions(self) -> bool:
        return self.item is not None and len(self.item.actions) > 0
    # =============

    # Actions handlers
    # ================
    @rx.event
    async def on_load(self, id: str):
        self.app_state: AppState = await self.get_state(AppState)
        self.actions_state: ActionsState = await self.get_state(ActionsState)
        self.roles_state: RoleSelectorState = await self.get_state(RoleSelectorState)
        self.item = UserDAO.get_user_by_id_with_relationships(id)
        if self.item is None:
            return [
                rx.redirect(routes.ADMIN_USERS),
                rx.toast.error("Запис не знайдено!"),
            ]

        self.roles_state.on_load(self.item.roles)
        self.actions_state.on_load(self.item.actions)

    # ================


class AddUserState(rx.State):
    item: User = User()
    app_state: Optional[AppState] = None
    roles_state: Optional[RoleSelectorState] = None
    actions_state: Optional[ActionsState] = None
    list_workers: List[Tuple[str, str]] = []

    # Frontend vars
    # =============
    @rx.var
    def has_roles(self) -> bool:
        return len(self.item.roles) > 0

    @rx.var
    def has_actions(self) -> bool:
        return len(self.item.actions) > 0

    @rx.var
    def id_worker(self) -> str:
        return str(self.item.id_worker) if self.item.id_worker is not None else ""

    # =============

    # Action handlers
    # ===============
    @rx.event
    async def on_load(self):
        self.app_state: AppState = await self.get_state(AppState)
        self.roles_state: RoleSelectorState = await self.get_state(RoleSelectorState)
        self.actions_state: ActionsState = await self.get_state(ActionsState)
        self.list_workers: List[Tuple[str, str]] = [
            (item.fio, str(item.id)) for item in WorkerDAO.get_all()
        ]

        self.reset_item()
        self.roles_state.on_load(self.item.roles)
        self.actions_state.on_load(self.item.actions)

    @rx.event
    def reset_item(self):
        self.item = User()

    @rx.event
    def on_change_login(self, login: str):
        self.item.login = login if login != "" else None

    @rx.event
    def on_change_worker(self, worker: str):
        self.item.id_worker = int(worker) if int(worker) > 0 else None

    @rx.event
    def on_change_password(self, password: str):
        self.item.password_hash = password if password != "" else None

    @rx.event
    def on_change_roles(self):
        self.item.roles = self.roles_state._get_selected_items()

    @rx.event
    def on_change_actions(self):
        self.item.actions = self.actions_state._get_selected_items()

    @rx.event
    def on_open_roles(self):
        self.roles_state.on_load(self.item.roles)

    @rx.event
    def on_open_actions(self):
        self.actions_state.on_load(self.item.actions)

    @rx.event
    def add_one(self):
        if not self.app_state.has_permission(ActionEnum.USERS_CREATE):
            return rx.toast.error("У вас недостатньо прав для виконання цієї дії!")

        if (
            self.item.login is None
            or self.item.password_hash is None
            or self.item.id_worker is None
        ):
            return rx.toast.error("Заповнить всі обов'язкові поля!")

        if len(self.item.roles) == 0 and len(self.item.actions) == 0:
            return rx.toast.error(
                "Користувач має мати доступ хоча б до однієї дії або мати роль!"
            )

        if check_pass(self.item.password_hash):
            return rx.roast.error("Пароль містить недопустимі символи!")

        self.item.salt = gen_salt()
        self.item.password_hash = gen_hash(self.item.password_hash, self.item.salt)

        flag, text, id = UserDAO.add_one(self.item)
        if flag:
            return [
                rx.redirect(f"{routes.ADMIN_USERS_VIEW_ID}{id}"),
                rx.toast.success(text),
            ]
        else:
            return [rx.toast.error(text)]

    # ===============


class EditUserState(rx.State):
    item: Optional[User] = None
    app_state: Optional[AppState] = None
    roles_state: Optional[RoleSelectorState] = None
    actions_state: Optional[ActionsState] = None
    list_workers: List[Tuple[str, str]] = []
    password: str = ""

    # Frontend vars
    # =============
    @rx.var
    def has_roles(self) -> bool:
        return self.item is not None and len(self.item.roles) > 0

    @rx.var
    def has_actions(self) -> bool:
        return self.item is not None and len(self.item.actions) > 0

    @rx.var
    def id_worker(self) -> str:
        return str(self.item.id_worker) if self.item is not None else ""
    # =============

    # Action handlers
    # ===============
    @rx.event
    async def on_load(self, login: str):
        self.app_state: AppState = await self.get_state(AppState)
        self.roles_state: RoleSelectorState = await self.get_state(RoleSelectorState)
        self.actions_state: ActionsState = await self.get_state(ActionsState)
        self.list_workers: List[Tuple[str, str]] = [
            (item.fio, str(item.id)) for item in WorkerDAO.get_all()
        ]
        self.reset_item(login)
        if self.item is None:
            return [rx.redirect(routes.ADMIN_USERS), rx.toast.error("Користувача не знайдено!")]
        self.roles_state.on_load(self.item.roles)
        self.actions_state.on_load(self.item.actions)

    @rx.event
    def reset_item(self, login: str):
        self.item = UserDAO.get_user_by_id_with_relationships(login)

    @rx.event
    def on_change_worker(self, worker: str):
        self.item.id_worker = int(worker) if int(worker) > 0 else None

    @rx.event
    def on_change_password(self, password: str):
        self.password = password if password != "" else None

    @rx.event
    def on_change_roles(self):
        self.item.roles = self.roles_state._get_selected_items()

    @rx.event
    def on_change_actions(self):
        self.item.actions = self.actions_state._get_selected_items()

    @rx.event
    def on_open_roles(self):
        self.roles_state.on_load(self.item.roles)

    @rx.event
    def on_open_actions(self):
        self.actions_state.on_load(self.item.actions)

    @rx.event
    def edit_one(self):
        if not self.app_state.has_permission(ActionEnum.USERS_EDIT):
            return rx.toast.error("У вас недостатньо прав для виконання цієї дії!")

        if self.item.id_worker is None:
            return rx.toast.error("Заповнить всі обов'язкові поля!")

        if len(self.item.roles) == 0 and len(self.item.actions == 0):
            return rx.toast.error(
                "Користувач має мати доступ хоча б до однієї дії або мати роль!"
            )

        if self.password != "":
            if check_pass(self.password):
                return rx.roast.error("Пароль містить недопустимі символи!")

            self.item.salt = gen_salt()
            self.item.password_hash = gen_hash(self.item.password_has, self.item.salt)

        flag, text, id = UserDAO.edit_one(self.item)
        if flag:
            return [
                rx.redirect(f"{routes.ADMIN_USERS_VIEW_ID}{id}"),
                rx.toast.success(text),
            ]
        else:
            return [rx.toast.error(text)]
    # ===============


class ListUserState(rx.State):
    items: List[User] = []
    app_state: Optional[AppState] = None

    # Frontend vars
    # =============
    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    # =============

    # Action handlers
    # ===============
    @rx.event
    async def on_load(self):
        self.items: List[User] = UserDAO.get_all_with_relationships()
        self.app_state: AppState = await self.get_state(AppState)


class UserState(rx.State):
    class Pages:
        ADD = "add"
        EDIT = "edit"
        VIEW = "view"
        LIST = "list"

    current_page: str = Pages.LIST
    app_state: Optional[AppState] = None

    def _check_path(self):
        if not (
            self.app_state.has_permission(ActionEnum.USERS_CREATE)
            or self.app_state.has_permission(ActionEnum.USERS_EDIT)
            or self.app_state.has_permission(ActionEnum.USERS_VIEW)
            or self.app_state.has_permission(ActionEnum.USERS_LIST)
        ):
            return rx.redirect(routes.WELCOME)

        page = self.router.page.params.get("page", "")
        if page != "":
            id = -1
            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                return rx.redirect(routes.ADMIN_USERS)

            # /users/add
            if page == self.Pages.ADD:
                yield AddUserState.on_load()
            # /users/edit/[id]
            elif page == self.Pages.EDIT:
                id = self.router.page.params.get("id", "")
                if id != "" or UserDAO.get_user_by_id(id) is not None:
                    yield EditUserState.on_load(id)
                else:
                    return rx.redirect(routes.ADMIN_USERS)
            # /users/view/[id]
            elif page == self.Pages.VIEW:
                id = self.router.page.params.get("id", "")
                if id != "" or UserDAO.get_user_by_id(id) is not None:
                    yield ViewUserState.on_load(id)
                else:
                    return rx.redirect(routes.ADMIN_USERS)

            self.current_page = page
        else:
            # /users
            yield ListUserState.on_load()
            self.current_page = self.Pages.LIST

    @rx.event
    async def on_load(self):
        self.current_page: str = self.Pages.LIST
        self.app_state: AppState = await self.get_state(AppState)
        return self._check_path()

    @rx.event
    def delete_one(self, login: str):
        if login is not None or len(login) > 0:
            flag, text = UserDAO.delete_one(login)
            if flag:
                return [rx.redirect(routes.ADMIN_USERS), rx.toast.success(text)]
            else:
                return [rx.toast.error(text)]
        else:
            return [rx.toast.error("Не обрано запис для видалення.")]
