import reflex as rx

from typing import List, Optional, Tuple

import TrifleSklad.routes as routes
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.declared import movements_type_list, movements_status_list

from TrifleSklad.models import Product
from TrifleSklad.dao import ProductCatalogDAO, ProductDAO, MovementDAO
from TrifleSklad.movement.list_mixin import ALL


class UnitsReportState(rx.State):
    app_state: Optional[AppState] = None

    # "list" — перелік одиниць; "view" — деталь однієї одиниці з історією руху.
    page_mode: str = "list"

    # Список
    # ======================
    items: List[Product] = []
    list_catalog: List[Tuple[str, str]] = []
    search_str: Optional[str] = None
    filter_catalog_id: str = ALL

    _current_page: int = 1
    _all_pages: int = 1
    _limit: int = 20

    # Деталь
    # ======================
    unit: Optional[Product] = None
    # Рядок історії: (№, тип, дата, статус, маршрут, url-руху)
    history_rows: List[Tuple[str, str, str, str, str, str]] = []

    # Backend only
    # ======================
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

    def _load_unit(self, id: int):
        self.unit = ProductDAO.get_by_id_with_relationships(id)
        if self.unit is None:
            self.history_rows = []
            return
        rows: List[Tuple[str, str, str, str, str, str]] = []
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
            url = routes.movement_view_url(m.type, m.id)
            rows.append((str(m.id), type_title, m.date, status_title, route, url))
        self.history_rows = rows

    # Dynamic variables
    # ======================
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

    @rx.var
    def is_view_mode(self) -> bool:
        return self.page_mode == "view"

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
        return (
            self.unit.serial_number
            if self.unit is not None and self.unit.serial_number
            else "—"
        )

    @rx.var
    def unit_storage(self) -> str:
        return (
            self.unit.storage.title
            if self.unit is not None and self.unit.storage is not None
            else "—"
        )

    @rx.var
    def unit_owner(self) -> str:
        return (
            self.unit.owner.title
            if self.unit is not None and self.unit.owner is not None
            else "—"
        )

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
        return str(self.unit.count) if self.unit is not None else "—"

    @rx.var
    def has_history(self) -> bool:
        return len(self.history_rows) > 0

    # Action handlers
    # ======================
    @rx.event
    async def on_load(self):
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
        if not self.app_state.has_permission(ActionEnum.REPORTS_UNITS):
            return rx.redirect(routes.WELCOME)

        page = self.router.page.params.get("page", "")

        if page == "":
            # /reports/units — перелік одиниць
            self.page_mode = "list"
            self.unit = None
            self.history_rows = []
            self._current_page = 1
            self.search_str = None
            self.filter_catalog_id = ALL
            self._load_catalog_options()
            self._load_list()
            return None

        if page == "view":
            id = self.router.page.params.get("id", "")
            if id == "":
                return rx.redirect(routes.REPORTS_UNITS)
            self.page_mode = "view"
            self._load_unit(int(id))
            if self.unit is None:
                return [
                    rx.redirect(routes.REPORTS_UNITS),
                    rx.toast.error("Одиницю ТМЦ не знайдено!"),
                ]
            return None

        return rx.redirect(routes.REPORTS_UNITS)

    @rx.event
    def on_change_search_str(self, value: str):
        self.search_str = value if value != "" else None

    @rx.event
    def on_click_search(self):
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

    @rx.event
    def current_page_decrement(self):
        if self._current_page > 1:
            self._current_page -= 1
            self._load_list()

    @rx.event
    def on_change_current_page(self, value: str):
        if value != "" and 0 < int(value) <= self._all_pages:
            self._current_page = int(value)
            self._load_list()
