from typing import Optional, Sequence

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.models import Role
from TrifleSklad.services.errors import ServiceError
from TrifleSklad.services.role import RoleService
from TrifleSklad.states.actions_picker import ActionsPickerState
from TrifleSklad.states.app import AppState
from TrifleSklad.states.audit_mixin import AuditHistoryMixin


class ListRoleState(AppState):
    items: Optional[Sequence[Role]] = None
    in_progress: bool = True

    @rx.var
    def has_items(self) -> bool:
        return self.items is not None and len(self.items) > 0

    @rx.event
    def on_load(self):
        if not self.has_permission(ActionEnum.ROLES_LIST):
            yield rx.redirect(routes.WELCOME)
            yield rx.toast.error("У Вас немає дозволу на перегляд цієї сторінки!")
            return
        try:
            self.in_progress = True
            self.items = RoleService().get_list_items()
            self.in_progress = False
        except Exception:
            yield rx.toast.error("Під час виконання запиту сталася помилка. Спробуйте знову.")

    @rx.event
    def on_click_add(self):
        return rx.redirect(routes.ADMIN_ROLES_ADD)


class AddRoleState(AppState):
    item: Role = Role(title="", description="")
    in_process: bool = False

    @rx.var
    def has_selected_actions(self) -> bool:
        return len(self.item.actions) > 0

    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""

    @rx.event
    def on_load(self):
        if not self.has_permission(ActionEnum.ROLES_CREATE):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        self.item = Role(title="", description="", actions=[])
        # list(...) — інакше в yield-подію потрапляє «жива» SQLAlchemy
        # InstrumentedList; Reflex робить deepcopy аргументів події при
        # ланцюжку подій, а deepcopy інструментованої колекції ламається на
        # weakref власника (AttributeError: InstanceState має 'obj').
        yield ActionsPickerState.on_load(list(self.item.actions))

    @rx.event
    def set_title(self, value: str):
        self.item.title = value

    @rx.event
    def set_description(self, value: str):
        self.item.description = value if value != "" else None

    @rx.event
    async def apply_actions(self):
        picker = await self.get_state(ActionsPickerState)
        self.item.actions = picker._get_selected_items()

    @rx.event
    async def open_actions(self):
        picker = await self.get_state(ActionsPickerState)
        picker.on_load(self.item.actions)

    @rx.event
    def on_save(self):
        if not self.has_permission(ActionEnum.ROLES_CREATE):
            yield rx.toast.error("У вас недостатньо прав для виконання цієї дії!")
            return
        if self.item.title == "":
            yield rx.toast.warning("Вкажіть назву ролі!")
            return
        if len(self.item.actions) == 0:
            yield rx.toast.warning("Оберіть хоча б одне право для ролі!")
            return
        try:
            self.item = RoleService().add_one(self.item, self.user.login)
            yield rx.toast.success("Роль успішно додана!")
            yield rx.redirect(routes.ADMIN_ROLES_VIEW_ID + str(self.item.id))
        except ServiceError as e:
            yield rx.toast.warning(str(e))
        except Exception:
            yield rx.toast.error("Під час виконання запиту трапилась помилка. Спробуйте ще раз.")


class EditRoleState(AppState):
    item: Role = Role(title="", description="")
    in_process: bool = False

    @rx.var
    def has_selected_actions(self) -> bool:
        return len(self.item.actions) > 0

    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(ActionEnum.ROLES_EDIT):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        try:
            self.in_process = True
            item = RoleService().get_by_id(int(id))
            if item is None:
                self.in_process = False
                yield rx.redirect(routes.ADMIN_ROLES)
                yield rx.toast.error("Запис не було знайдено")
                return
            self.item = item
            self.in_process = False
            yield ActionsPickerState.on_load(list(self.item.actions))
        except Exception:
            self.in_process = False
            yield rx.toast.error("Під час виконання запиту сталася помилка. Спробуйте знову.")

    @rx.event
    def set_title(self, value: str):
        self.item.title = value

    @rx.event
    def set_description(self, value: str):
        self.item.description = value if value != "" else None

    @rx.event
    async def apply_actions(self):
        picker = await self.get_state(ActionsPickerState)
        self.item.actions = picker._get_selected_items()

    @rx.event
    async def open_actions(self):
        picker = await self.get_state(ActionsPickerState)
        picker.on_load(self.item.actions)

    @rx.event
    def on_save(self):
        if not self.has_permission(ActionEnum.ROLES_EDIT):
            yield rx.toast.error("У вас недостатньо прав для виконання цієї дії!")
            return
        if self.item.title == "":
            yield rx.toast.warning("Вкажіть назву ролі!")
            return
        if len(self.item.actions) == 0:
            yield rx.toast.warning("Оберіть хоча б одне право для ролі!")
            return
        try:
            self.item = RoleService().edit_one(self.item, self.user.login)
            yield rx.toast.success("Роль успішно змінена!")
            yield rx.redirect(routes.ADMIN_ROLES_VIEW_ID + str(self.item.id))
        except ServiceError as e:
            yield rx.toast.warning(str(e))
        except Exception:
            yield rx.toast.error("Під час виконання запиту трапилась помилка. Спробуйте ще раз.")


class ViewRoleState(AuditHistoryMixin, AppState):
    HISTORY_TABLE = "roles"
    HISTORY_ACTION = ActionEnum.ROLES_HISTORY
    HISTORY_DETAIL_ACTION = ActionEnum.ROLES_HISTORY_DETAIL

    item: Role = Role(title="", description="")
    in_process: bool = True

    @rx.var
    def has_actions(self) -> bool:
        return len(self.item.actions) > 0

    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(ActionEnum.ROLES_VIEW):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        try:
            self.in_process = True
            item = RoleService().get_by_id(int(id))
            self.in_process = False
            if item is None:
                yield rx.redirect(routes.ADMIN_ROLES)
                yield rx.toast.error("Запис не було знайдено")
                return
            self.item = item
            self._load_history(self.item.id)
        except Exception:
            self.in_process = False
            yield rx.toast.error("Під час виконання запиту сталася помилка. Спробуйте знову.")

    @rx.event
    def on_click_edit(self):
        return rx.redirect(routes.ADMIN_ROLES_EDIT_ID + str(self.item.id))

    @rx.event
    def on_click_delete(self):
        if not self.has_permission(ActionEnum.ROLES_DELETE):
            yield rx.toast.error("У вас недостатньо прав для виконання цієї дії!")
            return
        if RoleService().delete_one(self.item.id, self.user.login):
            yield rx.toast.success("Роль видалено.")
            yield ListRoleState.on_load()
            yield rx.redirect(routes.ADMIN_ROLES)
        else:
            yield rx.toast.error("Помилка! Роль для видалення не знайдена.")
