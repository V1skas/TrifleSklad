from typing import List, Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.dao_legacy import (
    OwnerDAO,
    ProductCatalogDAO,
    ProductCategoryDAO,
    ProductDAO,
    StorageDAO,
)
from TrifleSklad.declared import StorageType
from TrifleSklad.states.app import AppState

ALL = "all"


class StockReportState(AppState):
    in_progress: bool = True

    rows: List[Tuple[int, str, str, int, int]] = []

    _catalog_cache: List[Tuple[str, str, str]] = []
    list_categories: List[Tuple[str, str]] = []
    _storages_cache: List[Tuple[str, str, int]] = []
    list_owners: List[Tuple[str, str]] = []

    filter_catalog: str = ""
    filter_category: str = ""
    filter_storage: str = ""
    filter_owner: str = ""
    exclude_warehouse: bool = False
    exclude_site: bool = False
    exclude_department: bool = False
    exclude_client: bool = False

    search_catalog: str = ""
    search_storage: str = ""
    search_text: str = ""

    is_units_open: bool = False
    selected_title: str = ""
    unit_rows: List[Tuple[str, str, str, str, str, bool]] = []

    def _excluded_types(self) -> List[int]:
        excluded: List[int] = []
        if self.exclude_warehouse:
            excluded.append(StorageType.WAREHOUSE)
        if self.exclude_site:
            excluded.append(StorageType.TECHNICAL_SITE)
        if self.exclude_department:
            excluded.append(StorageType.DEPARTMENT)
        if self.exclude_client:
            excluded.append(StorageType.CLIENT)
        return excluded

    def _load_filter_options(self):
        self._catalog_cache = [
            (str(c.id), c.title, str(c.id_category) if c.id_category else "")
            for c in ProductCatalogDAO.get_all()
        ]
        self.list_categories = ProductCategoryDAO.get_hierarchy_options()
        self._storages_cache = [
            (str(s.id), s.title, s.type) for s in StorageDAO.get_all()
        ]
        self.list_owners = [(str(o.id), o.title) for o in OwnerDAO.get_all()]

    def _sync_catalog_filter(self):
        if self.filter_catalog == "" or self.filter_category == "":
            return
        for cid, _title, cat in self._catalog_cache:
            if cid == self.filter_catalog:
                if cat != self.filter_category:
                    self.filter_catalog = ""
                break

    def _sync_storage_filter(self):
        if self.filter_storage == "":
            return
        excluded = self._excluded_types()
        for sid, _title, stype in self._storages_cache:
            if sid == self.filter_storage:
                if stype in excluded:
                    self.filter_storage = ""
                break

    def _reload(self):
        self.rows = ProductDAO.get_stock_grouped(
            int(self.filter_catalog) if self.filter_catalog else None,
            int(self.filter_storage) if self.filter_storage else None,
            int(self.filter_owner) if self.filter_owner else None,
            self._excluded_types(),
            int(self.filter_category) if self.filter_category else None,
            self.search_text or None,
        )

    @rx.var
    def has_rows(self) -> bool:
        return len(self.rows) > 0

    @rx.var
    def list_storages(self) -> List[Tuple[str, str]]:
        excluded = self._excluded_types()
        return [
            (sid, title)
            for sid, title, stype in self._storages_cache
            if stype not in excluded
        ]

    @rx.var
    def filtered_list_catalog(self) -> List[Tuple[str, str]]:
        base = [
            (cid, title)
            for cid, title, cat in self._catalog_cache
            if self.filter_category == "" or cat == self.filter_category
        ]
        term = self.search_catalog.strip().lower()
        if term == "":
            return base
        return [c for c in base if term in c[1].lower()]

    @rx.var
    def filtered_list_storages(self) -> List[Tuple[str, str]]:
        excluded = self._excluded_types()
        base = [
            (sid, title)
            for sid, title, stype in self._storages_cache
            if stype not in excluded
        ]
        term = self.search_storage.strip().lower()
        if term == "":
            return base
        return [s for s in base if term in s[1].lower()]

    @rx.var
    def filter_catalog_value(self) -> str:
        return self.filter_catalog if self.filter_catalog != "" else ALL

    @rx.var
    def filter_category_value(self) -> str:
        return self.filter_category if self.filter_category != "" else ALL

    @rx.var
    def filter_storage_value(self) -> str:
        return self.filter_storage if self.filter_storage != "" else ALL

    @rx.var
    def filter_owner_value(self) -> str:
        return self.filter_owner if self.filter_owner != "" else ALL

    @rx.event
    def on_load(self):
        if not self.has_permission(Action.REPORTS_STOCK):
            yield rx.redirect(routes.WELCOME)
            yield rx.toast.error("У Вас немає дозволу на перегляд цієї сторінки!")
            return

        self.in_progress = True
        self.filter_catalog = ""
        self.filter_category = ""
        self.filter_storage = ""
        self.filter_owner = ""
        self.exclude_warehouse = False
        self.exclude_site = False
        self.exclude_department = False
        self.exclude_client = False
        self.search_text = ""
        self.is_units_open = False
        self.unit_rows = []
        self.selected_title = ""

        self._load_filter_options()
        self._reload()
        self.in_progress = False

    @rx.event
    def on_change_search_catalog(self, value: str):
        self.search_catalog = value

    @rx.event
    def on_change_search_storage(self, value: str):
        self.search_storage = value

    @rx.event
    def on_change_search_text(self, value: str):
        self.search_text = value
        self._reload()

    @rx.event
    def on_change_catalog(self, value: str):
        self.filter_catalog = "" if value == ALL else value
        self._reload()

    @rx.event
    def on_change_category(self, value: str):
        self.filter_category = "" if value == ALL else value
        self._sync_catalog_filter()
        self._reload()

    @rx.event
    def on_change_storage(self, value: str):
        self.filter_storage = "" if value == ALL else value
        self._reload()

    @rx.event
    def on_change_owner(self, value: str):
        self.filter_owner = "" if value == ALL else value
        self._reload()

    @rx.event
    def on_change_exclude_warehouse(self, value: bool):
        self.exclude_warehouse = value
        self._sync_storage_filter()
        self._reload()

    @rx.event
    def on_change_exclude_site(self, value: bool):
        self.exclude_site = value
        self._sync_storage_filter()
        self._reload()

    @rx.event
    def on_change_exclude_department(self, value: bool):
        self.exclude_department = value
        self._sync_storage_filter()
        self._reload()

    @rx.event
    def on_change_exclude_client(self, value: bool):
        self.exclude_client = value
        self._sync_storage_filter()
        self._reload()

    @rx.event
    def reset_filters(self):
        self.filter_catalog = ""
        self.filter_category = ""
        self.filter_storage = ""
        self.filter_owner = ""
        self.exclude_warehouse = False
        self.exclude_site = False
        self.exclude_department = False
        self.exclude_client = False
        self.search_text = ""
        self._reload()

    @rx.event
    def open_units(self, catalog_id: int, title: str):
        self.selected_title = title
        units = ProductDAO.get_stock_units(
            catalog_id,
            int(self.filter_storage) if self.filter_storage else None,
            int(self.filter_owner) if self.filter_owner else None,
            self._excluded_types(),
            self.search_text or None,
        )
        rows: List[Tuple[str, str, str, str, str, bool]] = []
        for unit in units:
            divisible = (
                unit.product_catalog.divisible
                if unit.product_catalog is not None
                else False
            )
            serial = unit.serial_number if unit.serial_number else "—"
            storage = unit.storage.title if unit.storage is not None else "—"
            owner = unit.owner.title if unit.owner is not None else "—"
            count = str(unit.count) if divisible else "—"
            rows.append((str(unit.id), serial, storage, owner, count, unit.excluded_from_accounting))
        self.unit_rows = rows
        self.is_units_open = True

    @rx.event
    def set_units_open(self, value: bool):
        self.is_units_open = value
        if not value:
            self.unit_rows = []
            self.selected_title = ""
