from datetime import date
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
    ADMISSION_PRODUCTS_EDIT_WINDOW_DAYS,
    MovementsStatus,
    MovementsType,
    StorageType,
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
from TrifleSklad.utils.clock import now_local


def _format_money(value: float) -> str:
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return "0.00"


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
    selected_capacity: int = 0

    search_catalog: str = ""

    filter_category: str = ""

    price_input: str = "0"

    error_count: bool = False
    error_price: bool = False

    @rx.var
    def category_options(self) -> List[Tuple[str, str]]:
        return [(label, id) for id, label in ProductCategoryDAO.get_hierarchy_options()]

    @rx.var
    def category_chosen(self) -> bool:
        return self.filter_category != ""

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
        return [
            (catalog.title, str(catalog.id))
            for catalog in self.cache_products_catalog_list
            if str(catalog.id_category) in allowed_category_ids
            and (term == "" or term in catalog.title.lower())
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

    def _per_unit_count(self) -> int:
        if self.selected_divisible and self.selected_capacity > 0:
            return self.selected_capacity
        return 1

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
        if self.is_product_uniq and not self.item.product.uniq:
            for i in range(self.item.count):
                self.item.products[i].serial_number = ""
        per_unit = self._per_unit_count()
        for unit in self.item.products:
            unit.id_product_catalog = self.item.product.id
            unit.count = per_unit
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

    @rx.event
    def clear(self):
        self.item = MovementProductsCatalog(
            count=0, price=0.0, id_product_catalog=-1, products=[]
        )

        self.is_product_uniq = False
        self.selected_divisible = False
        self.selected_capacity = 0
        self.id_product_catalog_entered = False
        self.id_product_catalog_in_cache = ""
        self.search_catalog = ""
        self.filter_category = ""
        self.price_input = "0"
        self.error_count = False
        self.error_price = False
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
        if self.new_uniq:
            self.new_capacity = "1"
            return
        self.new_capacity = value

    @rx.event
    def on_change_new_uniq(self, value: bool):
        self.new_uniq = value
        if value:
            self.new_divisible = False
            self.new_capacity = "1"

    @rx.event
    def on_change_new_divisible(self, value: bool):
        if self.new_uniq:
            self.new_divisible = False
            return
        self.new_divisible = value

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
                per_unit = self._per_unit_count()
                for unit in self.item.products:
                    unit.id_product_catalog = catalog.id
                    unit.count = per_unit
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
        if self.new_divisible and not (self.new_capacity.isdigit() and int(self.new_capacity) > 0):
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

        capacity = (
            1
            if self.new_uniq
            else (int(self.new_capacity) if self.new_capacity.isdigit() else 0)
        )
        product = ProductCatalog(
            title=title,
            description=self.new_description.strip() or None,
            id_category=int(self.new_id_category),
            unit=unit,
            divisible=False if self.new_uniq else self.new_divisible,
            uniq=self.new_uniq,
            capacity=capacity,
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
        if not self.has_permission(Action.ADMISSIONS_LIST):
            yield rx.redirect(routes.WELCOME)
            yield rx.toast.error("У Вас немає дозволу на перегляд цієї сторінки!")
            return
        self.in_progress = True
        self._reset_list_state()
        self.filter_supplier = ALL
        self.list_suppliers = [(s.title, str(s.id)) for s in SupplierDAO.get_all()]
        self._reload()
        self.in_progress = False

    @rx.event
    def on_click_add(self):
        return rx.redirect(routes.MOVEMENT_ADMISSIONS_ADD)

    @rx.event
    def on_change_filter_supplier(self, value: str):
        self.filter_supplier = value

    @rx.event
    def reset_filters(self):
        today = now_local().date().isoformat()
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
    def on_load(self):
        if not self.has_permission(Action.ADMISSIONS_CREATE):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
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
        line_total = sum(pc.count * pc.price for pc in self.item.movement.products_catalog)
        rate = self._get_nds_rate_value() / 100.0
        if rate <= 0:
            return _format_money(line_total)
        if self.item.flag_nds:
            return _format_money(line_total / (1 + rate))
        return _format_money(line_total)

    @rx.var
    def nds_amount_display(self) -> str:
        line_total = sum(pc.count * pc.price for pc in self.item.movement.products_catalog)
        rate = self._get_nds_rate_value() / 100.0
        if rate <= 0:
            return _format_money(0)
        if self.item.flag_nds:
            subtotal = line_total / (1 + rate)
            return _format_money(line_total - subtotal)
        return _format_money(line_total * rate)

    @rx.var
    def total_display(self) -> str:
        line_total = sum(pc.count * pc.price for pc in self.item.movement.products_catalog)
        rate = self._get_nds_rate_value() / 100.0
        if rate <= 0 or self.item.flag_nds:
            return _format_money(line_total)
        return _format_money(line_total * (1 + rate))

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
    ) -> List[Tuple[int, MovementProductsCatalog, str, str]]:
        return [
            (index, pc, _format_money(pc.price), _format_money(pc.count * pc.price))
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
        form_state.set_exclude_products_catalog_list(
            [pc.product.id for pc in self.item.movement.products_catalog]
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
            if i != self.current_product_catalog_index
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

        flag, text, id = AdmissionDAO.add_one(self.item)
        if not flag:
            yield rx.toast.error(text)
            return
        if keep:
            await self._reset_for_continue()
            yield rx.toast.success(text)
            return
        yield rx.toast.success(text)
        yield ListAdmissionState.on_load()
        yield rx.redirect(f"{routes.MOVEMENT_ADMISSIONS_VIEW_ID}{id}")


class EditAdmissionState(AppState):
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

    _can_edit_products: bool = False

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
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(Action.ADMISSIONS_EDIT):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
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

        self._can_edit_products = False
        if self.has_permission(Action.ADMISSIONS_EDIT_PRODUCTS):
            try:
                movement_date = date.fromisoformat(self.item.movement.date)
                within_window = (now_local().date() - movement_date).days <= ADMISSION_PRODUCTS_EDIT_WINDOW_DAYS
            except ValueError:
                within_window = False
            if within_window and AdmissionDAO.can_edit_products(self.item.id):
                self._can_edit_products = True
        self.in_process = False

    @rx.var
    def can_edit_products(self) -> bool:
        return self._can_edit_products

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
            return _format_money(0)
        line_total = sum(pc.count * pc.price for pc in self.item.movement.products_catalog)
        rate = self._get_nds_rate_value() / 100.0
        if rate <= 0:
            return _format_money(line_total)
        if self.item.flag_nds:
            return _format_money(line_total / (1 + rate))
        return _format_money(line_total)

    @rx.var
    def nds_amount_display(self) -> str:
        if self.item is None:
            return _format_money(0)
        line_total = sum(pc.count * pc.price for pc in self.item.movement.products_catalog)
        rate = self._get_nds_rate_value() / 100.0
        if rate <= 0:
            return _format_money(0)
        if self.item.flag_nds:
            subtotal = line_total / (1 + rate)
            return _format_money(line_total - subtotal)
        return _format_money(line_total * rate)

    @rx.var
    def total_display(self) -> str:
        if self.item is None:
            return _format_money(0)
        line_total = sum(pc.count * pc.price for pc in self.item.movement.products_catalog)
        rate = self._get_nds_rate_value() / 100.0
        if rate <= 0 or self.item.flag_nds:
            return _format_money(line_total)
        return _format_money(line_total * (1 + rate))

    @rx.var
    def item_status(self) -> str:
        return movements_status_list[self.item.movement.status] if self.item is not None else ""

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list

    @rx.var
    def item_movement_products_catalog_list(
        self,
    ) -> List[Tuple[int, MovementProductsCatalog, str, str]]:
        if self.item is None:
            return []
        return [
            (index, pc, _format_money(pc.price), _format_money(pc.count * pc.price))
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
        if self.item is None or not self._can_edit_products:
            return
        form_state = await self.get_state(MovementProductCatalogAddEditFormState)
        self.is_product_dialog_view_mode = False
        self.current_product_catalog_index = -1
        form_state.clear()
        form_state.set_exclude_products_catalog_list(
            [pc.product.id for pc in self.item.movement.products_catalog]
        )
        self.product_catalog_dialog_page = self.ProductCatalogDialogPages.EDIT
        self.is_open_product_catalog_dialog = True

    @rx.event
    async def edit_product_catalog_dialog(self):
        if self.item is None or not self._can_edit_products:
            return
        form_state = await self.get_state(MovementProductCatalogAddEditFormState)
        self.is_product_dialog_view_mode = False
        form_state.set_item(
            self.item.movement.products_catalog[self.current_product_catalog_index]
        )
        form_state.set_exclude_products_catalog_list([
            pc.product.id
            for i, pc in enumerate(self.item.movement.products_catalog)
            if i != self.current_product_catalog_index
        ])
        self.product_catalog_dialog_page = self.ProductCatalogDialogPages.EDIT
        self.is_open_product_catalog_dialog = True

    @rx.event
    async def edit_product_catalog_dialog_from_row(self, index: int):
        self.current_product_catalog_index = index
        await self.edit_product_catalog_dialog()

    @rx.event
    async def on_save_product_catalog_dialog(self):
        if self.item is None or not self._can_edit_products:
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
        if self.item is None or not self._can_edit_products:
            return rx.toast.error("У Вас немає дозволу на редагування переліку ТМЦ!")
        if index < 0 or index >= len(self.item.movement.products_catalog):
            return
        pc = self.item.movement.products_catalog[index]
        if pc.id is not None and pc.id > 0:
            flag, text = AdmissionDAO.delete_product_line(pc.id)
            if not flag:
                return rx.toast.error(text)
        del self.item.movement.products_catalog[index]
        self._recompute_total()
        return rx.toast.success("Позицію видалено!")

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

        flag, text, id = AdmissionDAO.edit_one(self.item)
        if flag:
            yield rx.toast.success(text)
            yield ListAdmissionState.on_load()
            yield rx.redirect(f"{routes.MOVEMENT_ADMISSIONS_VIEW_ID}{id}")
            return
        yield rx.toast.error(text)


class ViewAdmissionState(AppState):
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
        if not self.has_permission(Action.ADMISSIONS_VIEW):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
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
    ) -> List[Tuple[int, MovementProductsCatalog, str, str]]:
        return [
            (index, pc, _format_money(pc.price), _format_money(pc.count * pc.price))
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

    @rx.var
    def subtotal_display(self) -> str:
        line_total = sum(pc.count * pc.price for pc in self.item.movement.products_catalog)
        rate = (self.item.nds_rate.rate / 100.0) if self.item.nds_rate is not None else 0.0
        if rate <= 0:
            return _format_money(line_total)
        if self.item.flag_nds:
            return _format_money(line_total / (1 + rate))
        return _format_money(line_total)

    @rx.var
    def nds_amount_display(self) -> str:
        line_total = sum(pc.count * pc.price for pc in self.item.movement.products_catalog)
        rate = (self.item.nds_rate.rate / 100.0) if self.item.nds_rate is not None else 0.0
        if rate <= 0:
            return _format_money(0)
        if self.item.flag_nds:
            subtotal = line_total / (1 + rate)
            return _format_money(line_total - subtotal)
        return _format_money(line_total * rate)

    @rx.var
    def total_display(self) -> str:
        line_total = sum(pc.count * pc.price for pc in self.item.movement.products_catalog)
        rate = (self.item.nds_rate.rate / 100.0) if self.item.nds_rate is not None else 0.0
        if rate <= 0 or self.item.flag_nds:
            return _format_money(line_total)
        return _format_money(line_total * (1 + rate))

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
        if any(m.id != self.item.id for m in related_movements):
            self.cancel_conflict_movements = related_movements
            self.is_cancel_conflict_dialog_open = True
            yield rx.toast.error("Видалення неможливе: товар бере участь у пізніших рухах!")
            return

        flag, text = AdmissionDAO.delete_one(self.item.id)
        if flag:
            yield rx.toast.success(text)
            yield rx.redirect(routes.MOVEMENT_ADMISSIONS)
            return
        yield rx.toast.error(text)
