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
    StorageType,
    movements_status_list,
    movements_type_list,
)
from TrifleSklad.models import Movement, Product, SaleReturn
from TrifleSklad.movement.list_mixin import MovementListFilterMixin
from TrifleSklad.states.app import AppState
from TrifleSklad.states.audit_mixin import AuditHistoryMixin
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
        )

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def get_movement_statuses(self) -> List[str]:
        return movements_status_list

    @rx.event
    def on_load(self):
        if not self.has_permission(Action.SALE_RETURNS_LIST):
            yield rx.redirect(routes.WELCOME)
            yield rx.toast.error("У Вас немає дозволу на перегляд цієї сторінки!")
            return
        self.in_progress = True
        self._reset_list_state()
        self._reload()
        self.in_progress = False

    @rx.event
    def on_click_add(self):
        return rx.redirect(routes.MOVEMENT_SALE_RETURNS_ADD)


class ViewSaleReturnsState(AuditHistoryMixin, AppState):
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
    ) -> List[Tuple[int, str, int, float, List[Tuple[int, str, str]]]]:
        if self.item is None:
            return []
        result: List[Tuple[int, str, int, float, List[Tuple[int, str, str]]]] = []
        for index, pc in enumerate(self.item.movement.products_catalog):
            units: List[Tuple[int, str, str]] = []
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
                units.append((unit.id, serial, remain))
            result.append((index, pc.product.title, pc.count, pc.price, units))
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
        if not self.has_permission(Action.SALE_RETURNS_VIEW):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
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
        if any(m.id != self.item.id for m in related_movements):
            self.cancel_conflict_movements = related_movements
            self.is_cancel_conflict_dialog_open = True
            yield rx.toast.error("Скасування неможливе: товар бере участь у пізніших рухах!")
            return

        flag, text = MovementDAO.cancel_movement(self.item.id, self.user.login)
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
    ) -> List[Tuple[int, str, int, str, List[Tuple[int, str, str]]]]:
        order: List[int] = []
        groups: Dict[int, Tuple[str, bool, int, List[Tuple[int, str, str]]]] = {}
        for product in self.units:
            catalog = product.product_catalog
            if catalog is None:
                continue
            if catalog.id not in groups:
                order.append(catalog.id)
                groups[catalog.id] = (catalog.title, catalog.divisible, 0, [])
            title, divisible, remainder, units = groups[catalog.id]
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
                remainder + (product.count or 0),
                units,
            )
        result: List[Tuple[int, str, int, str, List[Tuple[int, str, str]]]] = []
        for catalog_id in order:
            title, divisible, remainder, units = groups[catalog_id]
            result.append(
                (
                    catalog_id,
                    title,
                    len(units),
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
        if not self.has_permission(Action.SALE_RETURNS_CREATE):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
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
            yield rx.toast.success("Повернення продажу проведено!")
            yield ListSaleReturnsState.on_load()
            yield rx.redirect(f"{routes.MOVEMENT_SALE_RETURNS_VIEW_ID}{id}")
            return
        yield rx.toast.error(text)


class EditSaleReturnsState(AppState):
    item: Optional[SaleReturn] = None
    in_process: bool = True
    status: str = ""

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
        if not self.has_permission(Action.SALE_RETURNS_EDIT):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        self.in_process = True
        self.item = SaleReturnDAO.get_by_id_with_all_relationship(int(id))
        if self.item is None:
            self.in_process = False
            yield rx.redirect(routes.MOVEMENT_SALE_RETURNS)
            yield rx.toast.error("Запис не знайдено!")
            return
        self.status = movements_status_list[self.item.movement.status]
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

        form_data = {
            "id": self.item.id,
            "status": status_index,
            "comment": self.item.movement.comment,
        }
        flag, text, id = SaleReturnDAO.edit_one(form_data, self.user.login)
        if flag:
            yield rx.toast.success("Повернення продажу змінено!")
            yield ListSaleReturnsState.on_load()
            yield rx.redirect(f"{routes.MOVEMENT_SALE_RETURNS_VIEW_ID}{id}")
            return
        yield rx.toast.error(text)
