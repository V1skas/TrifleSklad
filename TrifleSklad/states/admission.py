from typing import List, Optional, Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.dao_legacy import (
    AdmissionDAO,
    MovementDAO,
    NDSRateDAO,
    OwnerDAO,
    PaymentTypeDAO,
    ProductCatalogDAO,
    ProductCategoryDAO,
    StorageDAO,
    SupplierDAO,
)
from TrifleSklad.declared import (
    MovementsStatus,
    MovementsType,
    StorageType,
    admission_nds_split,
    format_amount,
    format_transferred_qty,
    generate_serial_range,
    movements_status_list,
    movements_type_list,
)
from TrifleSklad.models import (
    Admission,
    Movement,
    MovementProductsCatalog,
    Product,
    ProductCatalog,
    ProductCategory,
)
from TrifleSklad.movement.inline_creators import LookupCreatorsMixin
from TrifleSklad.movement.list_mixin import ALL, MovementListFilterMixin
from TrifleSklad.states.app import AppState
from TrifleSklad.states.audit_mixin import AuditHistoryMixin
from TrifleSklad.states.movement_cancel_mixin import CancelWithReasonMixin
from TrifleSklad.states.movement_edit_mixin import FullEditMixin
from TrifleSklad.utils.clock import now_local


def _format_money(value: float) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def _parse_positive_float(value: str) -> Optional[float]:
    """Розбирає рядок у додатне дробове число (напр. «0.75»); інакше None."""
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _parse_nonneg_float(value: str) -> Optional[float]:
    """Розбирає рядок у невід'ємне дробове число; інакше None. На відміну від
    `_parse_positive_float` — для ручної ціни одиниці, де 0 є допустимим
    значенням (TS-53)."""
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _residual_label(pc: MovementProductsCatalog) -> str:
    """Загальний обсяг позиції для колонки «Залишок» — сума ємностей створених
    одиниць (Product.count). Для повністю заповненої позиції дає той самий
    результат, що і count × capacity, але коректно враховує й неповну останню
    одиницю (TS-53); для неподільного — прочерк."""
    if pc.product is None or not pc.product.divisible:
        return "—"
    return format_amount(sum((p.count or 0) for p in pc.products))


def _admission_unit_lines(pc: MovementProductsCatalog) -> List[Tuple[float, float]]:
    """(к-сть, ціна) на КОЖНУ одиницю позиції — для `admission_nds_split` і
    суми рядка (TS-53). Ручна ціна одиниці (`Product.price`) — абсолютна
    (к-сть=1, без пропорції); без ручної ціни — базова ціна позиції: пропорційно
    заповненню для подільного ТМЦ із фіксованою ємністю, інакше повна (за
    фактичну одиницю, як і раніше)."""
    base_price = pc.price
    product = pc.product
    fixed_divisible = bool(
        product is not None
        and product.divisible
        and not product.no_fixed_capacity
        and product.capacity
    )
    units = pc.products or []
    if not units:
        return [(pc.count, base_price)]
    lines: List[Tuple[float, float]] = []
    for unit in units:
        if unit.price is not None:
            lines.append((1.0, unit.price))
        elif fixed_divisible:
            lines.append(((unit.count or 0) / product.capacity, base_price))
        else:
            lines.append((1.0, base_price))
    return lines


def _line_cost(pc: MovementProductsCatalog) -> float:
    return sum(qty * price for qty, price in _admission_unit_lines(pc))


def _qty_label(pc: MovementProductsCatalog) -> str:
    """Колонка «К-сть одиниць»: для подільного з фіксованою ємністю — дробове по
    ємності + фіз. к-сть у дужках (напр. «1.2 (2)»), інакше число фіз. одиниць."""
    product = pc.product
    total_amount = sum((p.count or 0) for p in pc.products)
    return format_transferred_qty(
        total_amount,
        pc.count,
        product.divisible if product is not None else False,
        product.capacity if product is not None else 0,
        product.no_fixed_capacity if product is not None else False,
    )


