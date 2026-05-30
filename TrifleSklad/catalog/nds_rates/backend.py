import reflex as rx

from typing import List, Optional

import TrifleSklad.routes as routes
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum

from TrifleSklad.models import NDSRate
from TrifleSklad.dao import NDSRateDAO


class ViewNdsRateState(rx.State):
    item: Optional[NDSRate] = None
    app_state: Optional[AppState] = None

    # Vars
    # ====
    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""

    @rx.var
    def rate(self) -> str:
        return str(self.item.rate) if self.item is not None and self.item.rate is not None else "0"

    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""
    # ====

    # Action handlers
    # ===============
    @rx.event
    async def on_load(self, id: int):
        self.item = NDSRateDAO.get_by_id(id)
        if self.item is None:
            return [
                rx.redirect(routes.CATALOG_NDS_RATES),
                rx.toast.error("Запис не знайдено!")
            ]
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
    # ===============


class AddNdsRateState(rx.State):
    item: Optional[NDSRate] = None
    app_state: Optional[AppState] = None

    def _reset_item(self):
        self.item: NDSRate = NDSRate()

    # Vars
    # ====
    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""

    @rx.var
    def rate(self) -> str:
        return str(self.item.rate) if self.item is not None and self.item.rate is not None else ""

    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""
    # ====

    # Action handlers
    # ===============
    @rx.event
    async def on_load(self):
        self._reset_item()
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)

    @rx.event
    def on_change_title(self, title: str):
        self.item.title = title if title != "" else None

    @rx.event
    def on_change_rate(self, rate: str):
        if rate == "":
            self.item.rate = 0.0
            return
        try:
            value = float(rate.replace(",", "."))
            self.item.rate = value if value >= 0 else 0.0
        except ValueError:
            pass

    @rx.event
    def on_change_description(self, description: str):
        self.item.description = description if description != "" else None

    @rx.event
    def add_one(self):
        if not self.app_state.has_permission(ActionEnum.NDS_RATES_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")

        if self.item.title is None:
            return rx.toast.error("Усі обов'язкові поля мають бути заповнені!")

        flag, text, id = NDSRateDAO.add_one(self.item)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_NDS_RATES_VIEW_ID}{id}")]
        return rx.toast.error(text)
    # ===============


class EditNdsRateState(rx.State):
    item: Optional[NDSRate] = None
    app_state: Optional[AppState] = None

    def _load_item(self, id: int):
        self.item = NDSRateDAO.get_by_id(id)

    # Vars
    # ====
    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""

    @rx.var
    def rate(self) -> str:
        return str(self.item.rate) if self.item is not None and self.item.rate is not None else ""

    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""
    # ====

    # Action handlers
    # ===============
    @rx.event
    async def on_load(self, id: int):
        self._load_item(id)
        if self.item is None:
            return [
                rx.redirect(routes.CATALOG_NDS_RATES),
                rx.toast.error("Запис не знайдено!")
            ]
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)

    @rx.event
    def on_change_title(self, title: str):
        self.item.title = title if title != "" else None

    @rx.event
    def on_change_rate(self, rate: str):
        if rate == "":
            self.item.rate = 0.0
            return
        try:
            value = float(rate.replace(",", "."))
            self.item.rate = value if value >= 0 else 0.0
        except ValueError:
            pass

    @rx.event
    def on_change_description(self, description: str):
        self.item.description = description if description != "" else None

    @rx.event
    def edit_one(self):
        if not self.app_state.has_permission(ActionEnum.NDS_RATES_EDIT):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")

        if self.item.title is None:
            return rx.toast.error("Усі обов'язкові поля мають бути заповнені!")

        flag, text, id = NDSRateDAO.edit_one(self.item)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_NDS_RATES_VIEW_ID}{id}")]
        return rx.toast.error(text)
    # ===============


class ListNdsRateState(rx.State):
    items: List[NDSRate] = []

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.event
    def on_load(self):
        self.items = NDSRateDAO.get_all()


class NdsRateState(rx.State):
    class Pages:
        ADD = "add"
        EDIT = "edit"
        VIEW = "view"
        LIST = "list"

    current_page: str = Pages.LIST
    app_state: Optional[AppState] = None

    def _check_path(self):
        page = self.router.page.params.get('page', '')
        if page != '':
            id = -1

            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                yield rx.redirect(routes.CATALOG_NDS_RATES)
                return

            if page == self.Pages.ADD:
                if not self.app_state.has_permission(ActionEnum.NDS_RATES_CREATE):
                    yield rx.redirect(routes.WELCOME)
                    return
                yield AddNdsRateState.on_load()
            elif page == self.Pages.EDIT:
                if not self.app_state.has_permission(ActionEnum.NDS_RATES_EDIT):
                    yield rx.redirect(routes.WELCOME)
                    return

                id = self.router.page.params.get('id', '')
                if id != '':
                    yield EditNdsRateState.on_load(id)
                else:
                    yield rx.redirect(routes.CATALOG_NDS_RATES)
                    return
            elif page == self.Pages.VIEW:
                if not self.app_state.has_permission(ActionEnum.NDS_RATES_VIEW):
                    yield rx.redirect(routes.WELCOME)
                    return

                id = self.router.page.params.get('id', '')
                if id != '':
                    yield ViewNdsRateState.on_load(id)
                else:
                    yield rx.redirect(routes.CATALOG_NDS_RATES)
                    return

            self.current_page = page
        else:
            if not self.app_state.has_permission(ActionEnum.NDS_RATES_LIST):
                yield rx.redirect(routes.WELCOME)
                return
            yield ListNdsRateState.on_load()
            self.current_page = self.Pages.LIST

    @rx.event
    async def on_load(self):
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
        return self._check_path()

    @rx.event
    def delete_one(self, id: int):
        if not self.app_state.has_permission(ActionEnum.NDS_RATES_DELETE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")

        if id > -1:
            flag, text = NDSRateDAO.delete_one(id)
            if flag:
                return [rx.toast.success(text), rx.redirect(routes.CATALOG_NDS_RATES)]
            else:
                return [rx.toast.error(text)]
        return rx.toast.error("Не обрано запис для видалення!")
