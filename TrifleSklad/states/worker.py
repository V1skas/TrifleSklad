from typing import Optional, Sequence

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.models import Worker
from TrifleSklad.services.errors import ServiceError
from TrifleSklad.services.worker import WorkerService
from TrifleSklad.states.app import AppState
from TrifleSklad.states.audit_mixin import AuditHistoryMixin


class ListWorkersState(AppState):
    items: Optional[Sequence[Worker]] = None
    in_progress: bool = True

    @rx.var
    def has_items(self) -> bool:
        return self.items is not None and len(self.items) > 0

    @rx.event
    def on_load(self):
        if not self.has_permission(Action.WORKERS_LIST):
            yield rx.redirect(routes.WELCOME)
            yield rx.toast.error("У Вас немає дозволу на перегляд цієї сторінки!")
            return
        try:
            self.in_progress = True
            self.items = WorkerService().get_list_items()
            self.in_progress = False
        except Exception:
            yield rx.toast.error("Під час виконання запиту сталася помилка. Спробуйте знову.")

    @rx.event
    def on_click_add(self):
        return rx.redirect(routes.ADMIN_WORKERS_ADD)


class AddWorkerState(AppState):
    item: Worker = Worker()
    in_process: bool = False

    @rx.event
    def on_load(self):
        if not self.has_permission(Action.WORKERS_CREATE):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        self.item = Worker()

    @rx.var
    def worker_fio(self) -> str:
        return self.item.fio if self.item is not None and self.item.fio is not None else ""

    @rx.var
    def position(self) -> str:
        return self.item.position if self.item is not None and self.item.position is not None else ""

    @rx.var
    def phone_number(self) -> str:
        return self.item.phone_number if self.item is not None and self.item.phone_number is not None else ""

    @rx.var
    def email(self) -> str:
        return self.item.email if self.item is not None and self.item.email is not None else ""

    @rx.var
    def is_default(self) -> bool:
        return bool(self.item.is_default) if self.item is not None else False

    @rx.event
    def set_worker_fio(self, value: str):
        self.item.fio = value

    @rx.event
    def set_position(self, value: str):
        self.item.position = value if value != "" else None

    @rx.event
    def set_phone_number(self, value: str):
        self.item.phone_number = value if value != "" else None

    @rx.event
    def set_email(self, value: str):
        self.item.email = value if value != "" else None

    @rx.event
    def set_is_default(self, value: bool):
        self.item.is_default = value

    @rx.event
    def on_save(self):
        if not self.has_permission(Action.WORKERS_CREATE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if not self.item.fio:
            yield rx.toast.warning("Вкажіть ПІБ співробітника!")
            return
        if self.item.position is None:
            yield rx.toast.warning("Вкажіть посаду співробітника!")
            return
        try:
            self.item = WorkerService().add_one(self.item, self.user.login)
            yield rx.toast.success("Співробітника додано!")
            yield rx.redirect(routes.ADMIN_WORKERS_VIEW_ID + str(self.item.id), replace=True)
        except ServiceError as e:
            yield rx.toast.warning(str(e))
        except Exception:
            yield rx.toast.error("Під час виконання запиту трапилась помилка. Спробуйте ще раз.")


class EditWorkerState(AppState):
    item: Worker = Worker()
    in_process: bool = False

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(Action.WORKERS_EDIT):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        try:
            self.in_process = True
            item = WorkerService().get_by_id(int(id))
            if item is None:
                self.in_process = False
                yield rx.redirect(routes.ADMIN_WORKERS)
                yield rx.toast.error("Запис не було знайдено")
                return
            self.item = item
            self.in_process = False
        except Exception:
            self.in_process = False
            yield rx.toast.error("Під час виконання запиту сталася помилка. Спробуйте знову.")

    @rx.var
    def worker_fio(self) -> str:
        return self.item.fio if self.item is not None and self.item.fio is not None else ""

    @rx.var
    def position(self) -> str:
        return self.item.position if self.item is not None and self.item.position is not None else ""

    @rx.var
    def phone_number(self) -> str:
        return self.item.phone_number if self.item is not None and self.item.phone_number is not None else ""

    @rx.var
    def email(self) -> str:
        return self.item.email if self.item is not None and self.item.email is not None else ""

    @rx.var
    def is_default(self) -> bool:
        return bool(self.item.is_default) if self.item is not None else False

    @rx.event
    def set_worker_fio(self, value: str):
        self.item.fio = value

    @rx.event
    def set_position(self, value: str):
        self.item.position = value if value != "" else None

    @rx.event
    def set_phone_number(self, value: str):
        self.item.phone_number = value if value != "" else None

    @rx.event
    def set_email(self, value: str):
        self.item.email = value if value != "" else None

    @rx.event
    def set_is_default(self, value: bool):
        self.item.is_default = value

    @rx.event
    def on_save(self):
        if not self.has_permission(Action.WORKERS_EDIT):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if not self.item.fio:
            yield rx.toast.warning("Вкажіть ПІБ співробітника!")
            return
        if self.item.position is None:
            yield rx.toast.warning("Вкажіть посаду співробітника!")
            return
        try:
            self.item = WorkerService().edit_one(self.item, self.user.login)
            yield rx.toast.success("Інформацію про співробітника змінено!")
            yield rx.redirect(routes.ADMIN_WORKERS_VIEW_ID + str(self.item.id), replace=True)
        except ServiceError as e:
            yield rx.toast.warning(str(e))
        except Exception:
            yield rx.toast.error("Під час виконання запиту трапилась помилка. Спробуйте ще раз.")


class ViewWorkerState(AuditHistoryMixin, AppState):
    HISTORY_TABLE = "workers"
    HISTORY_ACTION = Action.WORKERS_HISTORY
    HISTORY_DETAIL_ACTION = Action.WORKERS_HISTORY_DETAIL

    item: Optional[Worker] = None
    in_process: bool = True

    @rx.var
    def worker_fio(self) -> str:
        return self.item.fio if self.item is not None and self.item.fio is not None else ""

    @rx.var
    def position(self) -> str:
        return self.item.position if self.item is not None and self.item.position is not None else ""

    @rx.var
    def phone_number(self) -> str:
        return self.item.phone_number if self.item is not None and self.item.phone_number is not None else ""

    @rx.var
    def email(self) -> str:
        return self.item.email if self.item is not None and self.item.email is not None else ""

    @rx.var
    def is_default(self) -> bool:
        return bool(self.item.is_default) if self.item is not None else False

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(Action.WORKERS_VIEW):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        try:
            self.in_process = True
            self.item = WorkerService().get_by_id(int(id))
            self.in_process = False
            if self.item is None:
                yield rx.redirect(routes.ADMIN_WORKERS)
                yield rx.toast.error("Запис не було знайдено")
                return
            self._load_history(self.item.id)
        except Exception:
            self.in_process = False
            yield rx.toast.error("Під час виконання запиту сталася помилка. Спробуйте знову.")

    @rx.event
    def on_click_edit(self):
        if self.item is None:
            return
        return rx.redirect(routes.ADMIN_WORKERS_EDIT_ID + str(self.item.id))

    @rx.event
    def on_click_delete(self):
        if not self.has_permission(Action.WORKERS_DELETE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None:
            return
        if WorkerService().delete_one(self.item.id, self.user.login):
            yield rx.toast.success("Співробітника видалено!")
            yield ListWorkersState.on_load()
            yield rx.redirect(routes.ADMIN_WORKERS)
        else:
            yield rx.toast.error("Помилка! Співробітника не знайдено.")
