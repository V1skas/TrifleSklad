import reflex as rx

from typing import List, Optional, Tuple

from TrifleSklad.models import MovementProductsCatalog
from TrifleSklad.dao import ProductCatalogDAO

class MovementProductCatalogListState(rx.State):
    items: List[MovementProductsCatalog] = []
    selected_item: int = -1
    is_open_dialog: bool = False
    view_mode: bool = False
    total_cost: float = 0.0

    exclude_products_catalog_list: List[int] = []

    @rx.var
    def is_view_mode(self) -> bool:
        return self.view_mode

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def get_items(self) -> List[Tuple[int, MovementProductsCatalog]]:
        return [(index, item) for index, item in enumerate(self.items)]

    @rx.event
    def set_selected_item(self, item: int):
        if 0 <= item < len(self.items):
            self.selected_item = item
            return None
        else:
            self.selected_item = -1
            return rx.toast.error("Выбранный элемент вне диапазона")

    @rx.event
    def set_items(self, items: List[MovementProductsCatalog]):
        self.items = items
        self.selected_item = -1
        self.exclude_products_catalog_list = [item.product.id for item in items if item.product is not None]
        self.total_cost = sum(item.count * item.price for item in items)

    @rx.event
    def set_view_mode(self, is_view: bool):
        self.view_mode = is_view

    @rx.event
    def open_dialog(self):
        self.is_open_dialog = True

    @rx.event
    def close_dialog(self):
        self.is_open_dialog = False

    @rx.event
    async def on_add(self):
        self.selected_item = -1

        product_form: MovementProductCatalogState = await self.get_state(MovementProductCatalogState)
        product_form.load_products_catalog_list(self.exclude_products_catalog_list)
        product_form.set_current_page(MovementProductCatalogState.Pages.ADD)
        product_form.set_item(MovementProductsCatalog())

        self.open_dialog()

    @rx.event
    async def on_view(self, selected_item: int):
        if selected_item >= 0:
            self.selected_item = selected_item
            product_form = await self.get_state(MovementProductCatalogState)
            product_form.set_current_page(MovementProductCatalogState.Pages.VIEW)
            product_form.set_item(self.items[self.selected_item])

            self.open_dialog()
            return None
        else:
            return rx.toast.error("Не выбрана запись для просмотра")

    @rx.event
    async def on_delete(self):
        if self.selected_item >= 0:
            self.close_dialog()
            self.total_cost -= self.items[self.selected_item].count * self.items[self.selected_item].price
            self.exclude_products_catalog_list.remove(self.items[self.selected_item].product.id)
            del self.items[self.selected_item]
            self.selected_item = -1
            return None
        else:
            return rx.toast.error("Не выбрана запись для удаления")

    @rx.event
    async def on_save(self):
        product_form = await self.get_state(MovementProductCatalogState)
        item = product_form.save()

        if item is None:
            return rx.toast.error(product_form.error_text)

        if self.selected_item > -1:
            self.items[self.selected_item] = item
            self.exclude_products_catalog_list.remove(self.items[self.selected_item].product.id)
            self.exclude_products_catalog_list.append(item.product.id)
        else:
            self.items.append(item)
            self.exclude_products_catalog_list.append(item.product.id)

        self.total_cost = 0.0
        for item in self.items:
            self.total_cost += item.count * item.price

        self.close_dialog()
        return rx.toast.success("Позиция добавлена/изменена успешно")


class MovementProductCatalogState(rx.State):
    class Pages:
        ADD = "add"
        EDIT = "edit"
        VIEW = "view"

    product: str = ""
    count: str = "0"
    price: str = "0.0"
    serial_numbers: list[str] = []

    item: Optional[MovementProductsCatalog] = None

    product_error: bool = False
    count_error: bool = False
    price_error: bool = False

    error_text: str = "Обнаружена ошибка"

    current_page: str = ""

    products_catalog_list: List[Tuple[str, str]] = []

    def _check_correct(self) -> bool:
        result: bool = True

        if self.item.product is not None:
            self.product_error = False
        else:
            self.product_error = True
            result = False

        if len(self.count) > 0 and int(self.count) > int(0):
            self.count_error = False
        else:
            self.count_error = True
            result = False

        if len(self.price) > 0 and float(self.price) > float(0):
            self.price_error = False
        else:
            self.price_error = True
            result = False

        return result

    def load_products_catalog_list(self, exclude: List[int] = []):
        self.products_catalog_list = []
        for item in ProductCatalogDAO.get_all():
            if item.id not in exclude:
                self.products_catalog_list.append((item.title, str(item.id)))

    @rx.var
    def has_error(self) -> bool:
        return self.product_error or self.price_error or self.count_error

    @rx.event
    def on_change_product(self, value: str):
        self.product = value
        if self.product_error:
            self.product_error = False

    @rx.event
    def on_change_count(self, value: str):
        self.count = value
        if self.count_error:
            self.count_error = False

    @rx.event
    def on_change_price(self, value: str):
        self.price = value
        if self.price_error:
            self.price_error = False

    @rx.event
    def on_click_edit(self):
        self.load_products_catalog_list()
        self.current_page = MovementProductCatalogState.Pages.EDIT

    @rx.event
    def set_current_page(self, page: str):
        self.current_page = page

    @rx.event
    def set_item(self, item: MovementProductsCatalog):
        self.item = item

        self.product_error = False
        self.count_error = False
        self.price_error = False

        if self.current_page != MovementProductCatalogState.Pages.ADD:
            self.product = str(item.product.id) if item.product else ""
            self.count = str(item.count)
            self.price = str(item.price)
        else:
            self.product = ""
            self.count = "0"
            self.price = "0.0"

    def save(self):
        self.item.product = ProductCatalogDAO.get_by_id(self.product)
        self.item.id_product_catalog = self.item.product.id
        if not self._check_correct():
            return None

        self.item.count = int(self.count)
        self.item.price = float(self.price)

        return self.item
