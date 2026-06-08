from typing import List, Tuple

import reflex as rx

from TrifleSklad.dao import ProductDAO
from TrifleSklad.models import Product


class ProductsSelectorState(rx.State):
    items: List[Product] = []
    unselected_items: List[int] = []
    selected_items: List[int] = []
    unselected_items_filtered: List[int] = []
    selected_items_filtered: List[int] = []

    filter_many: str = ""
    filter_by_owner: int = -1
    filter_by_storage: int = -1
    filter_by_products: List[int] = []

    # Прапорець завантаження доступного ТМЦ (для показу скелетону в діалозі).
    is_loading: bool = False

    def clear(self) -> None:
        self.items = []
        self.unselected_items = []
        self.selected_items = []
        self.unselected_items_filtered = []
        self.selected_items_filtered = []
        self.filter_many = ""
        self.filter_by_owner = -1
        self.filter_by_storage = -1
        self.filter_by_products = []
        self.is_loading = False

    def reset_items(self) -> None:
        """Скидає перелік ТМЦ і службові індекси (без скидання фільтрів). Потрібно
        перед перезавантаженням діалогу: інакше обчислювані get_selected_items/
        get_unselected_items звертаються до застарілих індексів уже порожнього
        self.items під час проміжної дельти-скелетону → IndexError."""
        self.items = []
        self.unselected_items = []
        self.selected_items = []
        self.unselected_items_filtered = []
        self.selected_items_filtered = []

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    def set_filter(
        self,
        owner: int = -1,
        storage: int = -1,
        products: List[int] = [],
        many: str = "",
    ) -> None:
        self.filter_by_owner = owner
        self.filter_by_storage = storage
        self.filter_by_products = products
        self.filter_many = many
        self._load_items()

    def _load_items(self) -> None:
        self.items = ProductDAO.get_by_owner_storage_with_product_catalog(
            self.filter_by_owner, self.filter_by_storage
        )
        self.items = [
            item for item in self.items if item.id not in self.filter_by_products
        ]
        self.selected_items = []
        self.unselected_items = [i for i in range(len(self.items))]
        self.filter()

    def get_selected_items_only(self) -> List[Product]:
        return [self.items[index] for index in self.selected_items]

    @rx.var
    def get_selected_items(self) -> List[Tuple[int, Product]]:
        if self.filter_many != "":
            return [
                (index, self.items[index])
                for index in reversed(self.selected_items_filtered)
            ]
        else:
            return [
                (index, self.items[index]) for index in reversed(self.selected_items)
            ]

    @rx.var
    def get_unselected_items(self) -> List[Tuple[int, Product]]:
        if self.filter_many != "":
            return [
                (index, self.items[index])
                for index in reversed(self.unselected_items_filtered)
            ]
        else:
            return [(index, self.items[index]) for index in self.unselected_items]

    @rx.event
    def filter(self):
        if self.filter_many == "":
            self.unselected_items_filtered = self.unselected_items.copy()
            self.selected_items_filtered = self.selected_items.copy()
        else:
            self.unselected_items_filtered = [
                i
                for i in self.unselected_items
                if self.items[i]
                .product_catalog.title.lower()
                .find(self.filter_many.lower())
                != -1
                or self.items[i].serial_number is not None
                and self.items[i].serial_number.lower().find(self.filter_many.lower())
                != -1
                or str(self.items[i].id).lower().find(self.filter_many.lower()) != -1
            ]
            self.selected_items_filtered = [
                i
                for i in self.selected_items
                if self.items[i]
                .product_catalog.title.lower()
                .find(self.filter_many.lower())
                != -1
                or self.items[i].serial_number is not None
                and self.items[i].serial_number.lower().find(self.filter_many.lower())
                != -1
                or str(self.items[i].id).lower().find(self.filter_many.lower()) != -1
            ]

    @rx.event
    def select_item(self, item: int) -> None:
        if item in self.selected_items:
            self.selected_items.remove(item)
            self.unselected_items.append(item)
            self.unselected_items.sort()
        else:
            self.unselected_items.remove(item)
            self.selected_items.append(item)
            self.selected_items.sort()
        self.filter()

    @rx.event
    def change_filter_many(self, value: str):
        self.filter_many = value
        self.filter()
