import csv
import io
from typing import List, Optional, Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.dao_legacy import MovementDAO, OwnerDAO, ProductCategoryDAO, StorageDAO
from TrifleSklad.declared import (
    MovementsType,
    format_amount,
    format_transferred_qty,
    movements_status_list,
    movements_type_list,
)
from TrifleSklad.movement.list_mixin import SCROLL_TOP_SCRIPT
from TrifleSklad.services.product_catalog import ProductCatalogService
from TrifleSklad.states.app import AppState
from TrifleSklad.utils.clock import now_local

ALL = "all"


def _storage_owner_label(storage, owner) -> str:
    """«Склад (Власник)» або «Склад», або «—» — спільна розмітка джерела/
    призначення руху для звіту."""
    if storage is None:
        return "—"
    if owner is not None:
        return f"{storage.title} ({owner.title})"
    return storage.title


def _sender_label(movement, supplier_title: Optional[str]) -> str:
    """Відправник руху за типом: постачання → постачальник; повернення
    продажу → «Клієнт»; решта → склад/власник відправлення."""
    if movement.type == MovementsType.ADMISSION:
        return supplier_title or "—"
    if movement.type == MovementsType.SALE_RETURN:
        return "Клієнт"
    return _storage_owner_label(movement.incoming_storage, movement.incoming_owner)


def _receiver_label(movement) -> str:
    """Отримувач/призначення руху за типом: за наявності — склад/власник
    призначення; продаж → «Клієнт»; списання → «Списано»; інакше «—»."""
    if movement.destination_storage is not None:
        return _storage_owner_label(movement.destination_storage, movement.destination_owner)
    if movement.type == MovementsType.SALE:
        return "Клієнт"
    if movement.type == MovementsType.WRITE_OFF:
        return "Списано"
    return "—"


