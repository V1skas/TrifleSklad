from datetime import date
from typing import List, Tuple

import reflex as rx

from TrifleSklad.dao import OwnerDAO, StorageDAO
from TrifleSklad.declared import StorageType, movements_status_list

# Сентинел «без фільтра» для select-ів (Radix забороняє порожнє value у item).
ALL = "all"


class MovementListFilterMixin(rx.State, mixin=True):
    """Спільна логіка списків руху ТМЦ: сторінкування + фільтр за датою/статусами
    + (контекстно) за складом/власником відправлення/призначення.
    Підмішується в кожен `List*State`; конкретний запит до БД виконує `_reload`,
    який реалізує клас-нащадок (різні DAO/типи)."""

    # Пагінація
    _current_page: int = 1
    _all_pages: int = 1
    _limit: int = 20

    # Фільтр (карта з'являється по кнопці)
    is_filter_open: bool = False
    # Фільтр за датою вмикається перемикачем і застосовується по «Застосувати».
    filter_date_enabled: bool = False
    filter_date_from: str = ""
    filter_date_to: str = ""
    selected_statuses: List[int] = []

    # Фільтр за місцем/власником (застосовується кнопкою «Застосувати», як дата).
    # Який саме з них показувати — вирішує конкретна секція (передає у filter_card).
    filter_incoming_storage: str = ALL
    filter_destination_storage: str = ALL
    filter_incoming_owner: str = ALL
    filter_destination_owner: str = ALL

    # Опції селектів фільтра. list_storages — усі сховища; list_warehouses — лише
    # склади; list_sites — площадки/відділи (вибір залежить від контексту секції).
    list_storages: List[Tuple[str, str]] = []
    list_warehouses: List[Tuple[str, str]] = []
    list_sites: List[Tuple[str, str]] = []
    list_owners: List[Tuple[str, str]] = []

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
            self.filter_date_enabled
            or self.selected_statuses
            or self.filter_incoming_storage != ALL
            or self.filter_destination_storage != ALL
            or self.filter_incoming_owner != ALL
            or self.filter_destination_owner != ALL
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
    def _date_from_eff(self) -> str:
        # Дата застосовується лише коли перемикач увімкнено.
        return self.filter_date_from if self.filter_date_enabled else ""

    def _date_to_eff(self) -> str:
        return self.filter_date_to if self.filter_date_enabled else ""

    def _load_filter_options(self) -> None:
        storages = StorageDAO.get_all()
        self.list_storages = [(s.title, str(s.id)) for s in storages]
        self.list_warehouses = [
            (s.title, str(s.id)) for s in storages if s.type == StorageType.WAREHOUSE
        ]
        self.list_sites = [
            (s.title, str(s.id))
            for s in storages
            if s.type in (StorageType.TECHNICAL_SITE, StorageType.DEPARTMENT)
        ]
        self.list_owners = [(o.title, str(o.id)) for o in OwnerDAO.get_all()]

    def _reset_list_state(self) -> None:
        today = date.today().isoformat()
        self._current_page = 1
        self.is_filter_open = False
        self.filter_date_enabled = False
        # Дати за замовчуванням — сьогодні (видимі й у state), щоб фільтр спрацював
        # одразу після увімкнення перемикача, навіть якщо дату не чіпали.
        self.filter_date_from = today
        self.filter_date_to = today
        self.selected_statuses = []
        self.filter_incoming_storage = ALL
        self.filter_destination_storage = ALL
        self.filter_incoming_owner = ALL
        self.filter_destination_owner = ALL
        self._load_filter_options()
    # ======================

    # Event handlers
    # ======================
    @rx.event
    def toggle_filter(self):
        self.is_filter_open = not self.is_filter_open

    @rx.event
    def on_change_filter_date_enabled(self, value: bool):
        self.filter_date_enabled = value

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
    def on_change_filter_incoming_storage(self, value: str):
        self.filter_incoming_storage = value

    @rx.event
    def on_change_filter_destination_storage(self, value: str):
        self.filter_destination_storage = value

    @rx.event
    def on_change_filter_incoming_owner(self, value: str):
        self.filter_incoming_owner = value

    @rx.event
    def on_change_filter_destination_owner(self, value: str):
        self.filter_destination_owner = value

    @rx.event
    def reset_filters(self):
        today = date.today().isoformat()
        self.filter_date_enabled = False
        self.filter_date_from = today
        self.filter_date_to = today
        self.selected_statuses = []
        self.filter_incoming_storage = ALL
        self.filter_destination_storage = ALL
        self.filter_incoming_owner = ALL
        self.filter_destination_owner = ALL
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
