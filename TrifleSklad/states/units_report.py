from typing import List, Optional, Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.dao_legacy import MovementDAO, ProductCatalogDAO, ProductDAO
from TrifleSklad.declared import format_amount, movements_status_list, movements_type_list
from TrifleSklad.models import Product
from TrifleSklad.movement.list_mixin import ALL, SCROLL_TOP_SCRIPT
from TrifleSklad.states.app import AppState


class ListUnitsReportState(AppState):
    in_progress: bool = True

    items: List[Product] = []
    list_catalog: List[Tuple[str, str]] = []
    search_str: Optional[str] = None
    filter_catalog_id: str = ALL

    _current_page: int = 1
    _all_pages: int = 1
    _limit: int = 20

    def _load_catalog_options(self):
        self.list_catalog = [(c.title, str(c.id)) for c in ProductCatalogDAO.get_all()]

    def _catalog_filter(self) -> Optional[int]:
        if self.filter_catalog_id and self.filter_catalog_id != ALL:
            return int(self.filter_catalog_id)
        return None

    def _load_list(self):
        count_items = ProductDAO.get_units_count(self.search_str, self._catalog_filter())
        self._all_pages, self.items = ProductDAO.get_units_paginated(
            page=self._current_page,
            limit=self._limit,
            count_items=count_items,
            search=self.search_str,
            catalog_id=self._catalog_filter(),
        )

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def get_current_page(self) -> str:
        return str(self._current_page)

    @rx.var
    def get_all_pages(self) -> str:
        return str(self._all_pages)

    @rx.var
    def get_search_str(self) -> str:
        return self.search_str if self.search_str is not None else ""

    @rx.event
    def on_load(self):
        if not self.has_permission(Action.REPORTS_UNITS):
            yield rx.redirect(routes.WELCOME)
            yield rx.toast.error("У Вас немає дозволу на перегляд цієї сторінки!")
            return

        self.in_progress = True
        self._current_page = 1
        self.search_str = None
        self.filter_catalog_id = ALL
        self._load_catalog_options()
        self._load_list()
        self.in_progress = False

    @rx.event
    def on_change_search_str(self, value: str):
        # Гарячий пошук: фільтруємо одразу по вводу (з debounce у полі).
        self.search_str = value if value != "" else None
        self._current_page = 1
        self._load_list()

    @rx.event
    def on_change_filter_catalog(self, value: str):
        self.filter_catalog_id = value
        self._current_page = 1
        self._load_list()

    @rx.event
    def current_page_increment(self):
        if self._current_page + 1 <= self._all_pages:
            self._current_page += 1
            self._load_list()
            return rx.call_script(SCROLL_TOP_SCRIPT)

    @rx.event
    def current_page_decrement(self):
        if self._current_page > 1:
            self._current_page -= 1
            self._load_list()
            return rx.call_script(SCROLL_TOP_SCRIPT)

    @rx.event
    def on_change_current_page(self, value: str):
        if value != "" and 0 < int(value) <= self._all_pages:
            self._current_page = int(value)
            self._load_list()
            return rx.call_script(SCROLL_TOP_SCRIPT)


class ViewUnitsReportState(AppState):
    in_process: bool = True

    unit: Optional[Product] = None
    acquisition_cost: Optional[float] = None
    history_rows: List[Tuple[str, str, str, str, str, str, str]] = []

    def _load_unit(self, id: int):
        self.unit = ProductDAO.get_by_id_with_relationships(id)
        if self.unit is None:
            self.history_rows = []
            self.acquisition_cost = None
            return
        self.acquisition_cost = ProductDAO.get_acquisition_cost(id)
        rows: List[Tuple[str, str, str, str, str, str, str]] = []
        for m in MovementDAO.get_history_by_product_id(id):
            type_title = movements_type_list.get(m.type, "—")
            status_title = (
                movements_status_list[m.status]
                if 0 <= m.status < len(movements_status_list)
                else "—"
            )
            src = m.incoming_storage.title if m.incoming_storage is not None else "—"
            dst = m.destination_storage.title if m.destination_storage is not None else "—"
            route = f"{src} → {dst}"
            src_owner = m.incoming_owner.title if m.incoming_owner is not None else "—"
            dst_owner = m.destination_owner.title if m.destination_owner is not None else "—"
            owner_route = f"{src_owner} → {dst_owner}"
            url = routes.movement_view_url(m.type, m.id)
            rows.append((str(m.id), type_title, m.date, route, owner_route, status_title, url))
        self.history_rows = rows

    @rx.var
    def unit_title(self) -> str:
        return (
            self.unit.product_catalog.title
            if self.unit is not None and self.unit.product_catalog is not None
            else "—"
        )

    @rx.var
    def unit_unit(self) -> str:
        return (
            self.unit.product_catalog.unit
            if self.unit is not None and self.unit.product_catalog is not None
            else "—"
        )

    @rx.var
    def unit_serial(self) -> str:
        return self.unit.serial_number if self.unit is not None and self.unit.serial_number else "—"

    @rx.var
    def unit_storage(self) -> str:
        return self.unit.storage.title if self.unit is not None and self.unit.storage is not None else "—"

    @rx.var
    def unit_owner(self) -> str:
        return self.unit.owner.title if self.unit is not None and self.unit.owner is not None else "—"

    @rx.var
    def unit_divisible(self) -> bool:
        return (
            self.unit.product_catalog.divisible
            if self.unit is not None and self.unit.product_catalog is not None
            else False
        )

    @rx.var
    def unit_uniq(self) -> bool:
        return (
            self.unit.product_catalog.uniq
            if self.unit is not None and self.unit.product_catalog is not None
            else False
        )

    @rx.var
    def unit_count(self) -> str:
        return format_amount(self.unit.count) if self.unit is not None else "—"

    @rx.var
    def unit_fill_percent(self) -> int:
        # Заповненість полоси у відсотках (Progress приймає лише int). Без
        # фіксованої ємності — завжди повна (100%).
        if self.unit is None or self.unit.product_catalog is None:
            return 0
        catalog = self.unit.product_catalog
        if catalog.no_fixed_capacity:
            return 100
        if not catalog.capacity or catalog.capacity <= 0:
            return 0
        return int(min(100, round((self.unit.count / catalog.capacity) * 100)))

    @rx.var
    def unit_remain_label(self) -> str:
        if self.unit is None or self.unit.product_catalog is None:
            return "—"
        count = format_amount(self.unit.count)
        if self.unit.product_catalog.no_fixed_capacity:
            return f"{count}/∞ {self.unit.product_catalog.unit}"
        return f"{count}/{format_amount(self.unit.product_catalog.capacity)} {self.unit.product_catalog.unit}"

    @rx.var
    def unit_excluded(self) -> bool:
        return self.unit is not None and self.unit.excluded_from_accounting

    @rx.var
    def acquisition_cost_display(self) -> str:
        if self.acquisition_cost is None:
            return "—"
        return f"{self.acquisition_cost:.2f}"

    @rx.var
    def has_history(self) -> bool:
        return len(self.history_rows) > 0

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(Action.REPORTS_UNITS):
            yield rx.redirect(routes.WELCOME)
            yield rx.toast.error("У Вас немає дозволу на перегляд цієї сторінки!")
            return
        self.in_process = True
        self._load_unit(int(id))
        self.in_process = False
        if self.unit is None:
            yield rx.redirect(routes.REPORTS_UNITS)
            yield rx.toast.error("Одиницю ТМЦ не знайдено!")
