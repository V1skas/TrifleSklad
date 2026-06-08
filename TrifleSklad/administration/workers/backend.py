import reflex as rx
from typing import List, Tuple

from reflex import app

import TrifleSklad.routes as routes
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action

from TrifleSklad.models import Worker
from TrifleSklad.dao import WorkerDAO


class ListWorkersState(rx.State):
    items: List[Worker] = []

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0
    
    @rx.var
    def get_items(self) -> List[Tuple[int, Worker]]:
        return [(index, item) for index, item in enumerate(self.items)]
    
    # Actions handlers
    # ======================
    @rx.event
    def refresh_list(self):
        self.items = WorkerDAO.get_all()
    # ======================


class ViewWorkerState(rx.State):
    item: Worker = Worker(
        id=-1,
        fio="",
        phone_number="",
        email="",
        position=""
    )

    # Actions handlers
    # ======================
    @rx.event
    def load_item(self, id: int):
        item = WorkerDAO.get_by_id(id)
        if item is not None:
            self.item = item
        else:
            return [rx.redirect(routes.ADMIN_WORKERS, replace=True), rx.toast.error("Запис не було знайдено")]
    # ======================


class AddWorkerState(rx.State):
    item: Worker = Worker(
    )

    # Actions handlers
    # ======================
    @rx.event
    def reset_item(self):
        self.item = Worker()

    @rx.event
    def change_fio(self, value: str):
        self.item.fio = value

    @rx.event
    def change_position(self, value: str):
        self.item.position = value if value != "" else None

    @rx.event
    def change_phone_number(self, value: str):
        self.item.phone_number = value if value != "" else None

    @rx.event
    def change_email(self, value: str):
        self.item.email = value if value != "" else None

    @rx.event
    async def add_one(self):
        app_state: AppState = await self.get_state(AppState)
        if not app_state.has_permission(Action.WORKERS_CREATE):
            yield rx.redirect(routes.WELCOME, replace=True)
            return

        if self.item.fio == "" or self.item.position is None:
            yield rx.toast.error("Будь ласка, заповніть всі обов'язкові поля")
            return
        flag, text, id = WorkerDAO.add_one(self.item.dict())
        if flag:
            yield [rx.redirect(f"{routes.ADMIN_WORKERS_VIEW_ID}{id}"), rx.toast.success(text)]
            return
        yield rx.toast.error(text)
        return
    # ======================


class EditWorkerState(rx.State):
    item: Worker = Worker()

    # Actions handlers
    # ======================
    @rx.event
    def load_item(self, id: int):
        item = WorkerDAO.get_by_id(id)
        if item is not None:
            self.item = item
        else:
            return [rx.redirect(routes.ADMIN_WORKERS, replace=True), rx.toast.error("Запис не було знайдено")]

    @rx.event
    def change_fio(self, value: str):
        self.item.fio = value

    @rx.event
    def change_position(self, value: str):
        self.item.position = value if value != "" else None

    @rx.event
    def change_phone_number(self, value: str):
        self.item.phone_number = value if value != "" else None

    @rx.event
    def change_email(self, value: str):
        self.item.email = value if value != "" else None

    @rx.event
    async def edit_one(self):
        app_state: AppState = await self.get_state(AppState)
        if not app_state.has_permission(Action.WORKERS_EDIT):
            yield rx.redirect(routes.WELCOME, replace=True)
            return

        if self.item.fio == "" or self.item.position is None:
            yield rx.toast.error("Будь ласка, заповніть всі обов'язкові поля")
            return
        flag, text, id = WorkerDAO.edit_one(self.item.dict())
        if flag:
            yield [rx.redirect(f"{routes.ADMIN_WORKERS_VIEW_ID}{id}"), rx.toast.success(text)]
            return
        yield rx.toast.error(text)
        return
    # ======================


class WorkersState(rx.State):
    class Pages:
        ADD = 'add'
        EDIT = 'edit'
        VIEW = 'view'
        LIST = 'list'

    current_page: str = Pages.LIST

    async def _check_path(self):
        page = self.router.page.params.get("page", "")
        app_state: AppState = await self.get_state(AppState)

        if page != "":
            id = -1
            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                yield rx.redirect(routes.ADMIN_WORKERS)
                return

            # /workers/add
            if page == self.Pages.ADD:
                if not app_state.has_permission(Action.WORKERS_CREATE):
                    yield rx.redirect(routes.WELCOME)
                    return
                
                yield AddWorkerState.reset_item()
            # /workers/edit/[id]
            elif page == self.Pages.EDIT:
                if not app_state.has_permission(Action.WORKERS_EDIT):
                    yield rx.redirect(routes.WELCOME)
                    return
                id = self.router.page.params.get("id", "")
                if id != "":
                    yield EditWorkerState.load_item(id)
                else:
                    yield rx.redirect(routes.ADMIN_WORKERS)
                    return
                
            # /workers/view/[id]
            elif page == self.Pages.VIEW:
                if not app_state.has_permission(Action.WORKERS_VIEW):
                    yield rx.redirect(routes.WELCOME)
                    return
                
                id = self.router.page.params.get("id", "")
                if id != "":
                    yield ViewWorkerState.load_item(id)
                else:
                    yield rx.redirect(routes.ADMIN_WORKERS)
                    return
            self.current_page = page
        else:
            # /workers
            if not app_state.has_permission(Action.WORKERS_LIST):
                yield rx.redirect(routes.WELCOME)
                return
            yield ListWorkersState.refresh_list()
            self.current_page = self.Pages.LIST
            return
    
    @rx.event
    async def on_load(self):
        return self._check_path()
    
    @rx.event
    async def delete_one(self, id: int):
        app_state: AppState = await self.get_state(AppState)
        if not app_state.has_permission(Action.WORKERS_DELETE):
            yield rx.redirect(routes.WELCOME)
            return
        
        flag, text = WorkerDAO.delete_one(id)
        if flag:
            yield [rx.redirect(routes.ADMIN_WORKERS), rx.toast.success(text)]
            return
        yield rx.toast.error(text)
        return