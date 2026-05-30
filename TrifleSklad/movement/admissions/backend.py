from datetime import date
from typing import List, Optional, Tuple

import reflex as rx

import TrifleSklad.routes as routes
from TrifleSklad.dao import (
    AdmissionDAO,
    NDSRateDAO,
    OwnerDAO,
    PaymentTypeDAO,
    ProductCatalogDAO,
    StorageDAO,
    SupplierDAO,
)
from TrifleSklad.declared import (
    MovementsStatus,
    MovementsType,
    StorageType,
    movements_status_list,
)
from TrifleSklad.models import (
    Admission,
    Movement,
    MovementProductsCatalog,
    Product,
    ProductCatalog,
)
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

    error_count: bool = False
    error_price: bool = False
    # ======================

    # Dynamic variables
    # ======================
    @rx.var
    def products_catalog_list(self) -> List[Tuple[str, str]]:
        self.cache_products_catalog_list = ProductCatalogDAO.get_all_exclude_ids(
            self.exclude_products_catalog_list
        )
        return [
            (item[1].title, str(item[0]))
            for item in enumerate(self.cache_products_catalog_list)
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
    def __load_products_catalog_list(self):
        self.cache_products_catalog_list = ProductCatalogDAO.get_all_exclude_ids(
            self.exclude_products_catalog_list
        )

    def set_exclude_products_catalog_list(self, exclude_list: List[int]):
        self.exclude_products_catalog_list = exclude_list
        self.__load_products_catalog_list()

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
        return str(self.item.price)

    # ======================

    # Event handlers for form fields
    # ======================
    @rx.event
    def on_change_id_product_catalog(self, value: str):
        self.id_product_catalog_in_cache = value
        self.item.product = self.cache_products_catalog_list[int(value)]
        self.item.id_product_catalog = self.item.product.id
        if self.is_product_uniq and not self.item.product.uniq:
            for i in range(self.item.count):
                self.item.products[i].serial_number = ""
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

        for _ in range(int(value) - list_len):
            self.item.products.append(
                Product(
                    id_product_catalog=self.item.id_product_catalog,
                    id_storage=-1,
                    id_owner=-1,
                    serial_number="",
                    count=1,
                )
            )

    @rx.event
    def on_change_serial_numbers(self, index: int, value: str):
        if index < len(self.item.products):
            self.item.products[index].serial_number = value

    @rx.event
    def on_change_price(self, value: str):
        try:
            self.item.price = float(value)
        except ValueError:
            self.error_price = True
            return

        self.__check_price_correct()
        if self.error_price:
            return

    # ======================

    # Action handlers
    # ======================
    @rx.event
    def set_item(self, item: MovementProductsCatalog):
        self.item = item

        self.is_product_uniq = item.product.uniq
        self.id_product_catalog_entered = True

    @rx.event
    def clear(self):
        self.item = MovementProductsCatalog(
            count=0, price=0.0, id_product_catalog=-1, products=[]
        )

        self.is_product_uniq = False
        self.id_product_catalog_entered = False
        self.id_product_catalog_in_cache = ""
        self.error_count = False
        self.error_price = False

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


class ListAdmissionState(rx.State):
    items: List[Admission] = []

    # Dynamic variables
    # ======================
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
    def refresh_list(self):
        self.items = AdmissionDAO.get_all_with_supplier_movement_storage_owner()

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

    # Backend only
    # ======================
    def __load_suppliers(self):
        self.list_suppliers = [
            (item.title, str(item.id)) for item in SupplierDAO.get_all()
        ]

    def __load_storages(self):
        self.list_storages = [
            (item.title, str(item.id))
            for item in StorageDAO.get_all()
            if item.type == StorageType.WAREHOUSE
            and (
                self.search_name_destination_storage == ""
                or self.search_name_destination_storage.lower() in item.title.lower()
            )
        ]

    def __load_owners(self):
        self.list_owners = [(item.title, str(item.id)) for item in OwnerDAO.get_all()]

    def __load_payment_types(self):
        self.list_payment_types = [
            (item.title, str(item.id)) for item in PaymentTypeDAO.get_all()
        ]

    def __load_nds_rates(self):
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

    async def _on_load(self):
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

        self.__load_suppliers()
        self.__load_storages()
        self.__load_owners()
        self.__load_payment_types()
        self.__load_nds_rates()

        self.addedit_product_catalog_form_state = await self.get_state(
            MovementProductCatalogAddEditFormState
        )
        self.view_product_catalog_form_state = await self.get_state(
            MovementProductCatalogDetailedViewState
        )        
        
    async def on_load(self):
        await self._on_load()

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
        self.__load_storages()

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
        self.item.movement.id_user = (await self.get_state(AppState)).user.login

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


class EditAdmissionState(AddAdmissionState):
    # Backend only
    # ======================
    async def on_load(self, id: int):
        await super()._on_load()
        self.item = AdmissionDAO.get_by_id_with_all_relationship(id)

    # ======================

    # Action handlers
    # ======================
    @rx.event
    async def add_one(self):
        print("Use edit_one method instead of add_one in EditAdmissionState")

    @rx.event
    async def edit_one(self):
        self.item.movement.id_user = (await self.get_state(AppState)).user.login

        flag, text, id = AdmissionDAO.edit_one(self.item)
        if flag:
            return [
                rx.toast.success(text),
                rx.redirect(f"{routes.MOVEMENT_ADMISSIONS_VIEW_ID}{id}"),
            ]
        return rx.toast.error(text)

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

    # Backend only
    # ======================
    async def on_load(self, id: int):
        self.view_product_catalog_form_state = await self.get_state(
            MovementProductCatalogDetailedViewState
        )
        self.item = AdmissionDAO.get_by_id_with_all_relationship(id)
        self.dialog_open = False
        self.current_product_catalog_index = -1

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
        NONE = "none"

    current_page: str = Pages.NONE

    add_addmission_form_state: Optional[AddAdmissionState] = None
    edit_admission_form_state: Optional[EditAdmissionState] = None
    view_admission_state: Optional[ViewAdmissionState] = None
    list_admission_state: Optional[ListAdmissionState] = None

    async def _check_path(self):
        page = self.router.page.params.get("page", "")
        if page != "":
            id = -1

            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                return rx.redirect(routes.MOVEMENT_ADMISSIONS)

            # /admisions/add
            if page == self.Pages.ADD:
                if self.add_addmission_form_state is None:
                    return rx.toast.error(
                        "Стан форми додавання постачання не ініціалізовано"
                    )
                await self.add_addmission_form_state.on_load()
                self.current_page = self.Pages.ADD
                return None
            # /admisions/edit/[id]
            elif page == self.Pages.EDIT:
                id = self.router.page.params.get("id", "")
                if id != "":
                    if self.edit_admission_form_state is None:
                        return rx.toast.error(
                            "Стан форми редагування постачання не ініціалізовано"
                        )
                    await self.edit_admission_form_state.on_load(int(id))
                    self.current_page = self.Pages.EDIT
                    return None
                else:
                    return rx.redirect(routes.MOVEMENT_ADMISSIONS)
            # /admisions/view/[id]
            elif page == self.Pages.VIEW:
                id = self.router.page.params.get("id", "")
                if id != "":
                    if self.view_admission_state is None:
                        return rx.toast.error(
                            "Стан перегляду постачання не ініціалізовано"
                        )
                    await self.view_admission_state.on_load(id)
                    self.current_page = self.Pages.VIEW
                    return None
                else:
                    return rx.redirect(routes.MOVEMENT_ADMISSIONS)
        else:
            # /admissions
            if self.list_admission_state is None:
                return rx.toast.error(
                    "Стан списку постачань не ініціалізовано"
                )
            self.list_admission_state.refresh_list()
            self.current_page = self.Pages.LIST
            return None

    @rx.event
    async def on_load(self):
        self.add_addmission_form_state = await self.get_state(AddAdmissionState)
        self.list_admission_state = await self.get_state(ListAdmissionState)
        self.view_admission_state = await self.get_state(ViewAdmissionState)
        self.edit_admission_form_state = await self.get_state(EditAdmissionState)
        await self._check_path()

    @rx.event
    def delete_one(self, id):
        if id != -1:
            flag, text = AdmissionDAO.delete_one(id)
            if flag:
                return [rx.toast.success(text), rx.redirect(routes.MOVEMENT_ADMISSIONS)]
            else:
                return [rx.toast.error(text)]
        return rx.toast.error("Не обрано запис для видалення!")
