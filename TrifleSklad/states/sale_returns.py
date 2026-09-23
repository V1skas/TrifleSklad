from typing import Dict, List, Optional, Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.dao_legacy import (
    MovementDAO,
    ProductDAO,
    SaleDAO,
    SaleReturnDAO,
    StorageDAO,
)
from TrifleSklad.declared import (
    MovementsStatus,
    MovementsType,
    StorageType,
    format_transferred_qty,
    movements_status_list,
    movements_type_list,
)
from TrifleSklad.models import Movement, Product, SaleReturn
from TrifleSklad.movement.list_mixin import MovementListFilterMixin
from TrifleSklad.services.errors import ServiceError
from TrifleSklad.services.movement_edit import FullEditPayload, MovementEditService
from TrifleSklad.states.app import AppState
from TrifleSklad.states.audit_mixin import AuditHistoryMixin
from TrifleSklad.states.movement_cancel_mixin import CancelWithReasonMixin
from TrifleSklad.states.movement_edit_mixin import FullEditMixin
from TrifleSklad.utils.clock import now_local


class ListSaleReturnsState(MovementListFilterMixin, AppState):
    items: List[SaleReturn] = []
    in_progress: bool = True

    def _reload(self):
        self._all_pages, self.items = SaleReturnDAO.get_paginated(
            self._current_page,
            self._limit,
            self._date_from_eff(),
            self._date_to_eff(),
            self.selected_statuses,
            destination_storage=self.filter_destination_storage,
            catalog_ids=self.selected_catalog_ids,
        )

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list

    @rx.event
    def on_load(self):
        guard = self.access_guard(Action.SALE_RETURNS_LIST)
        if guard is not None:
            yield guard
            return
        self.in_progress = True
        self._enter_list()
        self._reload()
        self.in_progress = False

    @rx.event
    def on_click_add(self):
        return rx.redirect(routes.MOVEMENT_SALE_RETURNS_ADD)


