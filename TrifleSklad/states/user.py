from typing import List, Optional, Sequence, Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.dao_legacy import WorkerDAO
from TrifleSklad.models import User
from TrifleSklad.services.errors import ServiceError
from TrifleSklad.services.user import UserService
from TrifleSklad.states.actions_picker import ActionsPickerState
from TrifleSklad.states.app import AppState
from TrifleSklad.states.audit_mixin import AuditHistoryMixin
from TrifleSklad.states.role_selector import RoleSelectorState


class ListUserState(AppState):
    items: Optional[Sequence[User]] = None
    in_progress: bool = True

    @rx.var
    def has_items(self) -> bool:
        return self.items is not None and len(self.items) > 0

    @rx.event
    def on_load(self):
        if not self.has_permission(ActionEnum.USERS_LIST):
            yield rx.redirect(routes.WELCOME)
            yield rx.toast.error("У Вас немає дозволу на перегляд цієї сторінки!")
            return
        try:
            self.in_progress = True
            self.items = UserService().get_list_items()
            self.in_progress = False
        except Exception:
            yield rx.toast.error("Під час виконання запиту сталася помилка. Спробуйте знову.")

    @rx.event
    def on_click_add(self):
        return rx.redirect(routes.ADMIN_USERS_ADD)


class AddUserState(AppState):
    item: User = User()
    in_process: bool = False
    password: str = ""
    list_workers: List[Tuple[str, str]] = []

    @rx.var
    def has_roles(self) -> bool:
        return len(self.item.roles) > 0

    @rx.var
    def has_actions(self) -> bool:
        return len(self.item.actions) > 0

    @rx.var
    def login(self) -> str:
        return self.item.login if self.item is not None and self.item.login is not None else ""

    @rx.var
    def id_worker(self) -> str:
        return str(self.item.id_worker) if self.item is not None and self.item.id_worker is not None else ""

    @rx.event
    def on_load(self):
        if not self.has_permission(ActionEnum.USERS_CREATE):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        self.item = User(roles=[], actions=[])
        self.password = ""
        self.list_workers = [(w.fio, str(w.id)) for w in WorkerDAO.get_all()]
        # list(...) — інакше в yield-подію потрапляє «жива» SQLAlchemy
        # InstrumentedList; Reflex робить deepcopy аргументів події при
        # ланцюжку подій, а deepcopy інструментованої колекції ламається на
        # weakref власника (AttributeError: InstanceState має 'obj').
        yield RoleSelectorState.on_load(list(self.item.roles))
        yield ActionsPickerState.on_load(list(self.item.actions))

    @rx.event
    def set_login(self, value: str):
        self.item.login = value if value != "" else None

    @rx.event
    def set_id_worker(self, value: str):
        self.item.id_worker = int(value) if value.isdigit() and int(value) > 0 else None

    @rx.event
    def set_password(self, value: str):
        self.password = value

    @rx.event
    async def apply_roles(self):
        picker = await self.get_state(RoleSelectorState)
        self.item.roles = picker._get_selected_items()

    @rx.event
    async def apply_actions(self):
        picker = await self.get_state(ActionsPickerState)
        self.item.actions = picker._get_selected_items()

    @rx.event
    async def open_roles(self):
        picker = await self.get_state(RoleSelectorState)
        picker.on_load(self.item.roles)

    @rx.event
    async def open_actions(self):
        picker = await self.get_state(ActionsPickerState)
        picker.on_load(self.item.actions)

    @rx.event
    def on_save(self):
        if not self.has_permission(ActionEnum.USERS_CREATE):
            yield rx.toast.error("У вас недостатньо прав для виконання цієї дії!")
            return
        if self.item.login is None:
            yield rx.toast.warning("Вкажіть логін!")
            return
        if self.password == "":
            yield rx.toast.warning("Вкажіть пароль!")
            return
        if self.item.id_worker is None:
            yield rx.toast.warning("Оберіть співробітника!")
            return
        if len(self.item.roles) == 0 and len(self.item.actions) == 0:
            yield rx.toast.warning("Користувач має мати доступ хоча б до однієї дії або мати роль!")
            return
        try:
            self.item = UserService().add_one(self.item, self.user.login, self.password)
            yield rx.toast.success("Користувача додано!")
            yield rx.redirect(routes.ADMIN_USERS_VIEW_ID + str(self.item.login))
        except ServiceError as e:
            yield rx.toast.warning(str(e))
        except Exception:
            yield rx.toast.error("Під час виконання запиту трапилась помилка. Спробуйте ще раз.")