class MovementProductCatalogAddEditFormState(rx.State):
    item: MovementProductsCatalog = MovementProductsCatalog(
        count=0, price=0.0, id_product_catalog=-1, products=[]
    )

    exclude_products_catalog_list: List[int] = []
    cache_products_catalog_list: List[ProductCatalog] = []

    id_product_catalog_entered: bool = False
    id_product_catalog_in_cache: str = ""
    is_product_uniq: bool = False

    selected_divisible: bool = False
    selected_capacity: float = 0
    # Подільний ТМЦ без фіксованої ємності: ємність одиниці вводиться вручну для
    # кожної позиції постачання (одна на всі одиниці позиції).
    selected_no_fixed_capacity: bool = False
    entered_capacity: str = ""
    # Подільний ТМЦ із фіксованою ємністю: кожна одиниця позиції може бути
    # залита не повністю (TS-53) — «Кількість» лишається загальним числом
    # одиниць, а ємність кожної редагується окремо. Сирі рядки паралельно
    # `item.products` (як `price_input` тримає сиру ціну), щоб float не
    # переформатувався в полі під час набору.
    unit_amounts: List[str] = []
    # Ручна ціна конкретної одиниці (закріплюється за нею, без пропорції);
    # "" — override відсутній, ціна рахується пропорційно від базової.
    unit_prices: List[str] = []
    # Масові поля-дії: пишуть однакове значення в усі `unit_amounts`/
    # `unit_prices` одразу (з подальшою можливістю пооднічного доуточнення).
    bulk_capacity: str = ""
    bulk_price: str = ""
    # Позначка «поза бухгалтерським обліком» (TS-59 п.4): масова `position_excluded`
    # (на всю позицію) + поединична `unit_excluded` (паралельна `item.products`,
    # як `unit_amounts`). Одиниці постачання створюються самим діалогом, тож флаг
    # достатньо проставити на об'єктах Product у `_apply_units`.
    position_excluded: bool = False
    unit_excluded: List[bool] = []

    search_catalog: str = ""

    filter_category: str = ""

    price_input: str = "0"

    error_count: bool = False
    error_price: bool = False
    error_capacity: bool = False

    # Список категорій для фільтра діалогу (формат (назва, id)). Раніше був
    # @rx.var без реактивних залежностей → Reflex кешував його одноразово, і
    # створена «на льоту» категорія не з'являлась у фільтрі (TS-59 п.5). Тепер —
    # звичайне поле, яке перечитуємо при відкритті діалогу і після створення категорії.
    filter_category_options: List[Tuple[str, str]] = []

    def _load_filter_category_options(self):
        self.filter_category_options = [
            (label, cid) for cid, label in ProductCategoryDAO.get_hierarchy_options()
        ]

    @rx.var
    def category_chosen(self) -> bool:
        return self.filter_category != ""

    @rx.var
    def selected_capacity_label(self) -> str:
        return format_amount(self.selected_capacity)

    @rx.var
    def products_catalog_list(self) -> List[Tuple[str, str]]:
        self.cache_products_catalog_list = ProductCatalogDAO.get_all_exclude_ids(
            self.exclude_products_catalog_list
        )
        if self.filter_category == "":
            return []
        allowed_category_ids = set(
            str(i) for i in ProductCategoryDAO.get_self_and_children_ids(int(self.filter_category))
        )
        term = self.search_catalog.strip().lower()
        return sorted(
            (
                (catalog.title, str(catalog.id))
                for catalog in self.cache_products_catalog_list
                if str(catalog.id_category) in allowed_category_ids
                and (term == "" or term in catalog.title.lower())
            ),
            key=lambda option: option[0].lower(),
        )

    @rx.var
    def item_products_list(self) -> List[Tuple[int, Product]]:
        return [(index, product) for index, product in enumerate(self.item.products)]

    @rx.var
    def unit_rows(self) -> List[Tuple[int, str, bool, str, bool, bool]]:
        """(індекс, ємність, помилка ємності, ціна, помилка ціни, поза обліком) —
        для акордеону «Одиниці» (лише подільний ТМЦ із фіксованою ємністю,
        TS-53). `unit_amounts`/`unit_prices`/`unit_excluded` завжди однакової
        довжини — підтримується `_sync_unit_rows`."""
        if not self._units_editable():
            return []
        prices = self.unit_prices
        excluded = self.unit_excluded
        return [
            (
                i,
                amount,
                amount.strip() != "" and self._parse_unit_amount(amount) is None,
                prices[i] if i < len(prices) else "",
                (prices[i].strip() != "" and self._parse_unit_price(prices[i]) is None)
                if i < len(prices)
                else False,
                excluded[i] if i < len(excluded) else False,
            )
            for i, amount in enumerate(self.unit_amounts)
        ]

    @rx.var
    def has_errors(self) -> bool:
        return (
            self.error_count
            or self.error_price
            or self.item.id_product_catalog == -1
            or (
                self.selected_no_fixed_capacity
                and _parse_positive_float(self.entered_capacity) is None
            )
            or (
                self._units_editable()
                and any(
                    a.strip() != "" and self._parse_unit_amount(a) is None
                    for a in self.unit_amounts
                )
            )
            or (
                self._units_editable()
                and any(
                    p.strip() != "" and self._parse_unit_price(p) is None
                    for p in self.unit_prices
                )
            )
        )

    @rx.var
    def product_is_uniq(self) -> bool:
        return self.is_product_uniq

    def _load_products_catalog_list(self):
        self.cache_products_catalog_list = ProductCatalogDAO.get_all_exclude_ids(
            self.exclude_products_catalog_list
        )

    def set_exclude_products_catalog_list(self, exclude_list: List[int]):
        self.exclude_products_catalog_list = exclude_list
        self._load_products_catalog_list()

    def __check_count_correct(self):
        if self.item.count <= 0:
            self.error_count = True
        else:
            self.error_count = False

    def __check_price_correct(self):
        if self.item.price < 0:
            self.error_price = True
        else:
            self.error_price = False

    @rx.var
    def id_product_catalog(self) -> str:
        return self.id_product_catalog_in_cache

    @rx.var
    def count(self) -> str:
        return str(self.item.count)

    @rx.var
    def price(self) -> str:
        return self.price_input

    def _full_unit_count(self) -> float:
        """Ємність ПОВНОЇ одиниці позиції (значення за замовчуванням, поки
        конкретну одиницю не зроблено неповною — див. `_apply_units`)."""
        if self.selected_divisible and self.selected_no_fixed_capacity:
            parsed = _parse_positive_float(self.entered_capacity)
            return parsed if parsed is not None else 0
        if self.selected_divisible and self.selected_capacity > 0:
            return self.selected_capacity
        return 1

    def _units_editable(self) -> bool:
        """Пооднічне редагування ємності/ціни стосується лише подільного ТМЦ
        із фіксованою ємністю (TS-53) — не no_fixed (там ємність і так ручна,
        одна на всю позицію) і не неподільного."""
        return (
            self.selected_divisible
            and not self.selected_no_fixed_capacity
            and self.selected_capacity > 0
        )

    def _parse_unit_amount(self, value: str) -> Optional[float]:
        if not self._units_editable():
            return None
        parsed = _parse_positive_float(value)
        if parsed is None or parsed > self.selected_capacity:
            return None
        return parsed

    def _parse_unit_price(self, value: str) -> Optional[float]:
        """Розбирає ручну ціну одиниці (override). Порожнє чи невірне
        значення — None (override відсутній, ціна рахується пропорційно)."""
        if not self._units_editable():
            return None
        return _parse_nonneg_float(value)

    def _sync_unit_rows(self):
        """Приводить довжину `unit_amounts`/`unit_prices`/`unit_excluded` до к-сті
        одиниць позиції — нові одиниці за замовчуванням повні, без ручної ціни,
        а позначку обліку успадковують від масової (`position_excluded`)."""
        full_label = format_amount(self._full_unit_count())
        target_len = len(self.item.products)
        amounts = list(self.unit_amounts[:target_len])
        amounts += [full_label] * (target_len - len(amounts))
        self.unit_amounts = amounts
        prices = list(self.unit_prices[:target_len])
        prices += [""] * (target_len - len(prices))
        self.unit_prices = prices
        excluded = list(self.unit_excluded[:target_len])
        excluded += [self.position_excluded] * (target_len - len(excluded))
        self.unit_excluded = excluded

    def _apply_units(self):
        """Єдина точка запису Product.count/Product.price по всіх одиницях
        позиції (TS-53). no_fixed — усі одиниці отримують введену вручну
        ємність позиції, override ціни не підтримується; подільний із
        фіксованою ємністю — кожна одиниця за власними `unit_amounts[i]`/
        `unit_prices[i]` (порожнє/невірне — повна ємність / без override);
        неподільний — count=1, без override ціни."""
        units = self.item.products
        # Позначка «поза обліком» — незалежна від count/price, тож виставляємо її
        # одним проходом для всіх гілок нижче (поединична `unit_excluded`, а де її
        # ще немає — масова `position_excluded`).
        for i, unit in enumerate(units):
            unit.excluded_from_accounting = (
                self.unit_excluded[i]
                if i < len(self.unit_excluded)
                else self.position_excluded
            )
        if self.selected_divisible and self.selected_no_fixed_capacity:
            full = self._full_unit_count()
            for unit in units:
                unit.count = full
                unit.price = None
            return
        if self._units_editable():
            full = self._full_unit_count()
            for i, unit in enumerate(units):
                amount = self._parse_unit_amount(self.unit_amounts[i]) if i < len(self.unit_amounts) else None
                unit.count = amount if amount is not None else full
                price_text = self.unit_prices[i] if i < len(self.unit_prices) else ""
                unit.price = self._parse_unit_price(price_text)
            return
        for unit in units:
            unit.count = 1
            unit.price = None

    @rx.event
    def on_change_entered_capacity(self, value: str):
        self.entered_capacity = value
        self.error_capacity = _parse_positive_float(value) is None
        self._apply_units()

    @rx.event
    def on_change_unit_amount(self, index: int, value: str):
        if index < 0 or index >= len(self.unit_amounts):
            return
        amounts = list(self.unit_amounts)
        amounts[index] = value
        self.unit_amounts = amounts
        self._apply_units()

    @rx.event
    def on_change_unit_price(self, index: int, value: str):
        if index < 0 or index >= len(self.unit_prices):
            return
        prices = list(self.unit_prices)
        prices[index] = value
        self.unit_prices = prices
        self._apply_units()

    @rx.event
    def on_change_bulk_capacity(self, value: str):
        """Задає введене значення одразу всім `unit_amounts` (порожнє —
        скидає до повної ємності по кожній одиниці); подальше пооднічне
        доуточнення (`on_change_unit_amount`) лишається доступним."""
        self.bulk_capacity = value
        self.unit_amounts = [value] * len(self.unit_amounts)
        self._apply_units()

    @rx.event
    def on_change_bulk_price(self, value: str):
        """Задає введену ціну одразу всім одиницям (порожнє — знімає override
        з усіх, повертає пропорційний розрахунок)."""
        self.bulk_price = value
        self.unit_prices = [value] * len(self.unit_prices)
        self._apply_units()

    @rx.event
    def on_change_position_excluded(self, value: bool):
        """Масова позначка «поза обліком» — пише однакове значення в усі одиниці
        позиції (поединичне доуточнення лишається доступним)."""
        self.position_excluded = value
        self.unit_excluded = [value] * len(self.item.products)
        self._apply_units()

    @rx.event
    def on_change_unit_excluded(self, index: int, value: bool):
        if index < 0 or index >= len(self.item.products):
            return
        excluded = list(self.unit_excluded)
        # Вирівнюємо довжину до к-сті одиниць (нові — за масовою позначкою).
        while len(excluded) < len(self.item.products):
            excluded.append(self.position_excluded)
        excluded[index] = value
        self.unit_excluded = excluded
        self._apply_units()

    @rx.event
    def on_change_search_catalog(self, value: str):
        self.search_catalog = value

    def _reset_catalog_selection(self):
        self.item.product = None
        self.item.id_product_catalog = -1
        self.item.products = []
        self.item.count = 0
        self.id_product_catalog_in_cache = ""
        self.search_catalog = ""
        self.is_product_uniq = False
        self.selected_divisible = False
        self.selected_capacity = 0
        self.selected_no_fixed_capacity = False
        self.entered_capacity = ""
        self.error_capacity = False
        self.unit_amounts = []
        self.unit_prices = []
        self.bulk_capacity = ""
        self.bulk_price = ""
        self.unit_excluded = []
        self.position_excluded = False

    @rx.event
    def on_change_filter_category(self, value: str):
        if value == self.filter_category:
            return
        self.filter_category = value
        self._reset_catalog_selection()

    @rx.event
    def on_change_id_product_catalog(self, value: str):
        self.id_product_catalog_in_cache = value
        selected = next(
            (c for c in self.cache_products_catalog_list if str(c.id) == value),
            None,
        )
        if selected is None:
            return
        self.item.product = selected
        self.item.id_product_catalog = self.item.product.id
        self.selected_divisible = selected.divisible
        self.selected_capacity = selected.capacity or 0
        self.selected_no_fixed_capacity = bool(selected.no_fixed_capacity)
        self.entered_capacity = ""
        self.error_capacity = False
        self.unit_amounts = []
        self.unit_prices = []
        self.bulk_capacity = ""
        self.bulk_price = ""
        self.unit_excluded = []
        self.position_excluded = False
        if self.is_product_uniq and not self.item.product.uniq:
            for i in range(self.item.count):
                self.item.products[i].serial_number = ""
        for unit in self.item.products:
            unit.id_product_catalog = self.item.product.id
        self._sync_unit_rows()
        self._apply_units()
        self.is_product_uniq = self.item.product.uniq

    @rx.event
    def on_change_count(self, value: str):
        if self.item.product is None:
            return
        try:
            self.item.count = int(value)
        except ValueError:
            self.error_count = True
            return

        self.__check_count_correct()
        if self.error_count:
            self.is_product_uniq = False
            return
        self.is_product_uniq = self.item.product.uniq

        list_len = len(self.item.products)
        if int(value) < list_len:
            self.item.products = self.item.products[: int(value)]
            self._sync_unit_rows()
            self._apply_units()
            return

        full = self._full_unit_count()
        for _ in range(int(value) - list_len):
            self.item.products.append(
                Product(
                    id_product_catalog=self.item.id_product_catalog,
                    id_storage=-1,
                    id_owner=-1,
                    serial_number="",
                    count=full,
                )
            )
        self._sync_unit_rows()
        self._apply_units()

    @rx.event
    def on_change_serial_numbers(self, index: int, value: str):
        if index < len(self.item.products):
            self.item.products[index].serial_number = value

    serial_mask: str = ""
    serial_range_from: str = "1"
    serial_range_to: str = "1"
    serial_range_hex: bool = False

    @rx.event
    def on_change_serial_mask(self, value: str):
        self.serial_mask = value

    @rx.event
    def on_change_serial_range_from(self, value: str):
        self.serial_range_from = value

    @rx.event
    def on_change_serial_range_to(self, value: str):
        self.serial_range_to = value

    @rx.event
    def on_change_serial_range_hex(self, value: bool):
        self.serial_range_hex = value

    @rx.event
    def fill_serial_range(self):
        empty_indexes = [
            i for i, p in enumerate(self.item.products) if not p.serial_number
        ]
        if not empty_indexes:
            return rx.toast.error("Усі серійні номери вже заповнені!")
        values, error = generate_serial_range(
            self.serial_mask, self.serial_range_from, self.serial_range_to,
            len(empty_indexes), self.serial_range_hex,
        )
        if error is not None:
            return rx.toast.error(error)
        products = list(self.item.products)
        for i, value in zip(empty_indexes, values):
            products[i].serial_number = value
        self.item.products = products
        self.serial_mask = ""

    @rx.event
    def on_change_price(self, value: str):
        self.price_input = value
        if value.strip() == "":
            self.item.price = 0.0
            self.error_price = False
            return
        try:
            self.item.price = float(value)
        except ValueError:
            self.error_price = True
            return

        self.__check_price_correct()

    @rx.event
    def set_item(self, item: MovementProductsCatalog):
        self.item = item

        self.is_product_uniq = item.product.uniq
        self.selected_divisible = item.product.divisible if item.product else False
        self.selected_capacity = (
            (item.product.capacity or 0) if item.product else 0
        )
        self.selected_no_fixed_capacity = (
            bool(item.product.no_fixed_capacity) if item.product else False
        )
        # Усі одиниці позиції мають однакову введену ємність — відновлюємо з першої.
        self.entered_capacity = (
            format_amount(item.products[0].count)
            if self.selected_no_fixed_capacity and item.products
            else ""
        )
        self.error_capacity = False
        # Відновлюємо введені ємності й закріплені ціни кожної одиниці позиції
        # (TS-53) — за `selected_*`, уже виставленими вище.
        self.unit_amounts = (
            [format_amount(p.count) for p in item.products]
            if self._units_editable()
            else []
        )
        self.unit_prices = (
            [format_amount(p.price) if p.price is not None else "" for p in item.products]
            if self._units_editable()
            else []
        )
        self.bulk_capacity = ""
        self.bulk_price = ""
        # Відновлюємо позначку «поза обліком» кожної одиниці; масова — «увімкнена»,
        # коли всі одиниці позначені.
        self.unit_excluded = [bool(p.excluded_from_accounting) for p in item.products]
        self.position_excluded = bool(
            item.products and all(p.excluded_from_accounting for p in item.products)
        )
        self.id_product_catalog_entered = True
        self.id_product_catalog_in_cache = (
            str(item.product.id) if item.product is not None else ""
        )
        self.filter_category = (
            str(item.product.id_category)
            if item.product is not None and item.product.id_category is not None
            else ""
        )
        self.search_catalog = ""
        self.price_input = str(item.price)
        self._load_filter_category_options()

    @rx.event
    def clear(self):
        self.item = MovementProductsCatalog(
            count=0, price=0.0, id_product_catalog=-1, products=[]
        )

        self.is_product_uniq = False
        self.selected_divisible = False
        self.selected_capacity = 0
        self.selected_no_fixed_capacity = False
        self.entered_capacity = ""
        self.error_capacity = False
        self.unit_amounts = []
        self.unit_prices = []
        self.bulk_capacity = ""
        self.bulk_price = ""
        self.unit_excluded = []
        self.position_excluded = False
        self.id_product_catalog_entered = False
        self.id_product_catalog_in_cache = ""
        self.search_catalog = ""
        self.filter_category = ""
        self.price_input = "0"
        self.error_count = False
        self.error_price = False
        self._load_filter_category_options()
        self._reset_new_product()
        self.is_create_open = False

    is_create_open: bool = False
    list_categories: List[Tuple[str, str]] = []
    units_cache: List[str] = []
    new_title: str = ""
    new_description: str = ""
    new_id_category: str = ""
    new_unit: str = ""
    new_divisible: bool = False
    new_uniq: bool = False
    new_capacity: str = "0"
    new_no_fixed_capacity: bool = False

    is_duplicate_confirm_open: bool = False
    duplicate_product_id: int = -1
    duplicate_product_category_id: str = ""
    duplicate_product_title: str = ""

    def _reset_new_product(self):
        self.new_title = ""
        self.new_description = ""
        self.new_id_category = ""
        self.new_unit = ""
        self.new_divisible = False
        self.new_uniq = False
        self.new_capacity = "0"
        self.new_no_fixed_capacity = False
        self.is_duplicate_confirm_open = False
        self.duplicate_product_id = -1
        self.duplicate_product_category_id = ""
        self.duplicate_product_title = ""

    @rx.event
    def open_create_product(self):
        self.list_categories = ProductCategoryDAO.get_hierarchy_options()
        self.units_cache = ProductCatalogDAO.get_list_units()
        self._reset_new_product()
        if self.filter_category != "":
            self.new_id_category = self.filter_category
        self.is_create_open = True

    @rx.event
    def set_create_open(self, value: bool):
        self.is_create_open = value

    @rx.event
    def on_change_new_title(self, value: str):
        self.new_title = value

    @rx.event
    def on_change_new_description(self, value: str):
        self.new_description = value

    @rx.event
    def on_change_new_category(self, value: str):
        self.new_id_category = value

    @rx.event
    def on_change_new_unit(self, value: str):
        self.new_unit = value

    @rx.event
    def on_change_new_capacity(self, value: str):
        if self.new_uniq or self.new_no_fixed_capacity:
            return
        self.new_capacity = value

    @rx.event
    def on_change_new_uniq(self, value: bool):
        self.new_uniq = value
        if value:
            self.new_divisible = False
            self.new_capacity = "1"
            self.new_no_fixed_capacity = False

    @rx.event
    def on_change_new_divisible(self, value: bool):
        if self.new_uniq:
            self.new_divisible = False
            return
        self.new_divisible = value
        # «Без фіксованої ємності» має сенс лише для подільного ТМЦ.
        if not value:
            self.new_no_fixed_capacity = False

    @rx.event
    def on_change_new_no_fixed_capacity(self, value: bool):
        # Тумблер доступний лише для подільного неунікального ТМЦ.
        if self.new_uniq or not self.new_divisible:
            self.new_no_fixed_capacity = False
            return
        self.new_no_fixed_capacity = value
        if value:
            self.new_capacity = "0"

    def _select_catalog_in_line(self, catalog_id: int, category_id: str):
        self._load_products_catalog_list()
        self.search_catalog = ""
        self.filter_category = category_id
        for catalog in self.cache_products_catalog_list:
            if catalog.id == catalog_id:
                self.id_product_catalog_in_cache = str(catalog.id)
                self.item.product = catalog
                self.item.id_product_catalog = catalog.id
                self.is_product_uniq = catalog.uniq
                self.selected_divisible = catalog.divisible
                self.selected_capacity = catalog.capacity or 0
                self.selected_no_fixed_capacity = bool(catalog.no_fixed_capacity)
                self.entered_capacity = ""
                self.error_capacity = False
                self.unit_amounts = []
                self.unit_prices = []
                self.bulk_capacity = ""
                self.bulk_price = ""
                self.unit_excluded = []
                self.position_excluded = False
                for unit in self.item.products:
                    unit.id_product_catalog = catalog.id
                self._sync_unit_rows()
                self._apply_units()
                break

    @rx.event
    async def create_product(self):
        if not (await self.get_state(AppState)).has_permission(Action.PRODUCTS_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        title = self.new_title.strip()
        if title == "":
            return rx.toast.error("Вкажіть назву товару!")
        if self.new_id_category == "":
            return rx.toast.error("Оберіть категорію товару!")
        if self.new_uniq and self.new_divisible:
            return rx.toast.error("Товар із серійним номером не може бути подільним!")
        if (
            self.new_divisible
            and not self.new_no_fixed_capacity
            and _parse_positive_float(self.new_capacity) is None
        ):
            return rx.toast.error("Для подільного ТМЦ потрібно вказати додатну місткість!")

        unit = self.new_unit.strip()
        existing = ProductCatalogDAO.get_by_title_and_unit(title, unit)
        if existing is not None:
            self.duplicate_product_id = existing.id
            self.duplicate_product_category_id = (
                str(existing.id_category) if existing.id_category is not None else ""
            )
            self.duplicate_product_title = f"{existing.title} ({existing.unit})"
            self.is_duplicate_confirm_open = True
            return

        if self.new_uniq:
            capacity = 1
        elif self.new_no_fixed_capacity:
            capacity = 0
        else:
            capacity = _parse_positive_float(self.new_capacity) or 0
        product = ProductCatalog(
            title=title,
            description=self.new_description.strip() or None,
            id_category=int(self.new_id_category),
            unit=unit,
            divisible=False if self.new_uniq else self.new_divisible,
            uniq=self.new_uniq,
            capacity=capacity,
            no_fixed_capacity=self.new_no_fixed_capacity,
            count=0,
        )
        flag, text, new_id = ProductCatalogDAO.add_one(product)
        if not flag:
            return rx.toast.error(text)

        self._select_catalog_in_line(new_id, str(int(self.new_id_category)))

        self.is_create_open = False
        self._reset_new_product()
        return rx.toast.success("Товар створено та обрано!")

    @rx.event
    def cancel_duplicate_product(self):
        self.is_duplicate_confirm_open = False
        self.duplicate_product_id = -1
        self.duplicate_product_category_id = ""
        self.duplicate_product_title = ""

    @rx.event
    def set_duplicate_confirm_open(self, value: bool):
        if not value:
            self.cancel_duplicate_product()

    @rx.event
    def confirm_use_duplicate_product(self):
        catalog_id = self.duplicate_product_id
        self._select_catalog_in_line(catalog_id, self.duplicate_product_category_id)

        self.is_duplicate_confirm_open = False
        self.duplicate_product_id = -1
        self.duplicate_product_category_id = ""
        self.duplicate_product_title = ""

        if self.item.id_product_catalog != catalog_id:
            return rx.toast.error("Цей товар вже додано до поставки в іншому рядку!")

        self.is_create_open = False
        self._reset_new_product()
        return rx.toast.success("Обрано наявний товар!")

    is_create_category_open: bool = False
    new_category_title: str = ""
    new_category_description: str = ""

    def _reset_new_category(self):
        self.new_category_title = ""
        self.new_category_description = ""

    @rx.event
    def open_create_category(self):
        self._reset_new_category()
        self.is_create_category_open = True

    @rx.event
    def set_create_category_open(self, value: bool):
        self.is_create_category_open = value

    @rx.event
    def on_change_new_category_title(self, value: str):
        self.new_category_title = value

    @rx.event
    def on_change_new_category_description(self, value: str):
        self.new_category_description = value

    @rx.event
    async def create_category(self):
        if not (await self.get_state(AppState)).has_permission(Action.CATEGORIES_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")

        title = self.new_category_title.strip()
        if title == "":
            return rx.toast.error("Вкажіть назву категорії!")

        category = ProductCategory(
            title=title,
            description=self.new_category_description.strip() or None,
        )
        flag, text, new_id = ProductCategoryDAO.add_one(category)
        if not flag:
            return rx.toast.error(text)

        self.list_categories = ProductCategoryDAO.get_hierarchy_options()
        self._load_filter_category_options()
        self.new_id_category = str(new_id)
        self.is_create_category_open = False
        self._reset_new_category()
        return rx.toast.success("Категорію створено та обрано!")


class MovementProductCatalogDetailedViewState(rx.State):
    item: MovementProductsCatalog = MovementProductsCatalog(
        count=0, price=0.0, id_product_catalog=-1, products=[]
    )

    @rx.var
    def item_products_list(self) -> List[Tuple[int, Product]]:
        return [(index, product) for index, product in enumerate(self.item.products)]

    @rx.var
    def price_display(self) -> str:
        return _format_money(self.item.price)

    @rx.var
    def quantity_label(self) -> str:
        return _qty_label(self.item)

    @rx.event
    def set_item(self, item: MovementProductsCatalog):
        self.item = item

    @rx.event
    def clear(self):
        self.item = MovementProductsCatalog(
            count=0, price=0.0, id_product_catalog=-1, products=[]
        )


class ListAdmissionState(MovementListFilterMixin, AppState):
    items: List[Admission] = []
    in_progress: bool = True

    filter_supplier: str = ALL
    list_suppliers: List[Tuple[str, str]] = []

    def _load_section_filter_options(self):
        self.list_suppliers = [(s.title, str(s.id)) for s in SupplierDAO.get_all()]

    def _reset_section_filter_values(self):
        self.filter_supplier = ALL

    def _reload(self):
        self._all_pages, self.items = AdmissionDAO.get_paginated(
            self._current_page,
            self._limit,
            self._date_from_eff(),
            self._date_to_eff(),
            self.selected_statuses,
            destination_storage=self.filter_destination_storage,
            destination_owner=self.filter_destination_owner,
            supplier=self.filter_supplier,
            catalog_ids=self.selected_catalog_ids,
        )

    @rx.var
    def has_active_filters(self) -> bool:
        return bool(
            self.filter_date_enabled
            or self.selected_statuses
            or self.selected_catalog_ids
            or self.filter_destination_storage != ALL
            or self.filter_destination_owner != ALL
            or self.filter_supplier != ALL
        )

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def get_items(self) -> List[Tuple[int, Admission, str]]:
        return [
            (index, item, _format_money(item.movement.total_cost))
            for index, item in enumerate(self.items)
        ]

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list

    @rx.event
    def on_load(self):
        guard = self.access_guard(Action.ADMISSIONS_LIST)
        if guard is not None:
            yield guard
            return
        self.in_progress = True
        self._enter_list()
        self._reload()
        self.in_progress = False

    @rx.event
    def on_click_add(self):
        return rx.redirect(routes.MOVEMENT_ADMISSIONS_ADD)

    @rx.event
    def on_change_filter_supplier(self, value: str):
        self.filter_supplier = value
        return self._apply_filters()


class AddAdmissionState(LookupCreatorsMixin, AppState):
    class ProductCatalogDialogPages:
        EDIT = "edit"
        VIEW = "view"
        EMPTY = "empty"

    item: Admission = Admission(
        id_payment_type=-1,
        id_supplier=-1,
        flag_nds=False,
        id_nds_rate=None,
        dollar_rate=0.0,
        invoice_number=None,
        movement=Movement(
            id_destination_storage=-1,
            id_destination_owner=-1,
            date=now_local().date().__str__(),
            comment="",
            status=MovementsStatus.CREATED,
            type=MovementsType.ADMISSION,
            total_cost=0.0,
            products_catalog=[],
        ),
    )
    current_product_catalog_index: int = -1

    search_name_destination_storage: str = ""

    list_suppliers: List[Tuple[str, str]] = []
    list_storages: List[Tuple[str, str]] = []
    list_owners: List[Tuple[str, str]] = []
    list_payment_types: List[Tuple[str, str]] = []
    list_nds_rates: List[Tuple[str, str]] = []
    nds_rates_cache: List[Tuple[int, float]] = []

    is_open_product_catalog_dialog: bool = False
    product_catalog_dialog_page: str = ""
    is_product_dialog_view_mode: bool = False

    def _load_suppliers(self):
        self.list_suppliers = [
            (item.title, str(item.id)) for item in SupplierDAO.get_all()
        ]

    def _load_storages(self):
        self.list_storages = [
            (item.title, str(item.id))
            for item in StorageDAO.get_all()
            if item.type == StorageType.WAREHOUSE
            and (
                self.search_name_destination_storage == ""
                or self.search_name_destination_storage.lower() in item.title.lower()
            )
        ]

    def _load_owners(self):
        self.list_owners = [(item.title, str(item.id)) for item in OwnerDAO.get_all()]

    def _load_payment_types(self):
        self.list_payment_types = [
            (item.title, str(item.id)) for item in PaymentTypeDAO.get_all()
        ]

    def _load_nds_rates(self):
        rates = NDSRateDAO.get_all()
        self.list_nds_rates = [(item.title, str(item.id)) for item in rates]
        self.nds_rates_cache = [(item.id, item.rate) for item in rates]

    def _get_nds_rate_value(self) -> float:
        if self.item.id_nds_rate is None:
            return 0.0
        for rid, rate in self.nds_rates_cache:
            if rid == self.item.id_nds_rate:
                return rate
        return 0.0

    def _nds_split(self) -> Tuple[float, float, float]:
        """(база, ПДВ, разом) поточного переліку позицій — спільна формула
        `declared.admission_nds_split`, одна для UI і для серверного перерахунку."""
        lines = [
            line
            for pc in self.item.movement.products_catalog
            for line in _admission_unit_lines(pc)
        ]
        return admission_nds_split(lines, self._get_nds_rate_value(), self.item.flag_nds)

    def _recompute_total(self):
        self.item.movement.total_cost = self._nds_split()[2]

    @rx.event
    def on_load(self):
        guard = self.access_guard(Action.ADMISSIONS_CREATE)
        if guard is not None:
            yield guard
            return

        self.item = Admission(
            id_payment_type=-1,
            id_supplier=-1,
            flag_nds=False,
            id_nds_rate=None,
            dollar_rate=0.0,
            invoice_number=None,
            movement=Movement(
                id_destination_storage=-1,
                id_destination_owner=-1,
                date=now_local().date().__str__(),
                comment="",
                status=MovementsStatus.CREATED,
                type=MovementsType.ADMISSION,
                total_cost=0.0,
                products_catalog=[],
            ),
        )

        self.current_product_catalog_index = -1
        self.search_name_destination_storage = ""
        self.is_open_product_catalog_dialog = False
        self.product_catalog_dialog_page = self.ProductCatalogDialogPages.EMPTY

        self._load_suppliers()
        self._load_storages()
        self._load_owners()
        self._load_payment_types()
        self._load_nds_rates()

        default_storage = StorageDAO.get_default_id(StorageType.WAREHOUSE)
        if default_storage is not None:
            self.item.movement.id_destination_storage = default_storage
        default_owner = OwnerDAO.get_default_id()
        if default_owner is not None:
            self.item.movement.id_destination_owner = default_owner
        default_payment = PaymentTypeDAO.get_default_id()
        if default_payment is not None:
            self.item.id_payment_type = default_payment
        if self.item.id_nds_rate is None:
            default_nds_rate = NDSRateDAO.get_default_id()
            if default_nds_rate is not None:
                self.item.id_nds_rate = default_nds_rate

    @rx.var
    def id_destination_storage(self) -> str:
        return str(self.item.movement.id_destination_storage)

    @rx.var
    def id_destination_owner(self) -> str:
        return str(self.item.movement.id_destination_owner)

    @rx.var
    def id_supplier(self) -> str:
        return str(self.item.id_supplier)

    @rx.var
    def status(self) -> str:
        return movements_status_list[self.item.movement.status]

    @rx.var
    def id_payment_type(self) -> str:
        return str(self.item.id_payment_type)

    @rx.var
    def flag_nds(self) -> str:
        return str(self.item.flag_nds)

    @rx.var
    def dollar_rate(self) -> str:
        return str(self.item.dollar_rate)

    @rx.var
    def id_nds_rate(self) -> str:
        return str(self.item.id_nds_rate) if self.item.id_nds_rate is not None else ""

    @rx.var
    def invoice_number(self) -> str:
        return self.item.invoice_number if self.item.invoice_number is not None else ""

    @rx.var
    def nds_rate_percent(self) -> str:
        return str(self._get_nds_rate_value())

    @rx.var
    def subtotal_display(self) -> str:
        return _format_money(self._nds_split()[0])

    @rx.var
    def nds_amount_display(self) -> str:
        return _format_money(self._nds_split()[1])

    @rx.var
    def total_display(self) -> str:
        return _format_money(self._nds_split()[2])

    @rx.event
    def on_change_search_name_destination_storage(self, value: str):
        self.search_name_destination_storage = value
        self._load_storages()

    @rx.event
    def on_click_search_name_destination_storage(self):
        self._load_storages()

    @rx.event
    def on_change_id_destination_storage(self, value: str):
        self.item.movement.id_destination_storage = int(value)

    @rx.event
    def on_change_id_destination_owner(self, value: str):
        self.item.movement.id_destination_owner = int(value)

    @rx.event
    def on_change_id_supplier(self, value: str):
        self.item.id_supplier = int(value)

    @rx.event
    def on_change_status(self, value: str):
        status = None
        for index, status_text in enumerate(movements_status_list):
            if status_text == value:
                status = index
                break
        if status is not None:
            self.item.movement.status = status

    @rx.event
    def on_change_id_payment_type(self, value: str):
        self.item.id_payment_type = int(value)

    @rx.event
    def on_change_flag_nds(self, value: bool):
        self.item.flag_nds = value
        self._recompute_total()

    @rx.event
    def on_change_id_nds_rate(self, value: str):
        if value == "" or value == "None":
            self.item.id_nds_rate = None
        else:
            try:
                self.item.id_nds_rate = int(value)
            except ValueError:
                self.item.id_nds_rate = None
        self._recompute_total()

    @rx.event
    def on_change_invoice_number(self, value: str):
        self.item.invoice_number = value if value != "" else None

    @rx.event
    def on_change_dollar_rate(self, value: str):
        try:
            self.item.dollar_rate = float(value)
        except ValueError:
            self.item.dollar_rate = 0.0

    @rx.event
    def on_change_date(self, value: str):
        self.item.movement.date = value

    @rx.event
    def on_change_comment(self, value: str):
        self.item.movement.comment = value

    @rx.event
    def on_close_product_catalog_dialog(self):
        self.is_open_product_catalog_dialog = False

    @rx.var
    def item_status(self) -> str:
        return movements_status_list[self.item.movement.status]

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list

    @rx.var
    def editable_statuses(self) -> List[str]:
        return [
            status
            for index, status in enumerate(movements_status_list)
            if index != MovementsStatus.CANCELED
        ]

    @rx.var
    def item_movement_products_catalog_list(
        self,
    ) -> List[Tuple[int, MovementProductsCatalog, str, str, str, str]]:
        return [
            (
                index,
                pc,
                _format_money(pc.price),
                _format_money(_line_cost(pc)),
                _residual_label(pc),
                _qty_label(pc),
            )
            for index, pc in enumerate(self.item.movement.products_catalog)
        ]

    @rx.var
    def has_item_movement_products_catalog(self) -> bool:
        return len(self.item.movement.products_catalog) > 0

    @rx.event
    async def view_product_catalog_dialog(self, index: int):
        view_state = await self.get_state(MovementProductCatalogDetailedViewState)
        self.is_product_dialog_view_mode = True
        self.current_product_catalog_index = index
        view_state.set_item(self.item.movement.products_catalog[index])
        self.product_catalog_dialog_page = self.ProductCatalogDialogPages.VIEW
        self.is_open_product_catalog_dialog = True

    @rx.event
    async def add_product_catalog_dialog_open(self):
        form_state = await self.get_state(MovementProductCatalogAddEditFormState)
        self.is_product_dialog_view_mode = False
        self.current_product_catalog_index = -1
        form_state.clear()
        # ТМЦ без фіксованої ємності можна додати кілька разів (різні партії —
        # різна ємність), тож із дедупу виключаємо лише товари з фіксованою ємністю.
        form_state.set_exclude_products_catalog_list(
            [
                pc.product.id
                for pc in self.item.movement.products_catalog
                if not pc.product.no_fixed_capacity
            ]
        )
        self.product_catalog_dialog_page = self.ProductCatalogDialogPages.EDIT
        self.is_open_product_catalog_dialog = True

    @rx.event
    async def edit_product_catalog_dialog(self):
        form_state = await self.get_state(MovementProductCatalogAddEditFormState)
        self.is_product_dialog_view_mode = False
        form_state.set_item(
            self.item.movement.products_catalog[self.current_product_catalog_index]
        )
        form_state.set_exclude_products_catalog_list([
            pc.product.id
            for i, pc in enumerate(self.item.movement.products_catalog)
            if i != self.current_product_catalog_index and not pc.product.no_fixed_capacity
        ])
        self.product_catalog_dialog_page = self.ProductCatalogDialogPages.EDIT
        self.is_open_product_catalog_dialog = True

    @rx.event
    async def on_save_product_catalog_dialog(self):
        form_state = await self.get_state(MovementProductCatalogAddEditFormState)

        if form_state.has_errors:
            return

        item = form_state.item

        if self.current_product_catalog_index > -1:
            self.item.movement.products_catalog[self.current_product_catalog_index] = (
                item
            )
        else:
            self.item.movement.products_catalog.append(item)

        self._recompute_total()
        self.is_open_product_catalog_dialog = False

    def _after_create_supplier(self, new_id: int):
        self._load_suppliers()
        self.item.id_supplier = new_id

    def _after_create_owner(self, new_id: int):
        self._load_owners()
        self.item.movement.id_destination_owner = new_id

    def _after_create_payment_type(self, new_id: int):
        self._load_payment_types()
        self.item.id_payment_type = new_id

    def _after_create_nds_rate(self, new_id: int):
        self._load_nds_rates()
        self.item.id_nds_rate = new_id
        self._recompute_total()

    def _after_create_storage(self, new_id: int):
        self._load_storages()
        self.item.movement.id_destination_storage = new_id

    async def _reset_for_continue(self):
        m = self.item.movement
        keep = dict(
            date=m.date,
            id_supplier=self.item.id_supplier,
            id_destination_storage=m.id_destination_storage,
            id_destination_owner=m.id_destination_owner,
            id_payment_type=self.item.id_payment_type,
            id_nds_rate=self.item.id_nds_rate,
            flag_nds=self.item.flag_nds,
            dollar_rate=self.item.dollar_rate,
            status=m.status,
        )
        self.item = Admission(
            id_payment_type=keep["id_payment_type"],
            id_supplier=keep["id_supplier"],
            flag_nds=keep["flag_nds"],
            id_nds_rate=keep["id_nds_rate"],
            dollar_rate=keep["dollar_rate"],
            invoice_number=None,
            movement=Movement(
                id_destination_storage=keep["id_destination_storage"],
                id_destination_owner=keep["id_destination_owner"],
                date=keep["date"],
                comment="",
                status=keep["status"],
                type=MovementsType.ADMISSION,
                total_cost=0.0,
                products_catalog=[],
            ),
        )
        self.current_product_catalog_index = -1
        self.is_open_product_catalog_dialog = False
        self.product_catalog_dialog_page = self.ProductCatalogDialogPages.EMPTY

        self._load_suppliers()
        self._load_storages()
        self._load_owners()
        self._load_payment_types()
        self._load_nds_rates()

        form_state = await self.get_state(MovementProductCatalogAddEditFormState)
        form_state.clear()
        self._recompute_total()

    @rx.event
    async def add_one(self, keep: bool = False):
        if not self.has_permission(Action.ADMISSIONS_CREATE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item.movement.id_destination_storage <= 0:
            yield rx.toast.error("Не обрано склад призначення!")
            return
        if self.item.movement.id_destination_owner <= 0:
            yield rx.toast.error("Не обрано власника призначення!")
            return
        if AdmissionDAO.is_invoice_number_exists(self.item.invoice_number):
            yield rx.toast.error("Постачання з таким номером накладної оплати вже існує!")
            return
        self.item.movement.id_user = self.user.login

        for pc in self.item.movement.products_catalog:
            for product in pc.products:
                product.id_storage = self.item.movement.id_destination_storage
                product.id_owner = self.item.movement.id_destination_owner

        flag, text, id = AdmissionDAO.add_one(self.item, self.user.login)
        if not flag:
            yield rx.toast.error(text)
            return
        if keep:
            await self._reset_for_continue()
            yield rx.toast.success(text)
            return
        yield rx.toast.success(text)
        yield ListAdmissionState.on_load()
        yield rx.redirect(f"{routes.MOVEMENT_ADMISSIONS_VIEW_ID}{id}", replace=True)


class EditAdmissionState(FullEditMixin, AppState):
    MOVEMENT_TYPE = MovementsType.ADMISSION

    class ProductCatalogDialogPages:
        EDIT = "edit"
        VIEW = "view"
        EMPTY = "empty"

    item: Optional[Admission] = None
    in_process: bool = True
    current_product_catalog_index: int = -1

    search_name_destination_storage: str = ""

    list_suppliers: List[Tuple[str, str]] = []
    list_storages: List[Tuple[str, str]] = []
    list_owners: List[Tuple[str, str]] = []
    list_payment_types: List[Tuple[str, str]] = []
    list_nds_rates: List[Tuple[str, str]] = []
    nds_rates_cache: List[Tuple[int, float]] = []

    is_open_product_catalog_dialog: bool = False
    product_catalog_dialog_page: str = ""
    is_product_dialog_view_mode: bool = False

    # Позиції, які користувач прибрав із переліку: видаляються при збереженні,
    # а не одразу при кліку (щоб «Скасувати» справді нічого не змінювало).
    removed_line_ids: List[int] = []

    def _load_suppliers(self):
        self.list_suppliers = [
            (item.title, str(item.id)) for item in SupplierDAO.get_all()
        ]

    def _load_storages(self):
        self.list_storages = [
            (item.title, str(item.id))
            for item in StorageDAO.get_all()
            if item.type == StorageType.WAREHOUSE
            and (
                self.search_name_destination_storage == ""
                or self.search_name_destination_storage.lower() in item.title.lower()
            )
        ]

    def _load_owners(self):
        self.list_owners = [(item.title, str(item.id)) for item in OwnerDAO.get_all()]

    def _load_payment_types(self):
        self.list_payment_types = [
            (item.title, str(item.id)) for item in PaymentTypeDAO.get_all()
        ]

    def _load_nds_rates(self):
        rates = NDSRateDAO.get_all()
        self.list_nds_rates = [(item.title, str(item.id)) for item in rates]
        self.nds_rates_cache = [(item.id, item.rate) for item in rates]

    def _get_nds_rate_value(self) -> float:
        if self.item is None or self.item.id_nds_rate is None:
            return 0.0
        for rid, rate in self.nds_rates_cache:
            if rid == self.item.id_nds_rate:
                return rate
        return 0.0

    def _nds_split(self) -> Tuple[float, float, float]:
        """(база, ПДВ, разом) поточного переліку позицій — спільна формула
        `declared.admission_nds_split`, одна для UI і для серверного перерахунку."""
        if self.item is None:
            return 0.0, 0.0, 0.0
        lines = [
            line
            for pc in self.item.movement.products_catalog
            for line in _admission_unit_lines(pc)
        ]
        return admission_nds_split(lines, self._get_nds_rate_value(), self.item.flag_nds)

    def _recompute_total(self):
        if self.item is None:
            return
        self.item.movement.total_cost = self._nds_split()[2]

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        guard = self.access_guard(Action.ADMISSIONS_EDIT)
        if guard is not None:
            yield guard
            return

        self.in_process = True
        self.search_name_destination_storage = ""
        self.is_open_product_catalog_dialog = False
        self.product_catalog_dialog_page = self.ProductCatalogDialogPages.EMPTY
        self.current_product_catalog_index = -1

        self._load_suppliers()
        self._load_storages()
        self._load_owners()
        self._load_payment_types()
        self._load_nds_rates()

        self.item = AdmissionDAO.get_by_id_with_all_relationship(int(id))
        if self.item is None:
            self.in_process = False
            yield rx.redirect(routes.MOVEMENT_ADMISSIONS)
            yield rx.toast.error("Запис не знайдено!")
            return

        # Гвард повного редагування (право + вікно + відсутність пізніших рухів)
        # спільний для всіх операцій — див. FullEditMixin/MovementEditService.
        self._load_editability(self.item.id)
        self.removed_line_ids = []
        self.in_process = False

    @rx.var
    def id_destination_storage(self) -> str:
        return str(self.item.movement.id_destination_storage) if self.item is not None else ""

    @rx.var
    def id_destination_owner(self) -> str:
        return str(self.item.movement.id_destination_owner) if self.item is not None else ""

    @rx.var
    def id_supplier(self) -> str:
        return str(self.item.id_supplier) if self.item is not None else ""

    @rx.var
    def status(self) -> str:
        return movements_status_list[self.item.movement.status] if self.item is not None else ""

    @rx.var
    def id_payment_type(self) -> str:
        return str(self.item.id_payment_type) if self.item is not None else ""

    @rx.var
    def flag_nds(self) -> str:
        return str(self.item.flag_nds) if self.item is not None else "False"

    @rx.var
    def dollar_rate(self) -> str:
        return str(self.item.dollar_rate) if self.item is not None else "0.0"

    @rx.var
    def id_nds_rate(self) -> str:
        if self.item is None or self.item.id_nds_rate is None:
            return ""
        return str(self.item.id_nds_rate)

    @rx.var
    def invoice_number(self) -> str:
        if self.item is None or self.item.invoice_number is None:
            return ""
        return self.item.invoice_number

    @rx.var
    def nds_rate_percent(self) -> str:
        return str(self._get_nds_rate_value())

    @rx.var
    def subtotal_display(self) -> str:
        return _format_money(self._nds_split()[0])

    @rx.var
    def nds_amount_display(self) -> str:
        return _format_money(self._nds_split()[1])

    @rx.var
    def total_display(self) -> str:
        return _format_money(self._nds_split()[2])

    @rx.var
    def item_status(self) -> str:
        return movements_status_list[self.item.movement.status] if self.item is not None else ""

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list

    @rx.var
    def item_movement_products_catalog_list(
        self,
    ) -> List[Tuple[int, MovementProductsCatalog, str, str, str, str]]:
        if self.item is None:
            return []
        return [
            (
                index,
                pc,
                _format_money(pc.price),
                _format_money(_line_cost(pc)),
                _residual_label(pc),
                _qty_label(pc),
            )
            for index, pc in enumerate(self.item.movement.products_catalog)
        ]

    @rx.var
    def has_item_movement_products_catalog(self) -> bool:
        return self.item is not None and len(self.item.movement.products_catalog) > 0

    @rx.event
    def on_change_search_name_destination_storage(self, value: str):
        self.search_name_destination_storage = value
        self._load_storages()

    @rx.event
    def on_click_search_name_destination_storage(self):
        self._load_storages()

    @rx.event
    def on_change_id_destination_storage(self, value: str):
        if self.item is not None and self.can_edit_full and value.lstrip("-").isdigit():
            self.item.movement.id_destination_storage = int(value)

    @rx.event
    def on_change_id_destination_owner(self, value: str):
        if self.item is not None and self.can_edit_full and value.lstrip("-").isdigit():
            self.item.movement.id_destination_owner = int(value)

    @rx.event
    def on_change_id_supplier(self, value: str):
        if self.item is not None and self.can_edit_full and value.lstrip("-").isdigit():
            self.item.id_supplier = int(value)

    @rx.event
    def on_change_status(self, value: str):
        if self.item is None:
            return
        for index, status_text in enumerate(movements_status_list):
            if status_text == value:
                self.item.movement.status = index
                return

    @rx.var
    def editable_statuses(self) -> List[str]:
        """Без «Скасовано» — скасування руху виконується окремою дією, що
        компенсує залишки, а не зміною статусу у формі."""
        return [
            status
            for index, status in enumerate(movements_status_list)
            if index != MovementsStatus.CANCELED
        ]

    @rx.event
    def on_change_id_payment_type(self, value: str):
        if self.item is not None and self.can_edit_full and value.lstrip("-").isdigit():
            self.item.id_payment_type = int(value)

    @rx.event
    def on_change_flag_nds(self, value: bool):
        if self.item is None or not self.can_edit_full:
            return
        self.item.flag_nds = value
        self._recompute_total()

    @rx.event
    def on_change_id_nds_rate(self, value: str):
        if self.item is None:
            return
        if value == "" or value == "None":
            self.item.id_nds_rate = None
        else:
            try:
                self.item.id_nds_rate = int(value)
            except ValueError:
                self.item.id_nds_rate = None
        self._recompute_total()

    @rx.event
    def on_change_invoice_number(self, value: str):
        if self.item is None:
            return
        self.item.invoice_number = value if value != "" else None

    @rx.event
    def on_change_dollar_rate(self, value: str):
        if self.item is None or not self.can_edit_full:
            return
        try:
            self.item.dollar_rate = float(value)
        except ValueError:
            self.item.dollar_rate = 0.0

    @rx.event
    def on_change_date(self, value: str):
        if self.item is not None and self.can_edit_full:
            self.item.movement.date = value

    @rx.event
    def on_change_comment(self, value: str):
        if self.item is not None:
            self.item.movement.comment = value

    @rx.event
    async def view_product_catalog_dialog(self, index: int):
        if self.item is None:
            return
        view_state = await self.get_state(MovementProductCatalogDetailedViewState)
        self.is_product_dialog_view_mode = True
        self.current_product_catalog_index = index
        view_state.set_item(self.item.movement.products_catalog[index])
        self.product_catalog_dialog_page = self.ProductCatalogDialogPages.VIEW
        self.is_open_product_catalog_dialog = True

    @rx.event
    async def add_product_catalog_dialog_open(self):
        if self.item is None or not self.can_edit_full:
            return
        form_state = await self.get_state(MovementProductCatalogAddEditFormState)
        self.is_product_dialog_view_mode = False
        self.current_product_catalog_index = -1
        form_state.clear()
        # ТМЦ без фіксованої ємності можна додати кілька разів (різні партії —
        # різна ємність), тож із дедупу виключаємо лише товари з фіксованою ємністю.
        form_state.set_exclude_products_catalog_list(
            [
                pc.product.id
                for pc in self.item.movement.products_catalog
                if not pc.product.no_fixed_capacity
            ]
        )
        self.product_catalog_dialog_page = self.ProductCatalogDialogPages.EDIT
        self.is_open_product_catalog_dialog = True

    @rx.event
    async def edit_product_catalog_dialog(self):
        if self.item is None or not self.can_edit_full:
            return
        form_state = await self.get_state(MovementProductCatalogAddEditFormState)
        self.is_product_dialog_view_mode = False
        form_state.set_item(
            self.item.movement.products_catalog[self.current_product_catalog_index]
        )
        form_state.set_exclude_products_catalog_list([
            pc.product.id
            for i, pc in enumerate(self.item.movement.products_catalog)
            if i != self.current_product_catalog_index and not pc.product.no_fixed_capacity
        ])
        self.product_catalog_dialog_page = self.ProductCatalogDialogPages.EDIT
        self.is_open_product_catalog_dialog = True

    @rx.event
    async def edit_product_catalog_dialog_from_row(self, index: int):
        self.current_product_catalog_index = index
        await self.edit_product_catalog_dialog()

    @rx.event
    async def on_save_product_catalog_dialog(self):
        if self.item is None or not self.can_edit_full:
            return
        form_state = await self.get_state(MovementProductCatalogAddEditFormState)
        if form_state.has_errors:
            return

        item = form_state.item

        if self.current_product_catalog_index > -1:
            self.item.movement.products_catalog[self.current_product_catalog_index] = item
        else:
            self.item.movement.products_catalog.append(item)

        self._recompute_total()
        self.is_open_product_catalog_dialog = False

    @rx.event
    def on_close_product_catalog_dialog(self):
        self.is_open_product_catalog_dialog = False

    @rx.event
    def delete_product_catalog_row(self, index: int):
        if self.item is None or not self.can_edit_full:
            return rx.toast.error("У Вас немає дозволу на редагування переліку ТМЦ!")
        if index < 0 or index >= len(self.item.movement.products_catalog):
            return
        pc = self.item.movement.products_catalog[index]
        if pc.id is not None and pc.id > 0:
            self.removed_line_ids.append(pc.id)
        del self.item.movement.products_catalog[index]
        self._recompute_total()
        return rx.toast.info("Позицію прибрано з переліку — збережіть, щоб застосувати.")

    @rx.event
    def edit_one(self):
        if not self.has_permission(Action.ADMISSIONS_EDIT):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None:
            yield rx.toast.error("Запис не завантажено!")
            return
        if self.item.movement.id_destination_storage <= 0:
            yield rx.toast.error("Не обрано склад призначення!")
            return
        if self.item.movement.id_destination_owner <= 0:
            yield rx.toast.error("Не обрано власника призначення!")
            return
        if AdmissionDAO.is_invoice_number_exists(self.item.invoice_number, exclude_id=self.item.id):
            yield rx.toast.error("Постачання з таким номером накладної оплати вже існує!")
            return
        self.item.movement.id_user = self.user.login

        for pc in self.item.movement.products_catalog:
            for product in pc.products:
                product.id_storage = self.item.movement.id_destination_storage
                product.id_owner = self.item.movement.id_destination_owner

        flag, text, id = AdmissionDAO.edit_one(
            self.item,
            self.user.login,
            reason=self.edit_reason,
            removed_line_ids=list(self.removed_line_ids),
        )
        if flag:
            self.removed_line_ids = []
            yield rx.toast.success(text)
            yield ListAdmissionState.on_load()
            yield rx.redirect(f"{routes.MOVEMENT_ADMISSIONS_VIEW_ID}{id}", replace=True)
            return
        yield rx.toast.error(text)


class ViewAdmissionState(CancelWithReasonMixin, AuditHistoryMixin, AppState):
    HISTORY_TABLE = "admissions"
    HISTORY_ACTION = Action.ADMISSIONS_HISTORY
    HISTORY_DETAIL_ACTION = Action.ADMISSIONS_HISTORY_DETAIL
    # Скасування постачання — це видалення непроведеного запису (він сам
    # породив одиниці), а не зміна статусу на «Скасовано».
    CANCEL_EVENT_NAME = "on_click_delete"

    item: Admission = Admission(
        id_payment_type=-1,
        id_supplier=-1,
        flag_nds=False,
        id_nds_rate=None,
        dollar_rate=0.0,
        invoice_number=None,
        movement=Movement(
            id_destination_storage=-1,
            id_destination_owner=-1,
            date=now_local().date().__str__(),
            comment="",
            status=MovementsStatus.CREATED,
            type=MovementsType.ADMISSION,
            total_cost=0.0,
            products_catalog=[],
        ),
    )
    in_process: bool = True

    dialog_open: bool = False
    current_product_catalog_index: int = -1

    cancel_conflict_movements: List[Movement] = []
    is_cancel_conflict_dialog_open: bool = False

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        guard = self.access_guard(Action.ADMISSIONS_VIEW)
        if guard is not None:
            yield guard
            return
        self.in_process = True
        item = AdmissionDAO.get_by_id_with_all_relationship(int(id))
        if item is None:
            self.in_process = False
            yield rx.redirect(routes.MOVEMENT_ADMISSIONS)
            yield rx.toast.error("Запис не знайдено!")
            return
        self.item = item
        self.dialog_open = False
        self.current_product_catalog_index = -1
        self._load_history(self.item.id)
        self.in_process = False

    @rx.event
    def on_click_edit(self):
        if self.item is None:
            return
        return rx.redirect(routes.MOVEMENT_ADMISSIONS_EDIT_ID + str(self.item.id))

    @rx.var
    def cancel_conflict_rows(self) -> List[Tuple[str, str, str, str, str]]:
        return [
            (
                str(m.id),
                movements_type_list.get(m.type, "—"),
                m.date,
                movements_status_list[m.status],
                routes.movement_view_url(m.type, m.id),
            )
            for m in self.cancel_conflict_movements
        ]

    @rx.event
    def set_cancel_conflict_dialog_open(self, value: bool):
        self.is_cancel_conflict_dialog_open = value

    @rx.var
    def item_status(self) -> str:
        return movements_status_list[self.item.movement.status]

    @rx.var
    def item_movement_products_catalog_list(
        self,
    ) -> List[Tuple[int, MovementProductsCatalog, str, str, str, str]]:
        return [
            (
                index,
                pc,
                _format_money(pc.price),
                _format_money(_line_cost(pc)),
                _residual_label(pc),
                _qty_label(pc),
            )
            for index, pc in enumerate(self.item.movement.products_catalog)
        ]

    @rx.var
    def item_movement_product_catalog(self) -> MovementProductsCatalog:
        return (
            self.item.movement.products_catalog[self.current_product_catalog_index]
            if len(self.item.movement.products_catalog) > 0
            else MovementProductsCatalog()
        )

    @rx.var
    def nds_rate_title(self) -> str:
        if self.item.nds_rate is not None:
            return f"{self.item.nds_rate.title} ({self.item.nds_rate.rate}%)"
        return "—"

    @rx.var
    def invoice_number(self) -> str:
        return self.item.invoice_number if self.item.invoice_number is not None else ""

    def _nds_split(self) -> Tuple[float, float, float]:
        """(база, ПДВ, разом) — спільна формула `declared.admission_nds_split`.
        Ставка тут береться з завантаженого relationship `Admission.nds_rate`
        (у View немає кешу ставок, як в Add/Edit)."""
        lines = [
            line
            for pc in self.item.movement.products_catalog
            for line in _admission_unit_lines(pc)
        ]
        rate = self.item.nds_rate.rate if self.item.nds_rate is not None else 0.0
        return admission_nds_split(lines, rate, self.item.flag_nds)

    @rx.var
    def subtotal_display(self) -> str:
        return _format_money(self._nds_split()[0])

    @rx.var
    def nds_amount_display(self) -> str:
        return _format_money(self._nds_split()[1])

    @rx.var
    def total_display(self) -> str:
        return _format_money(self._nds_split()[2])

    @rx.event
    async def on_change_dialog_open(self, index: int):
        view_state = await self.get_state(MovementProductCatalogDetailedViewState)
        self.current_product_catalog_index = index
        view_state.set_item(self.item.movement.products_catalog[index])
        self.dialog_open = True

    @rx.event
    def close_dialog(self):
        self.dialog_open = False
        self.current_product_catalog_index = -1

    @rx.event
    def on_click_delete(self):
        if not self.has_permission(Action.ADMISSIONS_DELETE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None:
            yield rx.toast.error("Не обрано запис для видалення!")
            return

        list_id_products: List[int] = [
            product.id
            for pc in self.item.movement.products_catalog
            for product in pc.products
        ]

        related_movements = MovementDAO.get_with_products_from_id(list_id_products, self.item.id)
        if related_movements:
            self.cancel_conflict_movements = related_movements
            self.is_cancel_conflict_dialog_open = True
            yield rx.toast.error("Видалення неможливе: товар бере участь у пізніших рухах!")
            return

        flag, text = AdmissionDAO.delete_one(self.item.id, self.user.login, reason=self.cancel_reason)
        if flag:
            yield rx.toast.success(text)
            yield rx.redirect(routes.MOVEMENT_ADMISSIONS)
            return
        yield rx.toast.error(text)