class CatalogMovementsReportState(AppState):
    in_progress: bool = True

    # (catalog_id, title, category_title, unit_display, delivered, issued, sold, returned, written_off, last_price, movement_count)
    rows: List[Tuple[int, str, str, str, str, str, str, str, str, str, str]] = []

    # Кеші опцій фільтрів.
    list_categories: List[Tuple[str, str]] = []
    _storages_cache: List[Tuple[str, str]] = []
    list_owners: List[Tuple[str, str]] = []

    # Фільтри (внутрішньо "" = без фільтра; селекти показують ALL).
    search_text: str = ""
    filter_category: str = ""
    filter_incoming_storage: str = ""
    filter_destination_storage: str = ""
    filter_incoming_owner: str = ""
    filter_destination_owner: str = ""
    date_from: str = ""
    date_to: str = ""
    exclude_canceled: bool = False

    # Пошук усередині селектів складів (їх може бути багато, зокрема клієнти).
    search_incoming_storage: str = ""
    search_destination_storage: str = ""

    _current_page: int = 1
    _all_pages: int = 1
    _limit: int = 20

    # Діалог зі списком рухів обраної позиції.
    is_movements_open: bool = False
    selected_title: str = ""
    selected_catalog_id: int = -1
    # Статистика обраної позиції для діалогу:
    dialog_unit: str = ""
    dialog_delivered: str = ""
    dialog_issued: str = ""
    dialog_sold: str = ""
    dialog_returned: str = ""
    dialog_written_off: str = ""
    dialog_price_history: str = ""
    # (id, тип, дата, відправник, отримувач, кількість, вартість_од, статус, view_url)
    movement_rows: List[Tuple[str, str, str, str, str, str, str, str, str]] = []

    # Пагінація діалогу (окрема від пагінації головної таблиці).
    _dialog_current_page: int = 1
    _dialog_all_pages: int = 1
    _dialog_limit: int = 20

    # Скид фільтрів/діалогу — лише при першому вході в сесії; повернення з
    # перегляду руху (повторний монтаж) зберігає фільтри й відкритий діалог.
    _initialized: bool = False

    def _load_filter_options(self):
        self.list_categories = ProductCategoryDAO.get_hierarchy_options()
        self._storages_cache = [(str(s.id), s.title) for s in StorageDAO.get_all()]
        self.list_owners = [(str(o.id), o.title) for o in OwnerDAO.get_all()]

    def _reload(self):
        count_items = MovementDAO.get_catalog_movement_summary_count(
            date_from=self.date_from,
            date_to=self.date_to,
            incoming_storage=self.filter_incoming_storage or None,
            destination_storage=self.filter_destination_storage or None,
            incoming_owner=self.filter_incoming_owner or None,
            destination_owner=self.filter_destination_owner or None,
            exclude_canceled=self.exclude_canceled,
            category_id=int(self.filter_category) if self.filter_category else None,
            search=self.search_text or None,
        )
        self._all_pages, catalog_rows = MovementDAO.get_catalog_movement_summary_paginated(
            page=self._current_page,
            limit=self._limit,
            count_items=count_items,
            date_from=self.date_from,
            date_to=self.date_to,
            incoming_storage=self.filter_incoming_storage or None,
            destination_storage=self.filter_destination_storage or None,
            incoming_owner=self.filter_incoming_owner or None,
            destination_owner=self.filter_destination_owner or None,
            exclude_canceled=self.exclude_canceled,
            category_id=int(self.filter_category) if self.filter_category else None,
            search=self.search_text or None,
        )

        catalog_ids = [r[0] for r in catalog_rows]
        stats = MovementDAO.get_catalog_movement_stats(
            catalog_ids,
            date_from=self.date_from,
            date_to=self.date_to,
            incoming_storage=self.filter_incoming_storage or None,
            destination_storage=self.filter_destination_storage or None,
            incoming_owner=self.filter_incoming_owner or None,
            destination_owner=self.filter_destination_owner or None,
        )
        prices = MovementDAO.get_catalog_admission_prices(catalog_ids)

        def _fmt_stat(units: int, amount: float, divisible: bool) -> str:
            if divisible:
                return format_amount(amount)
            return str(units)

        rows: List[Tuple[int, str, str, str, str, str, str, str, str, str, str]] = []
        for cat_id, title, unit, category_title, movement_count, divisible, uniq in catalog_rows:
            unit_display = unit if divisible else "од."
            cat_stat = stats.get(cat_id, {})

            # Поставлено
            adm_u, adm_a = cat_stat.get(MovementsType.ADMISSION, (0, 0.0))
            adm_str = _fmt_stat(adm_u, adm_a, divisible)

            # Видано (ISSUE + CLIENT_ISSUE)
            iss_u1, iss_a1 = cat_stat.get(MovementsType.ISSUE, (0, 0.0))
            iss_u2, iss_a2 = cat_stat.get(MovementsType.CLIENT_ISSUE, (0, 0.0))
            iss_str = _fmt_stat(iss_u1 + iss_u2, iss_a1 + iss_a2, divisible)

            # Продано (SALE)
            sale_u, sale_a = cat_stat.get(MovementsType.SALE, (0, 0.0))
            sale_str = _fmt_stat(sale_u, sale_a, divisible)

            # Повернуто (RETURN + SALE_RETURN)
            ret_u1, ret_a1 = cat_stat.get(MovementsType.RETURN, (0, 0.0))
            ret_u2, ret_a2 = cat_stat.get(MovementsType.SALE_RETURN, (0, 0.0))
            ret_str = _fmt_stat(ret_u1 + ret_u2, ret_a1 + ret_a2, divisible)

            # Списано (WRITE_OFF)
            wo_u, wo_a = cat_stat.get(MovementsType.WRITE_OFF, (0, 0.0))
            wo_str = _fmt_stat(wo_u, wo_a, divisible)

            # Остання вартість
            price_list = prices.get(cat_id, [])
            last_price_str = f"{price_list[0][0]:.2f}" if price_list else "—"

            rows.append(
                (
                    cat_id,
                    title,
                    category_title,
                    unit_display,
                    adm_str,
                    iss_str,
                    sale_str,
                    ret_str,
                    wo_str,
                    last_price_str,
                    str(movement_count),
                )
            )
        self.rows = rows

    # --- computed vars ---

    @rx.var
    def has_rows(self) -> bool:
        return len(self.rows) > 0

    @rx.var
    def get_current_page(self) -> str:
        return str(self._current_page)

    @rx.var
    def get_all_pages(self) -> str:
        return str(self._all_pages)

    @rx.var
    def dialog_current_page(self) -> str:
        return str(self._dialog_current_page)

    @rx.var
    def dialog_all_pages(self) -> str:
        return str(self._dialog_all_pages)

    @rx.var
    def filter_category_value(self) -> str:
        return self.filter_category if self.filter_category != "" else ALL

    @rx.var
    def filter_incoming_storage_value(self) -> str:
        return self.filter_incoming_storage if self.filter_incoming_storage != "" else ALL

    @rx.var
    def filter_destination_storage_value(self) -> str:
        return self.filter_destination_storage if self.filter_destination_storage != "" else ALL

    @rx.var
    def filter_incoming_owner_value(self) -> str:
        return self.filter_incoming_owner if self.filter_incoming_owner != "" else ALL

    @rx.var
    def filter_destination_owner_value(self) -> str:
        return self.filter_destination_owner if self.filter_destination_owner != "" else ALL

    @rx.var
    def filtered_incoming_storages(self) -> List[Tuple[str, str]]:
        term = self.search_incoming_storage.strip().lower()
        if term == "":
            return self._storages_cache
        return [s for s in self._storages_cache if term in s[1].lower()]

    @rx.var
    def filtered_destination_storages(self) -> List[Tuple[str, str]]:
        term = self.search_destination_storage.strip().lower()
        if term == "":
            return self._storages_cache
        return [s for s in self._storages_cache if term in s[1].lower()]

    # --- events ---

    @rx.event
    def on_load(self):
        guard = self.access_guard(Action.REPORTS_CATALOG_MOVEMENTS)
        if guard is not None:
            yield guard
            return

        self.in_progress = True
        self._load_filter_options()

        if not self._initialized:
            self._initialized = True
            self._current_page = 1
            self.search_text = ""
            self.filter_category = ""
            self.filter_incoming_storage = ""
            self.filter_destination_storage = ""
            self.filter_incoming_owner = ""
            self.filter_destination_owner = ""
            self.date_from = ""
            self.date_to = ""
            self.exclude_canceled = False
            self.search_incoming_storage = ""
            self.search_destination_storage = ""
            self.is_movements_open = False
            self.movement_rows = []
            self.selected_title = ""
            self.selected_catalog_id = -1
            self.dialog_unit = ""
            self.dialog_delivered = ""
            self.dialog_issued = ""
            self.dialog_sold = ""
            self.dialog_returned = ""
            self.dialog_written_off = ""
            self.dialog_price_history = ""

        self._reload()

        # Повернення з перегляду руху — відновлюємо відкритий діалог.
        if self.is_movements_open and self.selected_catalog_id != -1:
            self._load_movements(self.selected_catalog_id, self.selected_title)

        self.in_progress = False

    @rx.event
    def on_change_search_text(self, value: str):
        self.search_text = value
        self._current_page = 1
        self._reload()

    @rx.event
    def on_change_category(self, value: str):
        self.filter_category = "" if value == ALL else value
        self._current_page = 1
        self._reload()

    @rx.event
    def on_change_incoming_storage(self, value: str):
        self.filter_incoming_storage = "" if value == ALL else value
        self._current_page = 1
        self._reload()

    @rx.event
    def on_change_destination_storage(self, value: str):
        self.filter_destination_storage = "" if value == ALL else value
        self._current_page = 1
        self._reload()

    @rx.event
    def on_change_incoming_owner(self, value: str):
        self.filter_incoming_owner = "" if value == ALL else value
        self._current_page = 1
        self._reload()

    @rx.event
    def on_change_destination_owner(self, value: str):
        self.filter_destination_owner = "" if value == ALL else value
        self._current_page = 1
        self._reload()

    @rx.event
    def on_change_date_from(self, value: str):
        self.date_from = value
        self._current_page = 1
        self._reload()

    @rx.event
    def on_change_date_to(self, value: str):
        self.date_to = value
        self._current_page = 1
        self._reload()

    @rx.event
    def on_change_exclude_canceled(self, value: bool):
        self.exclude_canceled = value
        self._current_page = 1
        self._reload()

    @rx.event
    def on_change_search_incoming_storage(self, value: str):
        self.search_incoming_storage = value

    @rx.event
    def on_change_search_destination_storage(self, value: str):
        self.search_destination_storage = value

    @rx.event
    def reset_filters(self):
        self.search_text = ""
        self.filter_category = ""
        self.filter_incoming_storage = ""
        self.filter_destination_storage = ""
        self.filter_incoming_owner = ""
        self.filter_destination_owner = ""
        self.date_from = ""
        self.date_to = ""
        self.exclude_canceled = False
        self.search_incoming_storage = ""
        self.search_destination_storage = ""
        self._current_page = 1
        self._reload()

    @rx.event
    def current_page_increment(self):
        if self._current_page + 1 <= self._all_pages:
            self._current_page += 1
            self._reload()
            return rx.call_script(SCROLL_TOP_SCRIPT)

    @rx.event
    def current_page_decrement(self):
        if self._current_page > 1:
            self._current_page -= 1
            self._reload()
            return rx.call_script(SCROLL_TOP_SCRIPT)

    @rx.event
    def on_change_current_page(self, value: str):
        if value != "" and 0 < int(value) <= self._all_pages:
            self._current_page = int(value)
            self._reload()
            return rx.call_script(SCROLL_TOP_SCRIPT)

    # --- діалог рухів позиції ---

    def _load_movements(self, catalog_id: int, title: str) -> None:
        self.selected_catalog_id = catalog_id
        self.selected_title = title

        catalog = ProductCatalogService().get_by_id(catalog_id, with_del=True)
        unit = catalog.unit if catalog else ""
        divisible = catalog.divisible if catalog else False
        uniq = catalog.uniq if catalog else False
        capacity = catalog.capacity if catalog else 0.0
        no_fixed = catalog.no_fixed_capacity if catalog else False

        self.dialog_unit = unit or "од."

        # Завантажуємо статистику для діалогу
        stats_dict = MovementDAO.get_catalog_movement_stats(
            [catalog_id],
            date_from=self.date_from,
            date_to=self.date_to,
            incoming_storage=self.filter_incoming_storage or None,
            destination_storage=self.filter_destination_storage or None,
            incoming_owner=self.filter_incoming_owner or None,
            destination_owner=self.filter_destination_owner or None,
        )
        cat_stats = stats_dict.get(catalog_id, {})

        def _fmt_dlg_stat(units: int, amount: float) -> str:
            if uniq:
                return f"{units} од."
            if divisible:
                return f"{units} од. ({format_amount(amount)} {unit})"
            if unit and unit != "од.":
                return f"{units} од. ({units} {unit})"
            return f"{units} од."

        # Поставлено
        adm_u, adm_a = cat_stats.get(MovementsType.ADMISSION, (0, 0.0))
        self.dialog_delivered = _fmt_dlg_stat(adm_u, adm_a)

        # Видано (ISSUE + CLIENT_ISSUE)
        iss_u1, iss_a1 = cat_stats.get(MovementsType.ISSUE, (0, 0.0))
        iss_u2, iss_a2 = cat_stats.get(MovementsType.CLIENT_ISSUE, (0, 0.0))
        self.dialog_issued = _fmt_dlg_stat(iss_u1 + iss_u2, iss_a1 + iss_a2)

        # Продано (SALE)
        sale_u, sale_a = cat_stats.get(MovementsType.SALE, (0, 0.0))
        self.dialog_sold = _fmt_dlg_stat(sale_u, sale_a)

        # Повернуто (RETURN + SALE_RETURN)
        ret_u1, ret_a1 = cat_stats.get(MovementsType.RETURN, (0, 0.0))
        ret_u2, ret_a2 = cat_stats.get(MovementsType.SALE_RETURN, (0, 0.0))
        self.dialog_returned = _fmt_dlg_stat(ret_u1 + ret_u2, ret_a1 + ret_a2)

        # Списано (WRITE_OFF)
        wo_u, wo_a = cat_stats.get(MovementsType.WRITE_OFF, (0, 0.0))
        self.dialog_written_off = _fmt_dlg_stat(wo_u, wo_a)

        # Динаміка цін постачання (останні три різні ціни)
        prices_dict = MovementDAO.get_catalog_admission_prices([catalog_id])
        prices_list = prices_dict.get(catalog_id, [])
        distinct_prices: List[float] = []
        for p, _ in prices_list:
            p_round = round(p, 2)
            if p_round not in distinct_prices:
                distinct_prices.append(p_round)
                if len(distinct_prices) == 3:
                    break
        if distinct_prices:
            self.dialog_price_history = " → ".join(f"{p:.2f} грн" for p in reversed(distinct_prices))
        else:
            self.dialog_price_history = "—"

        count_items = MovementDAO.get_movements_by_catalog_count(
            catalog_id,
            date_from=self.date_from,
            date_to=self.date_to,
            incoming_storage=self.filter_incoming_storage or None,
            destination_storage=self.filter_destination_storage or None,
            incoming_owner=self.filter_incoming_owner or None,
            destination_owner=self.filter_destination_owner or None,
            exclude_canceled=self.exclude_canceled,
        )
        self._dialog_all_pages, lines = MovementDAO.get_movements_by_catalog(
            catalog_id,
            page=self._dialog_current_page,
            limit=self._dialog_limit,
            count_items=count_items,
            date_from=self.date_from,
            date_to=self.date_to,
            incoming_storage=self.filter_incoming_storage or None,
            destination_storage=self.filter_destination_storage or None,
            incoming_owner=self.filter_incoming_owner or None,
            destination_owner=self.filter_destination_owner or None,
            exclude_canceled=self.exclude_canceled,
        )

        rows: List[Tuple[str, str, str, str, str, str, str, str, str]] = []
        for line in lines:
            m = line.movement
            type_title = movements_type_list.get(m.type, "—")
            status_title = (
                movements_status_list[m.status]
                if 0 <= m.status < len(movements_status_list)
                else "—"
            )
            qty_label = (
                format_transferred_qty(line.amount, line.units, divisible, capacity, no_fixed)
                if (divisible and not no_fixed and capacity > 0)
                else (format_amount(line.amount) if divisible else str(line.units))
            )
            unit_price_label = (
                f"{line.price:.2f}"
                if m.type == MovementsType.ADMISSION
                else "—"
            )
            rows.append(
                (
                    str(m.id),
                    type_title,
                    m.date,
                    _sender_label(m, line.supplier_title),
                    _receiver_label(m),
                    qty_label,
                    unit_price_label,
                    status_title,
                    routes.movement_view_url(m.type, m.id),
                )
            )
        self.movement_rows = rows

    @rx.event
    def open_movements(self, catalog_id: int, title: str):
        self._dialog_current_page = 1
        self._load_movements(catalog_id, title)
        self.is_movements_open = True

    @rx.event
    def set_movements_open(self, value: bool):
        self.is_movements_open = value
        if not value:
            self.movement_rows = []
            self.selected_title = ""
            self.selected_catalog_id = -1
            self.dialog_unit = ""
            self.dialog_delivered = ""
            self.dialog_issued = ""
            self.dialog_sold = ""
            self.dialog_returned = ""
            self.dialog_written_off = ""
            self.dialog_price_history = ""
            self._dialog_current_page = 1
            self._dialog_all_pages = 1

    @rx.event
    def dialog_page_increment(self):
        if self._dialog_current_page + 1 <= self._dialog_all_pages:
            self._dialog_current_page += 1
            self._load_movements(self.selected_catalog_id, self.selected_title)

    @rx.event
    def dialog_page_decrement(self):
        if self._dialog_current_page > 1:
            self._dialog_current_page -= 1
            self._load_movements(self.selected_catalog_id, self.selected_title)

    @rx.event
    def on_change_dialog_page(self, value: str):
        if value != "" and 0 < int(value) <= self._dialog_all_pages:
            self._dialog_current_page = int(value)
            self._load_movements(self.selected_catalog_id, self.selected_title)

    @rx.event
    def export_csv(self):
        if self.selected_catalog_id == -1:
            return
        catalog = ProductCatalogService().get_by_id(self.selected_catalog_id, with_del=True)
        divisible = catalog.divisible if catalog else False

        _, lines = MovementDAO.get_movements_by_catalog(
            self.selected_catalog_id,
            page=1,
            limit=None,
            date_from=self.date_from,
            date_to=self.date_to,
            incoming_storage=self.filter_incoming_storage or None,
            destination_storage=self.filter_destination_storage or None,
            incoming_owner=self.filter_incoming_owner or None,
            destination_owner=self.filter_destination_owner or None,
            exclude_canceled=self.exclude_canceled,
        )

        output = io.StringIO()
        # UTF-8 BOM для коректного відкриття кирилиці в MS Excel
        output.write("\ufeff")
        writer = csv.writer(output, delimiter=";")
        writer.writerow([
            "Дата",
            "Тип руху",
            "Місце відправлення",
            "Відправник",
            "Місце отримання",
            "Отримувач",
            "Кількість",
            "Вартість одиниці",
            "Загальна вартість у постачанні",
        ])

        for line in lines:
            m = line.movement
            m_type = movements_type_list.get(m.type, "—")

            src_storage = m.incoming_storage.title if m.incoming_storage else "—"
            if m.type == MovementsType.ADMISSION:
                sender = line.supplier_title or "—"
            elif m.type == MovementsType.SALE_RETURN:
                sender = line.sender or "Клієнт"
            else:
                sender = m.incoming_owner.title if m.incoming_owner else "—"

            if m.destination_storage:
                dst_storage = m.destination_storage.title
            elif m.type == MovementsType.WRITE_OFF:
                dst_storage = "Списано"
            else:
                dst_storage = "—"

            if line.recipient:
                receiver = line.recipient
            elif m.type == MovementsType.SALE:
                receiver = "Клієнт"
            elif m.type == MovementsType.WRITE_OFF:
                receiver = "Списано"
            else:
                receiver = m.destination_owner.title if m.destination_owner else "—"

            qty_str = (
                format_amount(line.amount)
                if divisible
                else str(line.units)
            )

            is_admission = (m.type == MovementsType.ADMISSION)
            unit_price_str = f"{line.price:.2f}" if is_admission else "—"
            line_cost_str = (
                f"{line.line_cost:.2f}"
                if (is_admission and line.line_cost is not None)
                else "—"
            )

            writer.writerow([
                m.date,
                m_type,
                src_storage,
                sender,
                dst_storage,
                receiver,
                qty_str,
                unit_price_str,
                line_cost_str,
            ])

        csv_text = output.getvalue()
        file_title = self.selected_title.replace(" ", "_").replace("/", "_")
        filename = f"movements_{file_title}_{now_local().strftime('%Y%m%d_%H%M%S')}.csv"
        return rx.download(
            data=csv_text,
            filename=filename,
            mime_type="text/csv",
        )

