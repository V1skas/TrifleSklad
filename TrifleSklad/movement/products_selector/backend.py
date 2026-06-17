from typing import List, Optional, Tuple

import reflex as rx

from TrifleSklad.dao import ProductDAO
from TrifleSklad.models import Product


# Сентинел «без фільтра» для select-ів (Radix забороняє порожнє value у item).
ALL = "all"


class ProductsSelectorState(rx.State):
    # Обрані одиниці (повні об'єкти) — лишаються видимими завжди, незалежно від
    # фільтрів. Доступні (необрані) одиниці підвантажуються порціями з сервера.
    selected: List[Product] = []
    available: List[Product] = []

    # Параметри місця/власника та одиниці, які треба виключити (вже у русі).
    filter_by_owner: int = -1
    filter_by_storage: int = -1
    exclude_products: List[int] = []

    # Фільтри діалогу.
    filter_search: str = ""
    filter_catalog: str = ALL          # id позиції каталогу або ALL
    filter_min_remaining: str = ""     # залишок >= значення
    filter_fullness: str = ALL         # ALL / full / partial

    # Випадаючий список позицій каталогу, доступних на цьому місці/власнику.
    catalog_options: List[Tuple[str, str]] = []

    # Пагінація підвантаження за вимогою.
    _offset: int = 0
    _limit: int = 30
    has_more: bool = False

    # Прапорці завантаження (для скелетону: первинне/після фільтра — is_loading,
    # довантаження наступної порції — is_loading_more).
    is_loading: bool = False
    is_loading_more: bool = False

    def clear(self) -> None:
        self.selected = []
        self.available = []
        self.filter_by_owner = -1
        self.filter_by_storage = -1
        self.exclude_products = []
        self.filter_search = ""
        self.filter_catalog = ALL
        self.filter_min_remaining = ""
        self.filter_fullness = ALL
        self.catalog_options = []
        self._offset = 0
        self.has_more = False
        self.is_loading = False
        self.is_loading_more = False

    def reset_items(self) -> None:
        """Скидає переліки ТМЦ і пагінацію (без скидання фільтрів/місця). Потрібно
        перед перезавантаженням діалогу — щоб під час проміжної дельти-скелетону
        не лишалися застарілі дані."""
        self.selected = []
        self.available = []
        self._offset = 0
        self.has_more = False

    # Dynamic variables
    # ======================
    @rx.var
    def has_items(self) -> bool:
        return len(self.selected) > 0 or len(self.available) > 0

    @rx.var
    def get_selected_items(self) -> List[Tuple[int, Product]]:
        # index тут — id одиниці (для select/deselect за id, не за позицією).
        return [(item.id, item) for item in self.selected]

    @rx.var
    def get_available_items(self) -> List[Tuple[int, Product]]:
        return [(item.id, item) for item in self.available]
    # ======================

    # Backend only
    # ======================
    def _min_remaining_value(self) -> Optional[int]:
        raw = self.filter_min_remaining.strip()
        if raw == "":
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    def _catalog_id_value(self) -> int:
        if self.filter_catalog == ALL or self.filter_catalog == "":
            return -1
        try:
            return int(self.filter_catalog)
        except ValueError:
            return -1

    def _excluded_ids(self) -> List[int]:
        # Виключаємо вже додані до руху одиниці та вже обрані в діалозі.
        return list(self.exclude_products) + [p.id for p in self.selected]

    def _load_page(self, reset: bool) -> None:
        if reset:
            self._offset = 0
            self.available = []
        items, has_more = ProductDAO.get_filtered_paginated_by_owner_storage(
            owner_id=self.filter_by_owner,
            storage_id=self.filter_by_storage,
            exclude_ids=self._excluded_ids(),
            search=self.filter_search,
            catalog_id=self._catalog_id_value(),
            min_remaining=self._min_remaining_value(),
            fullness=self.filter_fullness,
            offset=self._offset,
            limit=self._limit,
        )
        if reset:
            self.available = items
        else:
            self.available = self.available + items
        self._offset += len(items)
        self.has_more = has_more

    def set_filter(
        self,
        owner: int = -1,
        storage: int = -1,
        products: List[int] = [],
    ) -> None:
        """Ініціалізація діалогу: задає місце/власника, перелік виключень,
        завантажує опції каталогу та першу порцію доступного ТМЦ."""
        self.filter_by_owner = owner
        self.filter_by_storage = storage
        self.exclude_products = products
        self.filter_search = ""
        self.filter_catalog = ALL
        self.filter_min_remaining = ""
        self.filter_fullness = ALL
        self.catalog_options = [
            (title, str(cid))
            for cid, title in ProductDAO.get_catalog_options_by_owner_storage(
                owner, storage
            )
        ]
        self._load_page(reset=True)
    # ======================

    # Action handlers
    # ======================
    @rx.event
    def load_more(self):
        # Захист від гонок: одне прокручування не має підтягнути кілька сторінок.
        if self.is_loading_more or not self.has_more or self.is_loading:
            return
        self.is_loading_more = True
        yield
        self._load_page(reset=False)
        self.is_loading_more = False

    @rx.event
    def apply_filters(self):
        self.is_loading = True
        yield
        self._load_page(reset=True)
        self.is_loading = False

    @rx.event
    def reset_filters(self):
        self.filter_search = ""
        self.filter_catalog = ALL
        self.filter_min_remaining = ""
        self.filter_fullness = ALL
        return ProductsSelectorState.apply_filters

    @rx.event
    def change_filter_search(self, value: str):
        self.filter_search = value
        return ProductsSelectorState.apply_filters

    @rx.event
    def change_filter_catalog(self, value: str):
        self.filter_catalog = value
        return ProductsSelectorState.apply_filters

    @rx.event
    def change_filter_min_remaining(self, value: str):
        self.filter_min_remaining = value
        return ProductsSelectorState.apply_filters

    @rx.event
    def change_filter_fullness(self, value: str):
        self.filter_fullness = value
        return ProductsSelectorState.apply_filters

    @rx.event
    def select_item(self, product_id: int) -> None:
        # Переносимо одиницю з доступних в обрані (лишається видимою при фільтрах).
        for index, product in enumerate(self.available):
            if product.id == product_id:
                self.selected = self.selected + [self.available.pop(index)]
                return

    @rx.event
    def deselect_item(self, product_id: int) -> None:
        # Повертаємо одиницю з обраних у початок доступних.
        for index, product in enumerate(self.selected):
            if product.id == product_id:
                removed = self.selected.pop(index)
                self.available = [removed] + self.available
                return

    def get_selected_items_only(self) -> List[Product]:
        return list(self.selected)
    # ======================
