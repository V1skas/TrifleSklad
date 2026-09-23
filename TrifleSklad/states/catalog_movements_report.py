from typing import List, Optional, Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.dao_legacy import MovementDAO, OwnerDAO, ProductCategoryDAO, StorageDAO
from TrifleSklad.declared import MovementsType, movements_status_list, movements_type_list
from TrifleSklad.movement.list_mixin import SCROLL_TOP_SCRIPT
from TrifleSklad.states.app import AppState

ALL = "all"


def _storage_owner_label(storage, owner) -> str:
    """«Склад (Власник)» або «Склад», або «—» — спільна розмітка джерела/
    призначення руху для звіту."""
    if storage is None:
        return "—"
    if owner is not None:
        return f"{storage.title} ({owner.title})"
    return storage.title


def _sender_label(movement, supplier_title: Optional[str]) -> str:
    """Відправник руху за типом: постачання → постачальник; повернення
    продажу → «Клієнт»; решта → склад/власник відправлення."""
    if movement.type == MovementsType.ADMISSION:
        return supplier_title or "—"
    if movement.type == MovementsType.SALE_RETURN:
        return "Клієнт"
    return _storage_owner_label(movement.incoming_storage, movement.incoming_owner)


def _receiver_label(movement) -> str:
    """Отримувач/призначення руху за типом: за наявності — склад/власник
    призначення; продаж → «Клієнт»; списання → «Списано»; інакше «—»."""
    if movement.destination_storage is not None:
        return _storage_owner_label(movement.destination_storage, movement.destination_owner)
    if movement.type == MovementsType.SALE:
        return "Клієнт"
    if movement.type == MovementsType.WRITE_OFF:
        return "Списано"
    return "—"


