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

    # Чи обов'язковий вибір власника для відкриття діалогу. Вимикається там, де
    # власник не задається (напр. повернення з площадки — фільтр лише за складом,
    # кожна одиниця зберігає свого власника).
    require_owner: bool = True

    # Обов'язковість серійного номера (вмикається лише там, де він потрібен —
    # напр. при видачі/продажу ТМЦ із серійним номером).
    require_serial: bool = False

    # Ввід ціни за позицію (вмикається лише там, де він потрібен — напр. продаж).
    # Ключ — id позиції каталогу, значення — введена ціна за одиницю.
    require_price: bool = False
    prices: Dict[int, str] = {}

    products_selector_state: Optional[ProductsSelectorState] = None

    async def on_load(self):
        # FUTURE: обследовать работу, возможно есть способ лучше
        self.products_selector_state = await self.get_state(ProductsSelectorState)
        self.products_selector_state.clear()
        self.split_mode = {}
        self.split_amount = {}
        self.require_owner = True
        self.require_serial = False
        self.require_price = False
        self.prices = {}
        # Скидаємо фільтри місця/власника, інакше кнопка «Додати» лишається
        # активною зі застарілими значеннями (і діалог показав би чужий ТМЦ),
        # доки користувач не обере склад і власника заново.
        self.filter_by_owner = -1
        self.filter_by_storage = -1
        self.items = []

    def set_view_mode(self, is_view: bool):
        self.view_mode = is_view

    def set_require_serial(self, flag: bool):
        self.require_serial = flag

    def set_require_owner(self, flag: bool):
        self.require_owner = flag

    def set_require_price(self, flag: bool):
        self.require_price = flag

    @rx.event
    def set_price(self, catalog_id: int, value: str):
        self.prices[catalog_id] = value

    def get_prices(self) -> Dict[int, float]:
        result: Dict[int, float] = {}
        for catalog_id, value in self.prices.items():
            try:
                result[catalog_id] = float(value) if value not in (None, "") else 0.0
            except (TypeError, ValueError):
                result[catalog_id] = 0.0
        return result

    @rx.event
    def set_serial_number(self, product_id: int, value: str):
        for index, product in enumerate(self.items):
            if product.id == product_id:
                self.items[index].serial_number = value
                break

    @rx.var
    def is_view_mode(self) -> bool:
        return self.view_mode

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def ability_open_dialog(self) -> bool:
        # Потрібен обраний склад; власник — лише якщо require_owner.
        if self.filter_by_storage <= -1:
            return False
        return self.filter_by_owner > -1 or not self.require_owner

    @rx.var
    def get_items(self) -> List[Tuple[int, Product]]:
        return [(index, item) for index, item in enumerate(self.items)]

    def _grouped_counts(self) -> Dict[int, Tuple[str, int]]:
        # Групує вибрані одиниці за позицією каталогу: id -> (назва, кількість).
        groups: Dict[int, Tuple[str, int]] = {}
        for product in self.items:
            if product.product_catalog is None:
                continue
            catalog_id = product.product_catalog.id
            title, count = groups.get(catalog_id, (product.product_catalog.title, 0))
            groups[catalog_id] = (title, count + 1)
        return groups

    @rx.var
    def price_positions(self) -> List[Tuple[int, str, int]]:
        # Позиції (id каталогу, назва, кількість) для вводу ціни при продажу.
        return [
            (catalog_id, title, count)
            for catalog_id, (title, count) in self._grouped_counts().items()
        ]

    @rx.var
    def total_cost(self) -> float:
        prices = self.get_prices()
        total = 0.0
        for catalog_id, (_title, count) in self._grouped_counts().items():
            total += prices.get(catalog_id, 0.0) * count
        return round(total, 2)

    @rx.event
    def open_dialog(self):
        # Спершу показуємо скелетон, потім (після yield) довантажуємо ТМЦ —
        # щоб користувач бачив процес завантаження, а не порожній діалог.
        self.products_selector_state.is_loading = True
        # Скидаємо не лише items, а й службові індекси — інакше обчислювані
        # get_(un)selected_items впадуть на застарілих індексах під час дельти.
        self.products_selector_state.reset_items()
        self.dialog_open = True
        yield
        filter_products = [item.id for item in self.items]
        self.products_selector_state.set_filter(
            self.filter_by_owner, self.filter_by_storage, filter_products
        )
        self.products_selector_state.is_loading = False

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
            # Ініціалізуємо ціну позиції (для продажу), якщо її ще немає.
            if (
                product.product_catalog is not None
                and product.product_catalog.id not in self.prices
            ):
                self.prices[product.product_catalog.id] = ""
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
        # Прохід 0 — серійні номери (обов'язкові лише там, де require_serial,
        # напр. при видачі/продажу ТМЦ із серійним номером).
        if self.require_serial:
            for product in self.items:
                if product.product_catalog is None or not product.product_catalog.uniq:
                    continue
                serial = product.serial_number
                if serial is None or not serial.strip():
                    return (
                        False,
                        f"Вкажіть серійний номер для «{product.product_catalog.title}»!",
                        [],
                    )

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