class ViewSaleReturnsState(CancelWithReasonMixin, AuditHistoryMixin, AppState):
    HISTORY_TABLE = "sale_returns"
    HISTORY_ACTION = Action.SALE_RETURNS_HISTORY
    HISTORY_DETAIL_ACTION = Action.SALE_RETURNS_HISTORY_DETAIL

    item: Optional[SaleReturn] = None
    in_process: bool = True

    expanded_positions: Dict[int, bool] = {}

    cancel_conflict_movements: List[Movement] = []
    is_cancel_conflict_dialog_open: bool = False

    @rx.var
    def item_status(self) -> str:
        return (
            movements_status_list[self.item.movement.status]
            if self.item is not None
            else ""
        )

    @rx.var
    def current_is_canceled(self) -> bool:
        return (
            self.item is not None
            and self.item.movement.status == MovementsStatus.CANCELED
        )

    @rx.var
    def positions_grouped(
        self,
    ) -> List[Tuple[int, str, str, float, List[Tuple[int, str, str, bool]]]]:
        if self.item is None:
            return []
        result: List[Tuple[int, str, str, float, List[Tuple[int, str, str, bool]]]] = []
        for index, pc in enumerate(self.item.movement.products_catalog):
            units: List[Tuple[int, str, str, bool]] = []
            for unit in pc.products:
                catalog = unit.product_catalog
                serial = (
                    unit.serial_number
                    if (catalog is not None and catalog.uniq and unit.serial_number)
                    else "—"
                )
                remain = (
                    str(unit.count)
                    if (catalog is not None and catalog.divisible)
                    else "—"
                )
                units.append((unit.id, serial, remain, unit.excluded_from_accounting))
            product = pc.product
            total_amount = sum(unit.count or 0 for unit in pc.products)
            result.append(
                (
                    index,
                    product.title,
                    format_transferred_qty(
                        total_amount,
                        pc.count,
                        product.divisible,
                        product.capacity,
                        product.no_fixed_capacity,
                    ),
                    pc.price,
                    units,
                )
            )
        return result

    @rx.var
    def total_cost(self) -> float:
        return (
            self.item.movement.total_cost
            if self.item is not None and self.item.movement.total_cost is not None
            else 0.0
        )

    @rx.var
    def source_sale_url(self) -> str:
        return (
            f"{routes.MOVEMENT_SALES_VIEW_ID}{self.item.id_sale}"
            if self.item is not None
            else ""
        )

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

    @rx.event
    def toggle_position(self, index: int):
        self.expanded_positions[index] = not self.expanded_positions.get(index, False)

    @rx.event
    def on_click_edit(self):
        if self.item is None:
            return
        return rx.redirect(routes.MOVEMENT_SALE_RETURNS_EDIT_ID + str(self.item.id))

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        guard = self.access_guard(Action.SALE_RETURNS_VIEW)
        if guard is not None:
            yield guard
            return
        self.in_process = True
        self.item = SaleReturnDAO.get_by_id_with_all_relationship(int(id))
        if self.item is None:
            self.in_process = False
            yield rx.redirect(routes.MOVEMENT_SALE_RETURNS)
            yield rx.toast.error("Запис не знайдено!")
            return
        self.expanded_positions = {
            index: True
            for index in range(len(self.item.movement.products_catalog))
        }
        self._load_history(self.item.id)
        self.in_process = False

    @rx.event
    def on_click_cancel(self):
        if not self.has_permission(Action.SALE_RETURNS_DELETE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None:
            yield rx.toast.error("Не обрано запис для скасування!")
            return
        if self.item.movement.status == MovementsStatus.CANCELED:
            yield rx.toast.error("Повернення вже скасовано!")
            return

        list_id_products: List[int] = []
        for pc in self.item.movement.products_catalog:
            for product in pc.products:
                list_id_products.append(product.id)

        related_movements = MovementDAO.get_with_products_from_id(list_id_products, self.item.id)
        if related_movements:
            self.cancel_conflict_movements = related_movements
            self.is_cancel_conflict_dialog_open = True
            yield rx.toast.error("Скасування неможливе: товар бере участь у пізніших рухах!")
            return

        flag, text = MovementDAO.cancel_movement(self.item.id, self.user.login, reason=self.cancel_reason)
        if not flag:
            yield rx.toast.error(text)
            return

        ProductDAO.delete_list(list_id_products)
        yield rx.toast.success("Повернення продажу скасовано!")
        yield ListSaleReturnsState.on_load()
        yield rx.redirect(f"{routes.MOVEMENT_SALE_RETURNS_VIEW_ID}{self.item.id}")


class AddSaleReturnsState(AppState):
    current_date: str = ""

    id_destination_storage: str = ""
    status: str = ""
    comment: str = ""

    selected_sale_id: str = ""
    sale_locked: bool = False
    sale_label: str = ""
    list_sales: List[Tuple[str, str]] = []
    list_warehouses: List[Tuple[str, str]] = []

    units: List[Product] = []
    selected_units: Dict[int, bool] = {}
    compensations: Dict[int, str] = {}
    expanded_catalogs: Dict[int, bool] = {}
    excluded: Dict[int, bool] = {}

    def _load_warehouses(self):
        self.list_warehouses = [
            (s.title, str(s.id))
            for s in StorageDAO.get_all_by_type(StorageType.WAREHOUSE)
        ]

    def _load_sales(self):
        self.list_sales = [
            (f"№{s.id} від {s.movement.date}", str(s.id))
            for s in SaleReturnDAO.get_returnable_sales()
        ]

    def _load_units(self, sale_id: int):
        self.units = SaleReturnDAO.get_sale_units(sale_id)
        self.selected_units = {p.id: True for p in self.units}
        self.compensations = {p.id: "" for p in self.units}
        self.expanded_catalogs = {
            p.product_catalog.id: True
            for p in self.units
            if p.product_catalog is not None
        }
        self.excluded = {p.id: False for p in self.units}

    def _status_index(self) -> int:
        for index, status_text in enumerate(movements_status_list):
            if status_text == self.status:
                return index
        return MovementsStatus.CREATED

    def _catalog_of(self, unit_id: int) -> Optional[int]:
        for p in self.units:
            if p.id == unit_id and p.product_catalog is not None:
                return p.product_catalog.id
        return None

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
    def has_sale(self) -> bool:
        return self.selected_sale_id != ""

    @rx.var
    def grouped_units(
        self,
    ) -> List[Tuple[int, str, str, str, List[Tuple[int, str, str]]]]:
        order: List[int] = []
        groups: Dict[
            int, Tuple[str, bool, bool, float, float, List[Tuple[int, str, str]]]
        ] = {}
        for product in self.units:
            catalog = product.product_catalog
            if catalog is None:
                continue
            if catalog.id not in groups:
                order.append(catalog.id)
                groups[catalog.id] = (
                    catalog.title,
                    catalog.divisible,
                    bool(catalog.no_fixed_capacity),
                    catalog.capacity or 0,
                    0,
                    [],
                )
            title, divisible, no_fixed, capacity, remainder, units = groups[catalog.id]
            serial = (
                product.serial_number
                if (catalog.uniq and product.serial_number)
                else "—"
            )
            remain = str(product.count) if catalog.divisible else "—"
            units.append((product.id, serial, remain))
            groups[catalog.id] = (
                title,
                divisible,
                no_fixed,
                capacity,
                remainder + (product.count or 0),
                units,
            )
        result: List[Tuple[int, str, str, str, List[Tuple[int, str, str]]]] = []
        for catalog_id in order:
            title, divisible, no_fixed, capacity, remainder, units = groups[catalog_id]
            result.append(
                (
                    catalog_id,
                    title,
                    format_transferred_qty(remainder, len(units), divisible, capacity, no_fixed),
                    str(remainder) if divisible else "—",
                    units,
                )
            )
        return result

    def _unit_compensation(self, unit_id: int) -> float:
        raw = self.compensations.get(unit_id, "")
        try:
            return float(raw) if raw not in (None, "") else 0.0
        except (TypeError, ValueError):
            return 0.0

    @rx.var
    def position_sums(self) -> Dict[int, float]:
        sums: Dict[int, float] = {}
        for product in self.units:
            if product.product_catalog is None:
                continue
            if not self.selected_units.get(product.id, False):
                continue
            catalog_id = product.product_catalog.id
            sums[catalog_id] = round(
                sums.get(catalog_id, 0.0) + self._unit_compensation(product.id), 2
            )
        return sums

    @rx.var
    def total_compensation(self) -> float:
        total = 0.0
        for unit_id, selected in self.selected_units.items():
            if selected:
                total += self._unit_compensation(unit_id)
        return round(total, 2)

    def _bind_sale(self, sale_id: int):
        sale = SaleDAO.get_by_id_with_all_relationship(sale_id)
        if sale is None:
            return
        self.selected_sale_id = str(sale_id)
        self.sale_locked = True
        self.sale_label = f"№{sale.id} від {sale.movement.date}"
        if sale.movement.id_incoming_storage is not None:
            self.id_destination_storage = str(sale.movement.id_incoming_storage)
        self._load_units(sale_id)

    @rx.event
    def on_load(self, id: str = ""):
        guard = self.access_guard(Action.SALE_RETURNS_CREATE)
        if guard is not None:
            yield guard
            return

        self.current_date = now_local().date().__str__()
        self.id_destination_storage = ""
        self.status = ""
        self.comment = ""
        self.selected_sale_id = ""
        self.sale_locked = False
        self.sale_label = ""
        self.units = []
        self.selected_units = {}
        self.compensations = {}
        self.expanded_catalogs = {}
        self.excluded = {}

        self._load_warehouses()
        self._load_sales()

        if id != "" and id.lstrip("-").isdigit() and int(id) > 0:
            self._bind_sale(int(id))

    @rx.event
    def on_change_sale(self, value: str):
        self.selected_sale_id = value
        if value == "":
            self.units = []
            self.selected_units = {}
            self.compensations = {}
            self.expanded_catalogs = {}
            self.excluded = {}
            return
        sale = SaleDAO.get_by_id_with_all_relationship(int(value))
        if sale is None:
            self.selected_sale_id = ""
            yield rx.toast.error("Продаж не знайдено!")
            return
        if sale.movement.id_incoming_storage is not None:
            self.id_destination_storage = str(sale.movement.id_incoming_storage)
        self._load_units(int(value))

    @rx.event
    def on_change_id_destination_storage(self, value: str):
        self.id_destination_storage = value

    @rx.event
    def toggle_catalog(self, catalog_id: int):
        self.expanded_catalogs[catalog_id] = not self.expanded_catalogs.get(catalog_id, False)

    @rx.event
    def toggle_unit(self, unit_id: int, checked: bool):
        self.selected_units[unit_id] = checked

    @rx.event
    def set_compensation(self, unit_id: int, value: str):
        self.compensations[unit_id] = value

    @rx.event
    def set_excluded(self, unit_id: int, value: bool):
        self.excluded[unit_id] = value

    @rx.event
    def on_change_status(self, value: str):
        self.status = value

    @rx.event
    def on_change_date(self, value: str):
        self.current_date = value

    @rx.event
    def on_change_comment(self, value: str):
        self.comment = value

    @rx.event
    def add_one(self):
        if not self.has_permission(Action.SALE_RETURNS_CREATE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.selected_sale_id == "":
            yield rx.toast.error("Не обрано продаж для повернення!")
            return
        if self.id_destination_storage == "":
            yield rx.toast.error("Не обрано склад призначення!")
            return
        if not StorageDAO.is_type(int(self.id_destination_storage), StorageType.WAREHOUSE):
            yield rx.toast.error("Повертати ТМЦ можна лише на склад!")
            return

        selected_ids = [uid for uid, sel in self.selected_units.items() if sel]
        if len(selected_ids) == 0:
            yield rx.toast.error("Оберіть хоча б одну одиницю для повернення!")
            return

        compensations: Dict[int, float] = {}
        for unit_id in selected_ids:
            catalog_id = self._catalog_of(unit_id)
            if catalog_id is None:
                continue
            raw = self.compensations.get(unit_id, "")
            if raw not in (None, ""):
                try:
                    value = float(raw)
                except (TypeError, ValueError):
                    yield rx.toast.error("Невірна компенсована вартість для однієї з одиниць!")
                    return
                if value < 0:
                    yield rx.toast.error("Компенсована вартість не може бути від'ємною!")
                    return
            else:
                value = 0.0
            compensations[catalog_id] = round(compensations.get(catalog_id, 0.0) + value, 2)

        form_data = {
            "id_sale": int(self.selected_sale_id),
            "date": self.current_date,
            "id_destination_storage": int(self.id_destination_storage),
            "status": self._status_index(),
            "comment": self.comment,
            "product_ids": selected_ids,
            "compensations": compensations,
            "id_user": self.user.login,
        }

        flag, text, id = SaleReturnDAO.add_one(form_data, self.user.login)
        if flag:
            ProductDAO.set_excluded_flags(
                {uid: self.excluded.get(uid, False) for uid in selected_ids}
            )
            yield rx.toast.success("Повернення продажу проведено!")
            yield ListSaleReturnsState.on_load()
            yield rx.redirect(f"{routes.MOVEMENT_SALE_RETURNS_VIEW_ID}{id}", replace=True)
            return
        yield rx.toast.error(text)


class EditSaleReturnsState(FullEditMixin, AppState):
    MOVEMENT_TYPE = MovementsType.SALE_RETURN

    item: Optional[SaleReturn] = None
    in_process: bool = True
    status: str = ""

    id_destination_storage: str = ""
    selected_sale_id: str = ""
    list_sales: List[Tuple[str, str]] = []
    list_warehouses: List[Tuple[str, str]] = []

    # Повернення продажу не використовує спільний віджет вибору одиниць: ТМЦ
    # уже продано (is_deleted=True), тож перелік будується з одиниць вихідного
    # продажу — так само, як на сторінці додавання.
    units: List[Product] = []
    selected_units: Dict[int, bool] = {}
    compensations: Dict[int, str] = {}
    expanded_catalogs: Dict[int, bool] = {}
    excluded: Dict[int, bool] = {}

    def _load_warehouses(self):
        self.list_warehouses = [
            (s.title, str(s.id)) for s in StorageDAO.get_all_by_type(StorageType.WAREHOUSE)
        ]

    def _load_sales(self):
        sales = {str(s.id): f"№{s.id} від {s.movement.date}" for s in SaleReturnDAO.get_returnable_sales()}
        # Вихідний продаж цього повернення міг «зникнути» зі списку доступних
        # (усі його одиниці вже повернені) — але лишатись обраним він мусить.
        if self.selected_sale_id != "" and self.selected_sale_id not in sales:
            sale = SaleDAO.get_by_id_with_all_relationship(int(self.selected_sale_id))
            if sale is not None:
                sales[self.selected_sale_id] = f"№{sale.id} від {sale.movement.date}"
        self.list_sales = [(title, sale_id) for sale_id, title in sales.items()]

    def _load_units(self, sale_id: int, movement_id: int, selected_ids: Optional[List[int]] = None):
        self.units = SaleReturnDAO.get_sale_units_for_edit(sale_id, movement_id)
        chosen = set(selected_ids) if selected_ids is not None else {p.id for p in self.units}
        self.selected_units = {p.id: p.id in chosen for p in self.units}
        self.compensations = {p.id: self.compensations.get(p.id, "") for p in self.units}
        self.expanded_catalogs = {
            p.product_catalog.id: True for p in self.units if p.product_catalog is not None
        }
        self.excluded = {p.id: p.excluded_from_accounting for p in self.units}

    def _catalog_of(self, unit_id: int) -> Optional[int]:
        for p in self.units:
            if p.id == unit_id and p.product_catalog is not None:
                return p.product_catalog.id
        return None

    def _unit_compensation(self, unit_id: int) -> float:
        raw = self.compensations.get(unit_id, "")
        try:
            return float(raw) if raw not in (None, "") else 0.0
        except (TypeError, ValueError):
            return 0.0

    @rx.var
    def grouped_units(self) -> List[Tuple[int, str, str, str, List[Tuple[int, str, str]]]]:
        order: List[int] = []
        groups: Dict[int, Tuple[str, bool, bool, float, float, List[Tuple[int, str, str]]]] = {}
        for product in self.units:
            catalog = product.product_catalog
            if catalog is None:
                continue
            if catalog.id not in groups:
                order.append(catalog.id)
                groups[catalog.id] = (
                    catalog.title,
                    catalog.divisible,
                    bool(catalog.no_fixed_capacity),
                    catalog.capacity or 0,
                    0,
                    [],
                )
            title, divisible, no_fixed, capacity, remainder, units = groups[catalog.id]
            serial = product.serial_number if (catalog.uniq and product.serial_number) else "—"
            remain = str(product.count) if catalog.divisible else "—"
            units.append((product.id, serial, remain))
            groups[catalog.id] = (
                title,
                divisible,
                no_fixed,
                capacity,
                remainder + (product.count or 0),
                units,
            )
        result: List[Tuple[int, str, str, str, List[Tuple[int, str, str]]]] = []
        for catalog_id in order:
            title, divisible, no_fixed, capacity, remainder, units = groups[catalog_id]
            result.append(
                (
                    catalog_id,
                    title,
                    format_transferred_qty(remainder, len(units), divisible, capacity, no_fixed),
                    str(remainder) if divisible else "—",
                    units,
                )
            )
        return result

    @rx.var
    def position_sums(self) -> Dict[int, float]:
        sums: Dict[int, float] = {}
        for product in self.units:
            if product.product_catalog is None or not self.selected_units.get(product.id, False):
                continue
            catalog_id = product.product_catalog.id
            sums[catalog_id] = round(sums.get(catalog_id, 0.0) + self._unit_compensation(product.id), 2)
        return sums

    @rx.var
    def total_compensation(self) -> float:
        total = 0.0
        for unit_id, selected in self.selected_units.items():
            if selected:
                total += self._unit_compensation(unit_id)
        return round(total, 2)

    @rx.event
    def toggle_catalog(self, catalog_id: int):
        self.expanded_catalogs[catalog_id] = not self.expanded_catalogs.get(catalog_id, False)

    @rx.event
    def toggle_unit(self, unit_id: int, checked: bool):
        if self.can_edit_full:
            self.selected_units[unit_id] = checked

    @rx.event
    def set_compensation(self, unit_id: int, value: str):
        if self.can_edit_full:
            self.compensations[unit_id] = value

    @rx.event
    def set_excluded(self, unit_id: int, value: bool):
        if self.can_edit_full:
            self.excluded[unit_id] = value

    @rx.event
    def on_change_sale(self, value: str):
        if not self.can_edit_full or value == "":
            return
        sale = SaleDAO.get_by_id_with_all_relationship(int(value))
        if sale is None:
            yield rx.toast.error("Продаж не знайдено!")
            return
        self.selected_sale_id = value
        if sale.movement.id_incoming_storage is not None:
            self.id_destination_storage = str(sale.movement.id_incoming_storage)
        self.compensations = {}
        self._load_units(int(value), self.item.id, selected_ids=[])
        yield rx.toast.warning("Перелік одиниць оновлено — оберіть, що саме повертається!")

    @rx.event
    def on_change_id_destination_storage(self, value: str):
        if self.can_edit_full:
            self.id_destination_storage = value

    def _status_index(self) -> int:
        for index, status_text in enumerate(movements_status_list):
            if status_text == self.status:
                return index
        return MovementsStatus.CREATED

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

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        guard = self.access_guard(Action.SALE_RETURNS_EDIT)
        if guard is not None:
            yield guard
            return
        self.in_process = True
        self.item = SaleReturnDAO.get_by_id_with_all_relationship(int(id))
        if self.item is None:
            self.in_process = False
            yield rx.redirect(routes.MOVEMENT_SALE_RETURNS)
            yield rx.toast.error("Запис не знайдено!")
            return
        self.status = movements_status_list[self.item.movement.status]
        self.selected_sale_id = str(self.item.id_sale)
        self.id_destination_storage = str(self.item.movement.id_destination_storage)

        self._load_warehouses()
        self._load_sales()
        self._load_editability(self.item.id)

        current_ids = [
            product.id
            for position in self.item.movement.products_catalog
            for product in position.products
        ]
        self.compensations = {}
        self._load_units(self.item.id_sale, self.item.id, selected_ids=current_ids)
        # Компенсація зберігається на позицію каталогу — при редагуванні
        # розкладаємо її по обраних одиницях цієї позиції порівну.
        for position in self.item.movement.products_catalog:
            unit_ids = [product.id for product in position.products]
            if not unit_ids:
                continue
            per_unit = round(position.price / len(unit_ids), 2)
            for unit_id in unit_ids:
                self.compensations[unit_id] = str(per_unit)
        self.in_process = False

    @rx.event
    def on_change_status(self, value: str):
        self.status = value

    @rx.event
    def on_change_comment(self, value: str):
        if self.item is not None:
            self.item.movement.comment = value

    @rx.event
    def edit_one(self):
        if not self.has_permission(Action.SALE_RETURNS_EDIT):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None:
            yield rx.toast.error("Запис не завантажено!")
            return
        if self.item.movement.status == MovementsStatus.CANCELED:
            yield rx.toast.error("Повернення вже скасовано!")
            return

        status_index = self._status_index()
        if status_index == MovementsStatus.CANCELED:
            yield rx.toast.error(
                "Скасування виконується кнопкою «Скасувати», а не через редагування!"
            )
            return

        if self.can_edit_full:
            if not StorageDAO.is_type(int(self.id_destination_storage), StorageType.WAREHOUSE):
                yield rx.toast.error("Повертати ТМЦ можна лише на склад!")
                return
            selected_ids = [uid for uid, sel in self.selected_units.items() if sel]
            if len(selected_ids) == 0:
                yield rx.toast.error("Оберіть хоча б одну одиницю для повернення!")
                return
            compensations: Dict[int, float] = {}
            for unit_id in selected_ids:
                catalog_id = self._catalog_of(unit_id)
                if catalog_id is None:
                    continue
                value = self._unit_compensation(unit_id)
                if value < 0:
                    yield rx.toast.error("Компенсована вартість не може бути від'ємною!")
                    return
                compensations[catalog_id] = round(compensations.get(catalog_id, 0.0) + value, 2)

            sale = SaleDAO.get_by_id_with_all_relationship(int(self.selected_sale_id))
            if sale is None:
                yield rx.toast.error("Продаж не знайдено!")
                return
            # Власником повернених одиниць стає той, з ким їх було продано.
            last_owner = sale.movement.id_incoming_owner
            try:
                MovementEditService().save_full(
                    FullEditPayload(
                        movement_id=self.item.id,
                        movement_type=MovementsType.SALE_RETURN,
                        reason=self.edit_reason,
                        header={
                            "id_incoming_owner": last_owner,
                            "id_destination_owner": last_owner,
                            "id_destination_storage": int(self.id_destination_storage),
                            "status": status_index,
                            "comment": self.item.movement.comment,
                        },
                        child={"id_sale": int(self.selected_sale_id)},
                        unit_plan=[(unit_id, None) for unit_id in selected_ids],
                        prices=compensations,
                    ),
                    self.user.login,
                )
            except ServiceError as e:
                yield rx.toast.error(str(e))
                return
            ProductDAO.set_excluded_flags(
                {uid: self.excluded.get(uid, False) for uid in selected_ids}
            )
            yield rx.toast.success("Повернення продажу змінено!")
            yield ListSaleReturnsState.on_load()
            yield rx.redirect(f"{routes.MOVEMENT_SALE_RETURNS_VIEW_ID}{self.item.id}", replace=True)
            return

        form_data = {
            "id": self.item.id,
            "status": status_index,
            "comment": self.item.movement.comment,
        }
        flag, text, id = SaleReturnDAO.edit_one(form_data, self.user.login)
        if flag:
            yield rx.toast.success("Повернення продажу змінено!")
            yield ListSaleReturnsState.on_load()
            yield rx.redirect(f"{routes.MOVEMENT_SALE_RETURNS_VIEW_ID}{id}", replace=True)
            return
        yield rx.toast.error(text)