class CatalogMovementsReportState(AppState):
    in_progress: bool = True

    # (catalog_id, title, unit, category_title, movement_count)
    rows: List[Tuple[int, str, str, str, int]] = []

    # Кеші опцій фільтрів.
    list_categories: List[Tuple[str, str]] = []
    _storages_cache: List[Tuple[str, str]] = []
    list_owners: List[Tuple[str, str]] = []

    # Фільтри (внутрішньо "" = без фільтра; селекти показують ALL).
    search_text: str = ""
    filter_category: str = ""
    filter_incoming_storage: str = ""
    filter_destination_storage: str = ""
    filter_incoming_owner: str = ""
    filter_destination_owner: str = ""
    date_from: str = ""
    date_to: str = ""
    exclude_canceled: bool = False

    # Пошук усередині селектів складів (їх може бути багато, зокрема клієнти).
    search_incoming_storage: str = ""
    search_destination_storage: str = ""

    _current_page: int = 1
    _all_pages: int = 1
    _limit: int = 20

    # Діалог зі списком рухів обраної позиції.
    is_movements_open: bool = False
    selected_title: str = ""
    selected_catalog_id: int = -1
    # (id, тип, дата, відправник, отримувач, кількість, статус, view_url)
    movement_rows: List[Tuple[str, str, str, str, str, str, str, str]] = []

    # Пагінація діалогу (окрема від пагінації головної таблиці).
    _dialog_current_page: int = 1
    _dialog_all_pages: int = 1
    _dialog_limit: int = 20

    # Скид фільтрів/діалогу — лише при першому вході в сесії; повернення з
    # перегляду руху (повторний монтаж) зберігає фільтри й відкритий діалог.
    _initialized: bool = False

    def _load_filter_options(self):
        self.list_categories = ProductCategoryDAO.get_hierarchy_options()
        self._storages_cache = [(str(s.id), s.title) for s in StorageDAO.get_all()]
        self.list_owners = [(str(o.id), o.title) for o in OwnerDAO.get_all()]

    def _reload(self):
        count_items = MovementDAO.get_catalog_movement_summary_count(
            date_from=self.date_from,
            date_to=self.date_to,
            incoming_storage=self.filter_incoming_storage or None,
            destination_storage=self.filter_destination_storage or None,
            incoming_owner=self.filter_incoming_owner or None,
            destination_owner=self.filter_destination_owner or None,
            exclude_canceled=self.exclude_canceled,
            category_id=int(self.filter_category) if self.filter_category else None,
            search=self.search_text or None,
        )
        self._all_pages, self.rows = MovementDAO.get_catalog_movement_summary_paginated(
            page=self._current_page,
            limit=self._limit,
            count_items=count_items,
            date_from=self.date_from,
            date_to=self.date_to,
            incoming_storage=self.filter_incoming_storage or None,
            destination_storage=self.filter_destination_storage or None,
            incoming_owner=self.filter_incoming_owner or None,
            destination_owner=self.filter_destination_owner or None,
            exclude_canceled=self.exclude_canceled,
            category_id=int(self.filter_category) if self.filter_category else None,
            search=self.search_text or None,
        )

    # --- computed vars ---

    @rx.var
    def has_rows(self) -> bool:
        return len(self.rows) > 0

    @rx.var
    def get_current_page(self) -> str:
        return str(self._current_page)

    @rx.var
    def get_all_pages(self) -> str:
        return str(self._all_pages)

    @rx.var
    def dialog_current_page(self) -> str:
        return str(self._dialog_current_page)

    @rx.var
    def dialog_all_pages(self) -> str:
        return str(self._dialog_all_pages)

    @rx.var
    def filter_category_value(self) -> str:
        return self.filter_category if self.filter_category != "" else ALL

    @rx.var
    def filter_incoming_storage_value(self) -> str:
        return self.filter_incoming_storage if self.filter_incoming_storage != "" else ALL

    @rx.var
    def filter_destination_storage_value(self) -> str:
        return self.filter_destination_storage if self.filter_destination_storage != "" else ALL

    @rx.var
    def filter_incoming_owner_value(self) -> str:
        return self.filter_incoming_owner if self.filter_incoming_owner != "" else ALL

    @rx.var
    def filter_destination_owner_value(self) -> str:
        return self.filter_destination_owner if self.filter_destination_owner != "" else ALL

    @rx.var
    def filtered_incoming_storages(self) -> List[Tuple[str, str]]:
        term = self.search_incoming_storage.strip().lower()
        if term == "":
            return self._storages_cache
        return [s for s in self._storages_cache if term in s[1].lower()]

    @rx.var
    def filtered_destination_storages(self) -> List[Tuple[str, str]]:
        term = self.search_destination_storage.strip().lower()
        if term == "":
            return self._storages_cache
        return [s for s in self._storages_cache if term in s[1].lower()]

    # --- events ---

    @rx.event
    def on_load(self):
        guard = self.access_guard(Action.REPORTS_CATALOG_MOVEMENTS)
        if guard is not None:
            yield guard
            return

        self.in_progress = True
        self._load_filter_options()

        if not self._initialized:
            self._initialized = True
            self._current_page = 1
            self.search_text = ""
            self.filter_category = ""
            self.filter_incoming_storage = ""
            self.filter_destination_storage = ""
            self.filter_incoming_owner = ""
            self.filter_destination_owner = ""
            self.date_from = ""
            self.date_to = ""
            self.exclude_canceled = False
            self.search_incoming_storage = ""
            self.search_destination_storage = ""
            self.is_movements_open = False
            self.movement_rows = []
            self.selected_title = ""
            self.selected_catalog_id = -1

        self._reload()

        # Повернення з перегляду руху — відновлюємо відкритий діалог.
        if self.is_movements_open and self.selected_catalog_id != -1:
            self._load_movements(self.selected_catalog_id, self.selected_title)

        self.in_progress = False

    @rx.event
    def on_change_search_text(self, value: str):
        self.search_text = value
        self._current_page = 1
        self._reload()

    @rx.event
    def on_change_category(self, value: str):
        self.filter_category = "" if value == ALL else value
        self._current_page = 1
        self._reload()

    @rx.event
    def on_change_incoming_storage(self, value: str):
        self.filter_incoming_storage = "" if value == ALL else value
        self._current_page = 1
        self._reload()

    @rx.event
    def on_change_destination_storage(self, value: str):
        self.filter_destination_storage = "" if value == ALL else value
        self._current_page = 1
        self._reload()

    @rx.event
    def on_change_incoming_owner(self, value: str):
        self.filter_incoming_owner = "" if value == ALL else value
        self._current_page = 1
        self._reload()

    @rx.event
    def on_change_destination_owner(self, value: str):
        self.filter_destination_owner = "" if value == ALL else value
        self._current_page = 1
        self._reload()

    @rx.event
    def on_change_date_from(self, value: str):
        self.date_from = value
        self._current_page = 1
        self._reload()

    @rx.event
    def on_change_date_to(self, value: str):
        self.date_to = value
        self._current_page = 1
        self._reload()

    @rx.event
    def on_change_exclude_canceled(self, value: bool):
        self.exclude_canceled = value
        self._current_page = 1
        self._reload()

    @rx.event
    def on_change_search_incoming_storage(self, value: str):
        self.search_incoming_storage = value

    @rx.event
    def on_change_search_destination_storage(self, value: str):
        self.search_destination_storage = value

    @rx.event
    def reset_filters(self):
        self.search_text = ""
        self.filter_category = ""
        self.filter_incoming_storage = ""
        self.filter_destination_storage = ""
        self.filter_incoming_owner = ""
        self.filter_destination_owner = ""
        self.date_from = ""
        self.date_to = ""
        self.exclude_canceled = False
        self.search_incoming_storage = ""
        self.search_destination_storage = ""
        self._current_page = 1
        self._reload()

    @rx.event
    def current_page_increment(self):
        if self._current_page + 1 <= self._all_pages:
            self._current_page += 1
            self._reload()
            return rx.call_script(SCROLL_TOP_SCRIPT)

    @rx.event
    def current_page_decrement(self):
        if self._current_page > 1:
            self._current_page -= 1
            self._reload()
            return rx.call_script(SCROLL_TOP_SCRIPT)

    @rx.event
    def on_change_current_page(self, value: str):
        if value != "" and 0 < int(value) <= self._all_pages:
            self._current_page = int(value)
            self._reload()
            return rx.call_script(SCROLL_TOP_SCRIPT)

    # --- діалог рухів позиції ---

    def _load_movements(self, catalog_id: int, title: str) -> None:
        self.selected_catalog_id = catalog_id
        self.selected_title = title
        count_items = MovementDAO.get_movements_by_catalog_count(
            catalog_id,
            date_from=self.date_from,
            date_to=self.date_to,
            incoming_storage=self.filter_incoming_storage or None,
            destination_storage=self.filter_destination_storage or None,
            incoming_owner=self.filter_incoming_owner or None,
            destination_owner=self.filter_destination_owner or None,
            exclude_canceled=self.exclude_canceled,
        )
        self._dialog_all_pages, movements = MovementDAO.get_movements_by_catalog(
            catalog_id,
            page=self._dialog_current_page,
            limit=self._dialog_limit,
            count_items=count_items,
            date_from=self.date_from,
            date_to=self.date_to,
            incoming_storage=self.filter_incoming_storage or None,
            destination_storage=self.filter_destination_storage or None,
            incoming_owner=self.filter_incoming_owner or None,
            destination_owner=self.filter_destination_owner or None,
            exclude_canceled=self.exclude_canceled,
        )
        rows: List[Tuple[str, str, str, str, str, str, str, str]] = []
        for movement, count, supplier_title in movements:
            type_title = movements_type_list.get(movement.type, "—")
            status_title = (
                movements_status_list[movement.status]
                if 0 <= movement.status < len(movements_status_list)
                else "—"
            )
            rows.append(
                (
                    str(movement.id),
                    type_title,
                    movement.date,
                    _sender_label(movement, supplier_title),
                    _receiver_label(movement),
                    str(count),
                    status_title,
                    routes.movement_view_url(movement.type, movement.id),
                )
            )
        self.movement_rows = rows

    @rx.event
    def open_movements(self, catalog_id: int, title: str):
        self._dialog_current_page = 1
        self._load_movements(catalog_id, title)
        self.is_movements_open = True

    @rx.event
    def set_movements_open(self, value: bool):
        self.is_movements_open = value
        if not value:
            self.movement_rows = []
            self.selected_title = ""
            self.selected_catalog_id = -1
            self._dialog_current_page = 1
            self._dialog_all_pages = 1

    @rx.event
    def dialog_page_increment(self):
        if self._dialog_current_page + 1 <= self._dialog_all_pages:
            self._dialog_current_page += 1
            self._load_movements(self.selected_catalog_id, self.selected_title)

    @rx.event
    def dialog_page_decrement(self):
        if self._dialog_current_page > 1:
            self._dialog_current_page -= 1
            self._load_movements(self.selected_catalog_id, self.selected_title)

    @rx.event
    def on_change_dialog_page(self, value: str):
        if value != "" and 0 < int(value) <= self._dialog_all_pages:
            self._dialog_current_page = int(value)
            self._load_movements(self.selected_catalog_id, self.selected_title)
