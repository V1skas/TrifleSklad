import reflex as rx

from typing import List, Optional, Tuple

from TrifleSklad.models import Product

from TrifleSklad.movement.products_selector.backend import ProductsSelectorState

class ProductsMovementListState(rx.State):
    items: List[Product] = []

    dialog_open: bool = False
    view_mode: bool = False

    filter_by_owner: int = -1
    filter_by_storage: int = -1

    products_selector_state: Optional[ProductsSelectorState] = None

    async def on_load(self):
        # FUTURE: обследовать работу, возможно есть способ лучше
        self.products_selector_state = (await self.get_state(ProductsSelectorState))
        self.products_selector_state.clear()

    def set_view_mode(self, is_view: bool):
        self.view_mode = is_view

    @rx.var
    def is_view_mode(self) -> bool:
        return self.view_mode

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def ability_open_dialog(self) ->  bool:
        return True if self.filter_by_owner > -1 and self.filter_by_storage > -1 else False

    @rx.var
    def get_items(self) -> List[Tuple[int, Product]]:
        return [(index, item) for index, item in enumerate(self.items)]

    @rx.event
    def open_dialog(self):
        filter_products = [ item.id for item in self.items ]
        self.products_selector_state.set_filter(self.filter_by_owner, self.filter_by_storage, filter_products)
        self.dialog_open = True

    @rx.event
    def close_dialog(self):
        self.dialog_open = False

    @rx.event
    def on_save_selected(self):
        self.items += self.products_selector_state.get_selected_items_only()
        self.close_dialog()

    @rx.event
    def on_remove_selected(self, item: int):
        if 0 <= item < len(self.items):
            self.items.pop(item)