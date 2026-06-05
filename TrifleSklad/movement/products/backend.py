from typing import Dict, List, Optional, Tuple

import reflex as rx

from TrifleSklad.dao import ProductDAO
from TrifleSklad.models import Product
from TrifleSklad.movement.products_selector.backend import ProductsSelectorState


class ProductsMovementListState(rx.State):
    items: List[Product] = []

    dialog_open: bool = False
    view_mode: bool = False

    filter_by_owner: int = -1
    filter_by_storage: int = -1

    # Подільне ТМЦ: режим (передати цілком / розділити) та обсяг частини,
    # ключ — id одиниці товару.
    split_mode: Dict[int, bool] = {}
    split_amount: Dict[int, str] = {}

    products_selector_state: Optional[ProductsSelectorState] = None

    async def on_load(self):
        # FUTURE: обследовать работу, возможно есть способ лучше
        self.products_selector_state = await self.get_state(ProductsSelectorState)
        self.products_selector_state.clear()
        self.split_mode = {}
        self.split_amount = {}

    def set_view_mode(self, is_view: bool):
        self.view_mode = is_view

    @rx.var
    def is_view_mode(self) -> bool:
        return self.view_mode

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def ability_open_dialog(self) -> bool:
        return (
            True if self.filter_by_owner > -1 and self.filter_by_storage > -1 else False
        )

    @rx.var
    def get_items(self) -> List[Tuple[int, Product]]:
        return [(index, item) for index, item in enumerate(self.items)]

    @rx.event
    def open_dialog(self):
        filter_products = [item.id for item in self.items]
        self.products_selector_state.set_filter(
            self.filter_by_owner, self.filter_by_storage, filter_products
        )
        self.dialog_open = True

    @rx.event
    def close_dialog(self):
        self.dialog_open = False

    @rx.event
    def on_save_selected(self):
        selected = self.products_selector_state.get_selected_items_only()
        self.items += selected
        # За замовчуванням — передати цілком; режим розділення вмикає користувач.
        for product in selected:
            if self._is_divisible(product):
                self.split_mode[product.id] = False
                self.split_amount[product.id] = ""
        self.close_dialog()

    @rx.event
    def on_remove_selected(self, item: int):
        if 0 <= item < len(self.items):
            removed = self.items.pop(item)
            self.split_mode.pop(removed.id, None)
            self.split_amount.pop(removed.id, None)

    @rx.event
    def set_split_mode_value(self, product_id: int, value: str):
        self.split_mode[product_id] = value == "split"

    @rx.event
    def set_split_amount(self, product_id: int, value: str):
        self.split_amount[product_id] = value

    @staticmethod
    def _is_divisible(product: Product) -> bool:
        return product.product_catalog is not None and product.product_catalog.divisible

    def resolve_movement_products(self) -> Tuple[bool, str, List[Product]]:
        """Готує підсумковий перелік одиниць товару для руху: для позицій у режимі
        «розділити» створює дочірні одиниці потрібного обсягу (батьківські зменшує).
        Спершу повністю валідує всі обсяги, лише потім вносить зміни в БД."""
        # Прохід 1 — валідація обсягів (без змін у БД).
        for product in self.items:
            if not (self._is_divisible(product) and self.split_mode.get(product.id, False)):
                continue
            title = product.product_catalog.title
            raw = self.split_amount.get(product.id, "")
            try:
                amount = int(raw)
            except (TypeError, ValueError):
                return False, f"Невірний обсяг для розділення «{title}»!", []
            if amount < 1 or amount >= product.count:
                return (
                    False,
                    f"Обсяг для «{title}» має бути від 1 до {product.count - 1} "
                    "(не можна передати всю ємність у нову одиницю)!",
                    [],
                )

        # Прохід 2 — застосування розділень.
        resolved: List[Product] = []
        for product in self.items:
            if self._is_divisible(product) and self.split_mode.get(product.id, False):
                amount = int(self.split_amount.get(product.id, "0"))
                flag, text, child = ProductDAO.split_product(product.id, amount)
                if not flag or child is None:
                    return False, text, []
                child.product_catalog = product.product_catalog
                resolved.append(child)
            else:
                resolved.append(product)
        return True, "", resolved
