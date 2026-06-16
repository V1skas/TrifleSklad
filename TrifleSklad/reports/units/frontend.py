import reflex as rx

from typing import Tuple

from components.elements import subpage_header

from TrifleSklad import routes
from TrifleSklad.models import Product
from TrifleSklad.movement.list_components import pagination
from TrifleSklad.movement.list_mixin import ALL
from TrifleSklad.reports.units.backend import UnitsReportState


def list_table_row(item: Product) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(
            item.id,
            width="1%",
            white_space="nowrap",
        ),
        rx.table.cell(item.product_catalog.title),
        rx.table.cell(
            rx.cond(item.product_catalog.uniq,
                    rx.text(rx.cond(item.serial_number, item.serial_number, "—")),
                    rx.text("—", color="gray")),
            width="1%", white_space="nowrap",
        ),
        rx.table.cell(
            rx.cond(item.product_catalog.divisible,
                    rx.text(item.count),
                    rx.text("—", color="gray")),
            width="1%", white_space="nowrap",
        ),
        rx.table.cell(item.storage.title),
        rx.table.cell(item.owner.title),
        on_click=rx.redirect(f"{routes.REPORTS_UNITS_VIEW_ID}{item.id}"),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def list_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("ID", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                rx.table.column_header_cell("Назва", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Серійний номер", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                rx.table.column_header_cell("Залишок", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                rx.table.column_header_cell("Місце зберігання", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Власник", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(UnitsReportState.items, list_table_row),
        ),
        variant="surface",
        width="100%",
    )


def units_list() -> rx.Component:
    return rx.vstack(
        subpage_header("Звіти/Одиниці ТМЦ"),
        rx.hstack(
            rx.input(
                placeholder="Пошук за назвою / серійним номером / id",
                value=UnitsReportState.get_search_str,
                on_change=UnitsReportState.on_change_search_str,
                flex="1",
                min_width="0",
            ),
            rx.button("Пошук", on_click=UnitsReportState.on_click_search, flex_shrink="0"),
            rx.select.root(
                rx.select.trigger(placeholder="Усі позиції"),
                rx.select.content(
                    rx.select.item("Усі позиції", value=ALL),
                    rx.foreach(
                        UnitsReportState.list_catalog,
                        lambda c: rx.select.item(c[0], value=c[1]),
                    ),
                ),
                value=UnitsReportState.filter_catalog_id,
                on_change=UnitsReportState.on_change_filter_catalog,
                width="18em",
                flex_shrink="0",
            ),
            width="100%",
            spacing="3",
            align="center",
        ),
        rx.cond(
            UnitsReportState.has_items,
            list_table(),
            rx.center(rx.text("Одиниць ТМЦ не знайдено", color="gray"), width="100%", padding="2em"),
        ),
        pagination(UnitsReportState),
        spacing="4",
        width="100%",
        height="100%",
    )


def history_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("№", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                rx.table.column_header_cell("Тип", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Дата", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Маршрут", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Статус", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(
                UnitsReportState.history_rows,
                lambda row: rx.table.row(
                    rx.table.cell(row[0], width="1%", white_space="nowrap"),
                    rx.table.cell(row[1]),
                    rx.table.cell(row[2]),
                    rx.table.cell(row[4]),
                    rx.table.cell(row[3]),
                    on_click=rx.redirect(row[5]),
                    cursor="pointer",
                    _hover={"background_color": rx.color("accent", 3)},
                ),
            ),
        ),
        variant="surface",
        width="100%",
    )


def _info_row(label: str, value) -> rx.Component:
    return rx.hstack(
        rx.text(label, weight="bold", width="14em"),
        rx.text(value),
        width="100%",
    )


def unit_detail() -> rx.Component:
    return rx.vstack(
        subpage_header(
            "Звіти/Одиниці ТМЦ/Перегляд",
            left=rx.button(
                "Повернутись",
                variant="ghost",
                size="3",
                on_click=rx.redirect(routes.REPORTS_UNITS),
            ),
        ),
        rx.card(
            rx.vstack(
                _info_row("ID одиниці:", UnitsReportState.unit.id),
                _info_row("Позиція каталогу:", UnitsReportState.unit_title),
                _info_row("Одиниця виміру:", UnitsReportState.unit_unit),
                rx.cond(
                    UnitsReportState.unit_uniq,
                    _info_row("Серійний номер:", UnitsReportState.unit_serial),
                ),
                rx.cond(
                    UnitsReportState.unit_divisible,
                    _info_row("Залишок:", UnitsReportState.unit_count),
                ),
                _info_row("Місце зберігання:", UnitsReportState.unit_storage),
                _info_row("Власник:", UnitsReportState.unit_owner),
                spacing="2",
                width="100%",
            ),
            width="100%",
        ),
        rx.heading("Історія руху", size="4", width="100%"),
        rx.cond(
            UnitsReportState.has_history,
            history_table(),
            rx.center(rx.text("Рухів за цією одиницею немає", color="gray"), width="100%", padding="2em"),
        ),
        spacing="4",
        width="100%",
        height="100%",
    )


def index() -> rx.Component:
    return rx.match(
        UnitsReportState.page_mode,
        ("view", unit_detail()),
        units_list(),
    )