class EditUserState(AppState):
    item: User = User()
    in_process: bool = False
    password: str = ""
    list_workers: List[Tuple[str, str]] = []

    @rx.var
    def has_roles(self) -> bool:
        return self.item is not None and len(self.item.roles) > 0

    @rx.var
    def has_actions(self) -> bool:
        return self.item is not None and len(self.item.actions) > 0

    @rx.var
    def id_worker(self) -> str:
        return str(self.item.id_worker) if self.item is not None and self.item.id_worker is not None else ""

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(ActionEnum.USERS_EDIT):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        try:
            self.in_process = True
            item = UserService().get_by_login(id)
            if item is None:
                self.in_process = False
                yield rx.redirect(routes.ADMIN_USERS)
                yield rx.toast.error("Користувача не знайдено!")
                return
            self.item = item
            self.password = ""
            self.list_workers = [(w.fio, str(w.id)) for w in WorkerDAO.get_all()]
            self.in_process = False
            yield RoleSelectorState.on_load(list(self.item.roles))
            yield ActionsPickerState.on_load(list(self.item.actions))
        except Exception:
            self.in_process = False
            yield rx.toast.error("Під час виконання запиту сталася помилка. Спробуйте знову.")

    @rx.event
    def set_id_worker(self, value: str):
        self.item.id_worker = int(value) if value.isdigit() and int(value) > 0 else None

    @rx.event
    def set_password(self, value: str):
        self.password = value

    @rx.event
    async def apply_roles(self):
        picker = await self.get_state(RoleSelectorState)
        self.item.roles = picker._get_selected_items()

    @rx.event
    async def apply_actions(self):
        picker = await self.get_state(ActionsPickerState)
        self.item.actions = picker._get_selected_items()

    @rx.event
    async def open_roles(self):
        picker = await self.get_state(RoleSelectorState)
        picker.on_load(self.item.roles)

    @rx.event
    async def open_actions(self):
        picker = await self.get_state(ActionsPickerState)
        picker.on_load(self.item.actions)

    @rx.event
    def on_save(self):
        if not self.has_permission(ActionEnum.USERS_EDIT):
            yield rx.toast.error("У вас недостатньо прав для виконання цієї дії!")
            return
        if self.item.id_worker is None:
            yield rx.toast.warning("Оберіть співробітника!")
            return
        if len(self.item.roles) == 0 and len(self.item.actions) == 0:
            yield rx.toast.warning("Користувач має мати доступ хоча б до однієї дії або мати роль!")
            return
        try:
            self.item = UserService().edit_one(self.item, self.user.login, self.password)
            yield rx.toast.success("Інформацію про користувача змінено!")
            yield rx.redirect(routes.ADMIN_USERS_VIEW_ID + str(self.item.login))
        except ServiceError as e:
            yield rx.toast.warning(str(e))
        except Exception:
            yield rx.toast.error("Під час виконання запиту трапилась помилка. Спробуйте ще раз.")


class ViewUserState(AuditHistoryMixin, AppState):
    HISTORY_TABLE = "users"
    HISTORY_ACTION = ActionEnum.USERS_HISTORY
    HISTORY_DETAIL_ACTION = ActionEnum.USERS_HISTORY_DETAIL

    item: Optional[User] = None
    in_process: bool = True

    @rx.var
    def has_roles(self) -> bool:
        return self.item is not None and len(self.item.roles) > 0

    @rx.var
    def has_actions(self) -> bool:
        return self.item is not None and len(self.item.actions) > 0

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(ActionEnum.USERS_VIEW):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        try:
            self.in_process = True
            self.item = UserService().get_by_login(id)
            self.in_process = False
            if self.item is None:
                yield rx.redirect(routes.ADMIN_USERS)
                yield rx.toast.error("Запис не знайдено!")
                return
            self._load_history(self.item.login)
        except Exception:
            self.in_process = False
            yield rx.toast.error("Під час виконання запиту сталася помилка. Спробуйте знову.")

    @rx.event
    def on_click_edit(self):
        if self.item is None:
            return
        return rx.redirect(routes.ADMIN_USERS_EDIT_ID + str(self.item.login))

    @rx.event
    def on_click_delete(self):
        if not self.has_permission(ActionEnum.USERS_DELETE):
            yield rx.toast.error("У вас недостатньо прав для виконання цієї дії!")
            return
        if self.item is None:
            return
        if UserService().delete_one(self.item.login, self.user.login):
            yield rx.toast.success("Користувача видалено!")
            yield ListUserState.on_load()
            yield rx.redirect(routes.ADMIN_USERS)
        else:
            yield rx.toast.error("Не обрано запис для видалення.")
