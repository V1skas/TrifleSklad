from datetime import date
from typing import List, Optional, Tuple

import reflex as rx

import TrifleSklad.routes as routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.dao import (
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
from TrifleSklad.movement.list_mixin import ALL, MovementListFilterMixin
from TrifleSklad.state import AppState


class MovementProductCatalogAddEditFormState(rx.State):
    item: MovementProductsCatalog = MovementProductsCatalog(
        count=0, price=0.0, id_product_catalog=-1, products=[]
    )

    exclude_products_catalog_list: List[int] = []
    cache_products_catalog_list: List[ProductCatalog] = []

    # Interface logic variables
    # ======================
    id_product_catalog_entered: bool = False
    id_product_catalog_in_cache: str = ""
    is_product_uniq: bool = False

    # Живий пошук позиції каталогу в селекті (підрядок у назві).
    search_catalog: str = ""

    # Сире (як ввів користувач) значення ціни — щоб поле не переформатувалося
    # у float-представлення на кожне натискання (інакше заважає вводити).
    price_input: str = "0"

    error_count: bool = False
    error_price: bool = False
    # ======================

    # Dynamic variables
    # ======================
    @rx.var
    def products_catalog_list(self) -> List[Tuple[str, str]]:
        # Кеш — повний перелік (для пошуку за id у on_change); у вивід потрапляють
        # лише позиції, що містять пошуковий підрядок. Value = id позиції каталогу.
        self.cache_products_catalog_list = ProductCatalogDAO.get_all_exclude_ids(
            self.exclude_products_catalog_list
        )
        term = self.search_catalog.strip().lower()
        return [
            (catalog.title, str(catalog.id))
            for catalog in self.cache_products_catalog_list
            if term == "" or term in catalog.title.lower()
        ]

    @rx.var
    def item_products_list(self) -> List[Tuple[int, Product]]:
        return [(index, product) for index, product in enumerate(self.item.products)]

    @rx.var
    def has_errors(self) -> bool:
        return (
            self.error_count or self.error_price or self.item.id_product_catalog == -1
        )

    @rx.var
    def product_is_uniq(self) -> bool:
        return self.is_product_uniq

    # ======================

    # Backend only
    # ======================
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

    # ======================

    # Getters for form fields
    # ======================
    @rx.var
    def id_product_catalog(self) -> str:
        return self.id_product_catalog_in_cache

    @rx.var
    def count(self) -> str:
        return str(self.item.count)

    @rx.var
    def price(self) -> str:
        return self.price_input

    # ======================

    # Event handlers for form fields
    # ======================
    def _per_unit_count(self) -> int:
        # Подільна одиниця ТМЦ створюється з повною місткістю (capacity) — це її
        # максимальний обсяг/залишок. Неподільна одиниця завжди має count = 1.
        product = self.item.product
        if (
            product is not None
            and product.divisible
            and product.capacity
            and product.capacity > 0
        ):
            return product.capacity
        return 1

    @rx.event
    def on_change_search_catalog(self, value: str):
        self.search_catalog = value

    @rx.event
    def on_change_id_product_catalog(self, value: str):
        # value — id позиції каталогу; шукаємо її в кеші.
        self.id_product_catalog_in_cache = value
        selected = next(
            (c for c in self.cache_products_catalog_list if str(c.id) == value),
            None,
        )
        if selected is None:
            return
        self.item.product = selected
        self.item.id_product_catalog = self.item.product.id
        if self.is_product_uniq and not self.item.product.uniq:
            for i in range(self.item.count):
                self.item.products[i].serial_number = ""
        # Зміна позиції каталогу — оновлюємо вже створені одиниці під нову позицію
        # (id каталогу та обсяг однієї одиниці: capacity для подільного, інакше 1).
        per_unit = self._per_unit_count()
        for unit in self.item.products:
            unit.id_product_catalog = self.item.product.id
            unit.count = per_unit
        self.is_product_uniq = self.item.product.uniq

    @rx.event
    def on_change_count(self, value: str):
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
            return

        per_unit = self._per_unit_count()
        for _ in range(int(value) - list_len):
            self.item.products.append(
                Product(
                    id_product_catalog=self.item.id_product_catalog,
                    id_storage=-1,
                    id_owner=-1,
                    serial_number="",
                    count=per_unit,
                )
            )

    @rx.event
    def on_change_serial_numbers(self, index: int, value: str):
        if index < len(self.item.products):
            self.item.products[index].serial_number = value

    @rx.event
    def on_change_price(self, value: str):
        # Зберігаємо рядок як є (не переформатовуємо), а у float парсимо лише для
        # обчислень/валідації. Порожнє поле — ціна 0 (мінімум, без помилки).
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

    # ======================

    # Action handlers
    # ======================
    @rx.event
    def set_item(self, item: MovementProductsCatalog):
        self.item = item

        self.is_product_uniq = item.product.uniq
        self.id_product_catalog_entered = True
        # Value селекта = id позиції каталогу (щоб селект показав поточну позицію).
        self.id_product_catalog_in_cache = (
            str(item.product.id) if item.product is not None else ""
        )
        self.search_catalog = ""
        self.price_input = str(item.price)

    @rx.event
    def clear(self):
        self.item = MovementProductsCatalog(
            count=0, price=0.0, id_product_catalog=-1, products=[]
        )

        self.is_product_uniq = False
        self.id_product_catalog_entered = False
        self.id_product_catalog_in_cache = ""
        self.search_catalog = ""
        self.price_input = "0"
        self.error_count = False
        self.error_price = False
        self._reset_new_product()
        self.is_create_open = False

    # ======================

    # Створення нового товару каталогу прямо з діалогу поставки
    # ======================
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

    def _reset_new_product(self):
        self.new_title = ""
        self.new_description = ""
        self.new_id_category = ""
        self.new_unit = ""
        self.new_divisible = False
        self.new_uniq = False
        self.new_capacity = "0"

    @rx.event
    def open_create_product(self):
        self.list_categories = [
            (str(item.id), item.title) for item in ProductCategoryDAO.get_all()
        ]
        self.units_cache = ProductCatalogDAO.get_list_units()
        self._reset_new_product()
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
        # Товар із серійним номером завжди має місткість 1.
        if self.new_uniq:
            self.new_capacity = "1"
            return
        self.new_capacity = value

    @rx.event
    def on_change_new_uniq(self, value: bool):
        self.new_uniq = value
        if value:
            # Серійний номер ⇒ неподільний, місткість = 1.
            self.new_divisible = False
            self.new_capacity = "1"

    @rx.event
    def on_change_new_divisible(self, value: bool):
        # Товар із серійним номером (uniq) не може бути подільним.
        if self.new_uniq:
            self.new_divisible = False
            return
        self.new_divisible = value

    @rx.event
    async def create_product(self):
        # Створення товару каталогу з поставки потребує права на додавання ТМЦ.
        if not (await self.get_state(AppState)).has_permission(ActionEnum.PRODUCTS_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        title = self.new_title.strip()
        if title == "" or self.new_id_category == "":
            return rx.toast.error("Вкажіть назву та категорію товару!")
        if self.new_uniq and self.new_divisible:
            return rx.toast.error("Товар із серійним номером не може бути подільним!")

        capacity = (
            1
            if self.new_uniq
            else (int(self.new_capacity) if self.new_capacity.isdigit() else 0)
        )
        product = ProductCatalog(
            title=title,
            description=self.new_description.strip() or None,
            id_category=int(self.new_id_category),
            unit=self.new_unit.strip(),
            divisible=False if self.new_uniq else self.new_divisible,
            uniq=self.new_uniq,
            capacity=capacity,
            count=0,
        )
        flag, text, new_id = ProductCatalogDAO.add_one(product)
        if not flag:
            return rx.toast.error(text)

        # Новий товар одразу обираємо в поточному рядку поставки.
        self._load_products_catalog_list()
        self.search_catalog = ""
        for catalog in self.cache_products_catalog_list:
            if catalog.id == new_id:
                self.id_product_catalog_in_cache = str(catalog.id)
                self.item.product = catalog
                self.item.id_product_catalog = catalog.id
                self.is_product_uniq = catalog.uniq
                per_unit = self._per_unit_count()
                for unit in self.item.products:
                    unit.id_product_catalog = catalog.id
                    unit.count = per_unit
                break

        self.is_create_open = False
        self._reset_new_product()
        return rx.toast.success("Товар створено та обрано!")
    # ======================

    # Створення нової категорії прямо з діалогу створення товару
    # ======================
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
        if not (await self.get_state(AppState)).has_permission(ActionEnum.CATEGORIES_CREATE):
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

        # Перезавантажуємо список і одразу обираємо нову категорію в новому товарі.
        self.list_categories = [
            (str(item.id), item.title) for item in ProductCategoryDAO.get_all()
        ]
        self.new_id_category = str(new_id)
        self.is_create_category_open = False
        self._reset_new_category()
        return rx.toast.success("Категорію створено та обрано!")
    # ======================


class MovementProductCatalogDetailedViewState(rx.State):
    item: MovementProductsCatalog = MovementProductsCatalog(
        count=0, price=0.0, id_product_catalog=-1, products=[]
    )

    @rx.var
    def item_products_list(self) -> List[Tuple[int, Product]]:
        return [(index, product) for index, product in enumerate(self.item.products)]

    # Action handlers
    # ======================
    @rx.event
    def set_item(self, item: MovementProductsCatalog):
        self.item = item

    @rx.event
    def clear(self):
        self.item = MovementProductsCatalog(
            count=0, price=0.0, id_product_catalog=-1, products=[]
        )

    # ======================


class ListAdmissionState(MovementListFilterMixin, rx.State):
    items: List[Admission] = []

    # Фільтр, специфічний для поставок: постачальник.
    filter_supplier: str = ALL
    list_suppliers: List[Tuple[str, str]] = []

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
        )

    # Dynamic variables
    # ======================
    @rx.var
    def has_active_filters(self) -> bool:
        return bool(
            self.filter_date_enabled
            or self.selected_statuses
            or self.filter_destination_storage != ALL
            or self.filter_destination_owner != ALL
            or self.filter_supplier != ALL
        )

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def get_items(self) -> List[Tuple[int, Admission]]:
        return [(index, item) for index, item in enumerate(self.items)]

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list

    # ======================

    # Action handlers
    # ======================
    @rx.event
    def on_load(self):
        self._reset_list_state()
        self.filter_supplier = ALL
        self.list_suppliers = [(s.title, str(s.id)) for s in SupplierDAO.get_all()]
        self._reload()

    @rx.event
    def on_change_filter_supplier(self, value: str):
        self.filter_supplier = value

    @rx.event
    def reset_filters(self):
        today = date.today().isoformat()
        self.filter_date_enabled = False
        self.filter_date_from = today
        self.filter_date_to = today
        self.selected_statuses = []
        self.filter_incoming_storage = ALL
        self.filter_destination_storage = ALL
        self.filter_incoming_owner = ALL
        self.filter_destination_owner = ALL
        self.filter_supplier = ALL
        self._current_page = 1
        self._reload()

    # ======================


class AddAdmissionState(rx.State):
    class ProductCatalogDialogPages:
        EDIT = "edit"
        VIEW = "view"
        EMPTY = "empty"

    # Form fields
    # ======================
    item: Admission = Admission(
        id_payment_type="-1",
        id_supplier=-1,
        flag_nds=False,
        id_nds_rate=None,
        dollar_rate=0.0,
        invoice_number=None,
        movement=Movement(
            id_destination_storage=-1,
            id_destination_owner=-1,
            date=date.today().__str__(),
            comment="",
            status=MovementsStatus.CREATED,
            type=MovementsType.ADMISSION,
            total_cost=0.0,
            products_catalog=[],
        ),
    )
    current_product_catalog_index: int
    # ======================

    # Filter fields
    # ======================
    search_name_destination_storage: str
    # ======================

    # Preloaded lists
    # ======================
    list_suppliers: List[Tuple[str, str]]
    list_storages: List[Tuple[str, str]]
    list_owners: List[Tuple[str, str]]
    list_payment_types: List[Tuple[str, str]]
    list_nds_rates: List[Tuple[str, str]]
    nds_rates_cache: List[Tuple[int, float]]
    # ======================

    # Interface logic variables
    # ======================
    is_open_product_catalog_dialog: bool
    product_catalog_dialog_page: str
    is_product_dialog_view_mode: bool
    # ======================

    # Nested form states
    # ======================
    addedit_product_catalog_form_state: Optional[
        MovementProductCatalogAddEditFormState
    ] = None
    view_product_catalog_form_state: Optional[
        MovementProductCatalogDetailedViewState
    ] = None
    # ======================

    app_state: Optional[AppState] = None

    # Backend only
    # ======================
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

    def _recompute_total(self):
        line_total = sum(pc.count * pc.price for pc in self.item.movement.products_catalog)
        rate = self._get_nds_rate_value() / 100.0
        if rate <= 0:
            self.item.movement.total_cost = round(line_total, 2)
            return
        if self.item.flag_nds:
            self.item.movement.total_cost = round(line_total, 2)
        else:
            self.item.movement.total_cost = round(line_total * (1 + rate), 2)

    @rx.event
    async def on_load(self):
        self.item = Admission(
            id_payment_type="-1",
            id_supplier=-1,
            flag_nds=False,
            id_nds_rate=None,
            dollar_rate=0.0,
            invoice_number=None,
            movement=Movement(
                id_destination_storage=-1,
                id_destination_owner=-1,
                date=date.today().__str__(),
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

        self.addedit_product_catalog_form_state = await self.get_state(
            MovementProductCatalogAddEditFormState
        )
        self.view_product_catalog_form_state = await self.get_state(
            MovementProductCatalogDetailedViewState
        )

        if self.app_state is None:
            self.app_state = await self.get_state(AppState)

    # ======================

    # Getters for form fields
    # ======================
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
        line_total = sum(pc.count * pc.price for pc in self.item.movement.products_catalog)
        rate = self._get_nds_rate_value() / 100.0
        if rate <= 0:
            return f"{round(line_total, 2)}"
        if self.item.flag_nds:
            return f"{round(line_total / (1 + rate), 2)}"
        return f"{round(line_total, 2)}"

    @rx.var
    def nds_amount_display(self) -> str:
        line_total = sum(pc.count * pc.price for pc in self.item.movement.products_catalog)
        rate = self._get_nds_rate_value() / 100.0
        if rate <= 0:
            return "0.0"
        if self.item.flag_nds:
            subtotal = line_total / (1 + rate)
            return f"{round(line_total - subtotal, 2)}"
        return f"{round(line_total * rate, 2)}"

    @rx.var
    def total_display(self) -> str:
        line_total = sum(pc.count * pc.price for pc in self.item.movement.products_catalog)
        rate = self._get_nds_rate_value() / 100.0
        if rate <= 0 or self.item.flag_nds:
            return f"{round(line_total, 2)}"
        return f"{round(line_total * (1 + rate), 2)}"

    # ======================

    # Event handlers for form fields
    # ======================
    @rx.event
    def on_change_search_name_destination_storage(self, value: str):
        self.search_name_destination_storage = value

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

    # ======================

    # Dynamic variables
    # ======================
    @rx.var
    def item_status(self) -> str:
        return movements_status_list[self.item.movement.status]

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list

    @rx.var
    def editable_statuses(self) -> List[str]:
        # «Скасовано» виставляється лише кнопкою «Скасувати» (з поверненням залишків).
        return [
            status
            for index, status in enumerate(movements_status_list)
            if index != MovementsStatus.CANCELED
        ]

    @rx.var
    def item_movement_products_catalog_list(
        self,
    ) -> List[Tuple[int, MovementProductsCatalog]]:
        return [
            (index, pc) for index, pc in enumerate(self.item.movement.products_catalog)
        ]

    @rx.var
    def has_item_movement_products_catalog(self) -> bool:
        return len(self.item.movement.products_catalog) > 0

    # ======================

    # Action handlers
    # ======================
    @rx.event
    def view_product_catalog_dialog(self, index: int):
        if self.view_product_catalog_dialog is None:
            return
        self.is_product_dialog_view_mode = True
        self.current_product_catalog_index = index
        self.view_product_catalog_form_state.item = self.item.movement.products_catalog[
            index
        ]
        self.product_catalog_dialog_page = self.ProductCatalogDialogPages.VIEW
        self.is_open_product_catalog_dialog = True

    @rx.event
    def add_product_catalog_dialog_open(self):
        if self.addedit_product_catalog_form_state is None:
            return rx.toast.error(
                "Стан форми додавання/редагування товарної позиції не ініціалізовано"
            )
        self.is_product_dialog_view_mode = False
        self.current_product_catalog_index = -1
        self.addedit_product_catalog_form_state.clear()
        self.addedit_product_catalog_form_state.set_exclude_products_catalog_list(
            [pc.product.id for pc in self.item.movement.products_catalog]
        )
        self.product_catalog_dialog_page = self.ProductCatalogDialogPages.EDIT
        self.is_open_product_catalog_dialog = True
        return None

    @rx.event
    def edit_product_catalog_dialog(self):
        if self.addedit_product_catalog_form_state is None:
            return
        self.is_product_dialog_view_mode = False
        self.addedit_product_catalog_form_state.set_item(
            self.item.movement.products_catalog[self.current_product_catalog_index]
        )
        self.addedit_product_catalog_form_state.exclude_products_catalog_list = [
            pc.product.id
            for i, pc in enumerate(self.item.movement.products_catalog)
            if i != self.current_product_catalog_index
        ]
        self.product_catalog_dialog_page = self.ProductCatalogDialogPages.EDIT
        self.is_open_product_catalog_dialog = True

    @rx.event
    def on_save_product_catalog_dialog(self):
        if self.addedit_product_catalog_form_state is None:
            return

        if self.addedit_product_catalog_form_state.has_errors:
            return

        item = self.addedit_product_catalog_form_state.item

        if self.current_product_catalog_index > -1:
            self.item.movement.products_catalog[self.current_product_catalog_index] = (
                item
            )
        else:
            self.item.movement.products_catalog.append(item)

        self._recompute_total()
        self.is_open_product_catalog_dialog = False

    @rx.event
    def on_close_product_catalog_dialog(self):
        self.is_open_product_catalog_dialog = False

    @rx.event
    async def add_one(self):
        if not self.app_state.has_permission(ActionEnum.ADMISSIONS_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        if self.item.movement.id_destination_storage <= 0 or self.item.movement.id_destination_owner <= 0:
            return rx.toast.error("Не обрано склад або власника призначення!")
        if AdmissionDAO.is_invoice_number_exists(self.item.invoice_number):
            return rx.toast.error("Постачання з таким номером накладної оплати вже існує!")
        self.item.movement.id_user = (await self.get_state(AppState)).user.login

        # Товар поступає на склад призначення поставки — проставляємо склад/власника
        # кожній одиниці ТМЦ, інакше залишки не знайдуться при списанні/русі.
        for pc in self.item.movement.products_catalog:
            for product in pc.products:
                product.id_storage = self.item.movement.id_destination_storage
                product.id_owner = self.item.movement.id_destination_owner

        flag, text, id = AdmissionDAO.add_one(self.item)
        if flag:
            return [
                rx.toast.success(text),
                rx.redirect(f"{routes.MOVEMENT_ADMISSIONS_VIEW_ID}{id}"),
            ]
        return rx.toast.error(text)

    @rx.event
    def cancel(self):
        return rx.redirect(routes.MOVEMENT_ADMISSIONS)

    # ======================


class EditAdmissionState(rx.State):
    class ProductCatalogDialogPages:
        EDIT = "edit"
        VIEW = "view"
        EMPTY = "empty"

    # Form fields
    # ======================
    item: Optional[Admission] = None
    current_product_catalog_index: int = -1
    # ======================

    # Filter fields
    # ======================
    search_name_destination_storage: str = ""
    # ======================

    # Preloaded lists
    # ======================
    list_suppliers: List[Tuple[str, str]] = []
    list_storages: List[Tuple[str, str]] = []
    list_owners: List[Tuple[str, str]] = []
    list_payment_types: List[Tuple[str, str]] = []
    list_nds_rates: List[Tuple[str, str]] = []
    nds_rates_cache: List[Tuple[int, float]] = []
    # ======================

    # Interface logic variables
    # ======================
    is_open_product_catalog_dialog: bool = False
    product_catalog_dialog_page: str = ""
    is_product_dialog_view_mode: bool = False
    # ======================

    # Nested form states
    # ======================
    addedit_product_catalog_form_state: Optional[
        MovementProductCatalogAddEditFormState
    ] = None
    view_product_catalog_form_state: Optional[
        MovementProductCatalogDetailedViewState
    ] = None
    # ======================

    app_state: Optional[AppState] = None

    # Backend only
    # ======================
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

    def _recompute_total(self):
        if self.item is None:
            return
        line_total = sum(pc.count * pc.price for pc in self.item.movement.products_catalog)
        rate = self._get_nds_rate_value() / 100.0
        if rate <= 0:
            self.item.movement.total_cost = round(line_total, 2)
            return
        if self.item.flag_nds:
            self.item.movement.total_cost = round(line_total, 2)
        else:
            self.item.movement.total_cost = round(line_total * (1 + rate), 2)

    @rx.event
    async def on_load(self, id: int):
        self.search_name_destination_storage = ""
        self.is_open_product_catalog_dialog = False
        self.product_catalog_dialog_page = self.ProductCatalogDialogPages.EMPTY
        self.current_product_catalog_index = -1

        self._load_suppliers()
        self._load_storages()
        self._load_owners()
        self._load_payment_types()
        self._load_nds_rates()

        self.item = AdmissionDAO.get_by_id_with_all_relationship(id)
        if self.item is None:
            return [
                rx.redirect(routes.MOVEMENT_ADMISSIONS),
                rx.toast.error("Запис не знайдено!"),
            ]

        self.addedit_product_catalog_form_state = await self.get_state(
            MovementProductCatalogAddEditFormState
        )
        self.view_product_catalog_form_state = await self.get_state(
            MovementProductCatalogDetailedViewState
        )

        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
    # ======================

    # Getters for form fields
    # ======================
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
        if self.item is None:
            return "0.0"
        line_total = sum(pc.count * pc.price for pc in self.item.movement.products_catalog)
        rate = self._get_nds_rate_value() / 100.0
        if rate <= 0:
            return f"{round(line_total, 2)}"
        if self.item.flag_nds:
            return f"{round(line_total / (1 + rate), 2)}"
        return f"{round(line_total, 2)}"

    @rx.var
    def nds_amount_display(self) -> str:
        if self.item is None:
            return "0.0"
        line_total = sum(pc.count * pc.price for pc in self.item.movement.products_catalog)
        rate = self._get_nds_rate_value() / 100.0
        if rate <= 0:
            return "0.0"
        if self.item.flag_nds:
            subtotal = line_total / (1 + rate)
            return f"{round(line_total - subtotal, 2)}"
        return f"{round(line_total * rate, 2)}"

    @rx.var
    def total_display(self) -> str:
        if self.item is None:
            return "0.0"
        line_total = sum(pc.count * pc.price for pc in self.item.movement.products_catalog)
        rate = self._get_nds_rate_value() / 100.0
        if rate <= 0 or self.item.flag_nds:
            return f"{round(line_total, 2)}"
        return f"{round(line_total * (1 + rate), 2)}"

    @rx.var
    def item_status(self) -> str:
        return movements_status_list[self.item.movement.status] if self.item is not None else ""

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list

    @rx.var
    def item_movement_products_catalog_list(
        self,
    ) -> List[Tuple[int, MovementProductsCatalog]]:
        if self.item is None:
            return []
        return [
            (index, pc) for index, pc in enumerate(self.item.movement.products_catalog)
        ]

    @rx.var
    def has_item_movement_products_catalog(self) -> bool:
        return self.item is not None and len(self.item.movement.products_catalog) > 0
    # ======================

    # Event handlers for form fields
    # ======================
    @rx.event
    def on_change_search_name_destination_storage(self, value: str):
        self.search_name_destination_storage = value

    @rx.event
    def on_click_search_name_destination_storage(self):
        self._load_storages()

    @rx.event
    def on_change_id_destination_storage(self, value: str):
        if self.item is not None and value.lstrip("-").isdigit():
            self.item.movement.id_destination_storage = int(value)

    @rx.event
    def on_change_id_destination_owner(self, value: str):
        if self.item is not None and value.lstrip("-").isdigit():
            self.item.movement.id_destination_owner = int(value)

    @rx.event
    def on_change_id_supplier(self, value: str):
        if self.item is not None and value.lstrip("-").isdigit():
            self.item.id_supplier = int(value)

    @rx.event
    def on_change_status(self, value: str):
        if self.item is None:
            return
        for index, status_text in enumerate(movements_status_list):
            if status_text == value:
                self.item.movement.status = index
                return

    @rx.event
    def on_change_id_payment_type(self, value: str):
        if self.item is not None and value.lstrip("-").isdigit():
            self.item.id_payment_type = int(value)

    @rx.event
    def on_change_flag_nds(self, value: bool):
        if self.item is None:
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
        if self.item is None:
            return
        try:
            self.item.dollar_rate = float(value)
        except ValueError:
            self.item.dollar_rate = 0.0

    @rx.event
    def on_change_date(self, value: str):
        if self.item is not None:
            self.item.movement.date = value

    @rx.event
    def on_change_comment(self, value: str):
        if self.item is not None:
            self.item.movement.comment = value
    # ======================

    # Action handlers
    # ======================
    @rx.event
    def view_product_catalog_dialog(self, index: int):
        if self.view_product_catalog_form_state is None or self.item is None:
            return
        self.is_product_dialog_view_mode = True
        self.current_product_catalog_index = index
        self.view_product_catalog_form_state.item = self.item.movement.products_catalog[index]
        self.product_catalog_dialog_page = self.ProductCatalogDialogPages.VIEW
        self.is_open_product_catalog_dialog = True

    @rx.event
    def add_product_catalog_dialog_open(self):
        if self.addedit_product_catalog_form_state is None or self.item is None:
            return rx.toast.error(
                "Стан форми додавання/редагування товарної позиції не ініціалізовано"
            )
        self.is_product_dialog_view_mode = False
        self.current_product_catalog_index = -1
        self.addedit_product_catalog_form_state.clear()
        self.addedit_product_catalog_form_state.set_exclude_products_catalog_list(
            [pc.product.id for pc in self.item.movement.products_catalog]
        )
        self.product_catalog_dialog_page = self.ProductCatalogDialogPages.EDIT
        self.is_open_product_catalog_dialog = True
        return None

    @rx.event
    def edit_product_catalog_dialog(self):
        if self.addedit_product_catalog_form_state is None or self.item is None:
            return
        self.is_product_dialog_view_mode = False
        self.addedit_product_catalog_form_state.set_item(
            self.item.movement.products_catalog[self.current_product_catalog_index]
        )
        self.addedit_product_catalog_form_state.exclude_products_catalog_list = [
            pc.product.id
            for i, pc in enumerate(self.item.movement.products_catalog)
            if i != self.current_product_catalog_index
        ]
        self.product_catalog_dialog_page = self.ProductCatalogDialogPages.EDIT
        self.is_open_product_catalog_dialog = True

    @rx.event
    def on_save_product_catalog_dialog(self):
        if self.addedit_product_catalog_form_state is None or self.item is None:
            return
        if self.addedit_product_catalog_form_state.has_errors:
            return

        item = self.addedit_product_catalog_form_state.item

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
    async def edit_one(self):
        if not self.app_state.has_permission(ActionEnum.ADMISSIONS_EDIT):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        if self.item is None:
            return rx.toast.error("Запис не завантажено!")
        if self.item.movement.id_destination_storage <= 0 or self.item.movement.id_destination_owner <= 0:
            return rx.toast.error("Не обрано склад або власника призначення!")
        if AdmissionDAO.is_invoice_number_exists(self.item.invoice_number, exclude_id=self.item.id):
            return rx.toast.error("Постачання з таким номером накладної оплати вже існує!")
        self.item.movement.id_user = (await self.get_state(AppState)).user.login

        # Синхронізуємо склад/власника одиниць ТМЦ зі складом призначення поставки.
        for pc in self.item.movement.products_catalog:
            for product in pc.products:
                product.id_storage = self.item.movement.id_destination_storage
                product.id_owner = self.item.movement.id_destination_owner

        flag, text, id = AdmissionDAO.edit_one(self.item)
        if flag:
            return [
                rx.toast.success(text),
                rx.redirect(f"{routes.MOVEMENT_ADMISSIONS_VIEW_ID}{id}"),
            ]
        return rx.toast.error(text)

    @rx.event
    def cancel(self):
        return rx.redirect(routes.MOVEMENT_ADMISSIONS)
    # ======================


class ViewAdmissionState(rx.State):
    item: Admission = Admission(
        id_payment_type="-1",
        id_supplier=-1,
        flag_nds=False,
        id_nds_rate=None,
        dollar_rate=0.0,
        invoice_number=None,
        movement=Movement(
            id_destination_storage=-1,
            id_destination_owner=-1,
            date=date.today().__str__(),
            comment="",
            status=MovementsStatus.CREATED,
            type=MovementsType.ADMISSION,
            total_cost=0.0,
            products_catalog=[],
        ),
    )

    dialog_open: bool = False
    current_product_catalog_index: int = -1

    # Nested form states
    # ======================
    view_product_catalog_form_state: Optional[
        MovementProductCatalogDetailedViewState
    ] = None
    # ======================

    app_state: Optional[AppState] = None

    # Backend only
    # ======================
    @rx.event
    async def on_load(self, id: int):
        self.view_product_catalog_form_state = await self.get_state(
            MovementProductCatalogDetailedViewState
        )
        self.item = AdmissionDAO.get_by_id_with_all_relationship(id)
        if self.item is None:
            return [
                rx.redirect(routes.MOVEMENT_ADMISSIONS),
                rx.toast.error("Запис не знайдено!"),
            ]
        self.dialog_open = False
        self.current_product_catalog_index = -1

        if self.app_state is None:
            self.app_state = await self.get_state(AppState)

    # ======================

    # Cancel-conflict dialog
    # ======================
    cancel_conflict_movements: List[Movement] = []
    is_cancel_conflict_dialog_open: bool = False

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
    # ======================

    # Getters for form fields
    # ======================
    @rx.var
    def item_status(self) -> str:
        return movements_status_list[self.item.movement.status]

    @rx.var
    def item_movement_products_catalog_list(
        self,
    ) -> List[Tuple[int, MovementProductsCatalog]]:
        return [
            (index, pc) for index, pc in enumerate(self.item.movement.products_catalog)
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

    @rx.var
    def subtotal_display(self) -> str:
        line_total = sum(pc.count * pc.price for pc in self.item.movement.products_catalog)
        rate = (self.item.nds_rate.rate / 100.0) if self.item.nds_rate is not None else 0.0
        if rate <= 0:
            return f"{round(line_total, 2)}"
        if self.item.flag_nds:
            return f"{round(line_total / (1 + rate), 2)}"
        return f"{round(line_total, 2)}"

    @rx.var
    def nds_amount_display(self) -> str:
        line_total = sum(pc.count * pc.price for pc in self.item.movement.products_catalog)
        rate = (self.item.nds_rate.rate / 100.0) if self.item.nds_rate is not None else 0.0
        if rate <= 0:
            return "0.0"
        if self.item.flag_nds:
            subtotal = line_total / (1 + rate)
            return f"{round(line_total - subtotal, 2)}"
        return f"{round(line_total * rate, 2)}"

    @rx.var
    def total_display(self) -> str:
        line_total = sum(pc.count * pc.price for pc in self.item.movement.products_catalog)
        rate = (self.item.nds_rate.rate / 100.0) if self.item.nds_rate is not None else 0.0
        if rate <= 0 or self.item.flag_nds:
            return f"{round(line_total, 2)}"
        return f"{round(line_total * (1 + rate), 2)}"

    # ======================

    # Action handlers
    # ======================
    @rx.event
    def on_change_dialog_open(self, index: int):
        if self.view_product_catalog_form_state is None:
            return
        self.current_product_catalog_index = index
        self.view_product_catalog_form_state.set_item(
            self.item.movement.products_catalog[index]
        )
        self.dialog_open = True

    @rx.event
    def close_dialog(self):
        self.dialog_open = False
        self.current_product_catalog_index = -1

    # ======================


class AdmissionState(rx.State):
    class Pages:
        ADD = "add"
        EDIT = "edit"
        VIEW = "view"
        LIST = "list"

    current_page: str = Pages.LIST
    app_state: Optional[AppState] = None

    def _check_path(self):
        page = self.router.page.params.get("page", "")
        if page != "":
            id = -1
            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                yield rx.redirect(routes.MOVEMENT_ADMISSIONS)
                return

            if page == self.Pages.ADD:
                if not self.app_state.has_permission(ActionEnum.ADMISSIONS_CREATE):
                    yield rx.redirect(routes.WELCOME)
                    return
                yield AddAdmissionState.on_load()
            elif page == self.Pages.EDIT:
                if not self.app_state.has_permission(ActionEnum.ADMISSIONS_EDIT):
                    yield rx.redirect(routes.WELCOME)
                    return
                id = self.router.page.params.get("id", "")
                if id != "":
                    yield EditAdmissionState.on_load(int(id))
                else:
                    yield rx.redirect(routes.MOVEMENT_ADMISSIONS)
                    return
            elif page == self.Pages.VIEW:
                if not self.app_state.has_permission(ActionEnum.ADMISSIONS_VIEW):
                    yield rx.redirect(routes.WELCOME)
                    return
                id = self.router.page.params.get("id", "")
                if id != "":
                    yield ViewAdmissionState.on_load(int(id))
                else:
                    yield rx.redirect(routes.MOVEMENT_ADMISSIONS)
                    return

            self.current_page = page
        else:
            if not self.app_state.has_permission(ActionEnum.ADMISSIONS_LIST):
                yield rx.redirect(routes.WELCOME)
                return
            yield ListAdmissionState.on_load()
            self.current_page = self.Pages.LIST

    @rx.event
    async def on_load(self):
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
        return self._check_path()

    @rx.event
    async def delete_one(self, id):
        if id == -1:
            return rx.toast.error("Не обрано запис для видалення!")
        if not self.app_state.has_permission(ActionEnum.ADMISSIONS_DELETE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")

        view_state = await self.get_state(ViewAdmissionState)

        # Одиниці товару, що надійшли цим постачанням.
        list_id_products: List[int] = [
            product.id
            for pc in view_state.item.movement.products_catalog
            for product in pc.products
        ]

        # Якщо товар бере участь у пізніших рухах (за наскрізним номером) —
        # видалення заборонено. Показуємо перелік рухів із цим товаром,
        # починаючи з поточного.
        related_movements = MovementDAO.get_with_products_from_id(list_id_products, id)
        if any(m.id != id for m in related_movements):
            view_state.cancel_conflict_movements = related_movements
            view_state.is_cancel_conflict_dialog_open = True
            return rx.toast.error(
                "Видалення неможливе: товар бере участь у пізніших рухах!"
            )

        flag, text = AdmissionDAO.delete_one(id)
        if flag:
            return [rx.toast.success(text), rx.redirect(routes.MOVEMENT_ADMISSIONS)]
        return rx.toast.error(text)
