from typing import List, Tuple

import reflex as rx

from TrifleSklad.declared import movements_status_list


class MovementListFilterMixin(rx.State, mixin=True):
    """Спільна логіка списків руху ТМЦ: сторінкування + фільтр за датою/статусами.
    Підмішується в кожен `List*State`; конкретний запит до БД виконує `_reload`,
    який реалізує клас-нащадок (різні DAO/типи)."""

    # Пагінація
    _current_page: int = 1
    _all_pages: int = 1
    _limit: int = 20

    # Фільтр (карта з'являється по кнопці)
    is_filter_open: bool = False
    filter_date_from: str = ""
    filter_date_to: str = ""
    selected_statuses: List[int] = []

    # Має реалізувати нащадок: оновлює self.items і self._all_pages за поточними
    # сторінкою/фільтрами (виклик відповідного DAO.get_paginated/...).
    def _reload(self) -> None:
        raise NotImplementedError

    # Vars
    # ======================
    @rx.var
    def get_current_page(self) -> str:
        return str(self._current_page)

    @rx.var
    def get_all_pages(self) -> str:
        return str(self._all_pages)

    @rx.var
    def has_active_filters(self) -> bool:
        return bool(
            self.filter_date_from or self.filter_date_to or self.selected_statuses
        )

    @rx.var
    def statuses_for_filter(self) -> List[Tuple[int, str, bool]]:
        # (індекс статусу, назва, чи обраний)
        return [
            (index, name, index in self.selected_statuses)
            for index, name in enumerate(movements_status_list)
        ]
    # ======================

    # Backend only
    # ======================
    def _reset_list_state(self) -> None:
        self._current_page = 1
        self.is_filter_open = False
        self.filter_date_from = ""
        self.filter_date_to = ""
        self.selected_statuses = []
    # ======================

    # Event handlers
    # ======================
    @rx.event
    def toggle_filter(self):
        self.is_filter_open = not self.is_filter_open

    @rx.event
    def on_change_filter_date_from(self, value: str):
        self.filter_date_from = value

    @rx.event
    def on_change_filter_date_to(self, value: str):
        self.filter_date_to = value

    @rx.event
    def set_status(self, index: int, checked: bool):
        if checked and index not in self.selected_statuses:
            self.selected_statuses = self.selected_statuses + [index]
        elif not checked and index in self.selected_statuses:
            self.selected_statuses = [s for s in self.selected_statuses if s != index]

    @rx.event
    def apply_filters(self):
        self._current_page = 1
        self._reload()

    @rx.event
    def reset_filters(self):
        self.filter_date_from = ""
        self.filter_date_to = ""
        self.selected_statuses = []
        self._current_page = 1
        self._reload()

    @rx.event
    def current_page_increment(self):
        if self._current_page + 1 <= self._all_pages:
            self._current_page += 1
            self._reload()

    @rx.event
    def current_page_decrement(self):
        if self._current_page > 1:
            self._current_page -= 1
            self._reload()

    @rx.event
    def on_change_current_page(self, value: str):
        if value != "" and value.isdigit() and 0 < int(value) <= self._all_pages:
            self._current_page = int(value)
            self._reload()
    # ======================
