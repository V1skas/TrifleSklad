import reflex as rx

from components.elements import subpage_header

import TrifleSklad.routes as routes
from TrifleSklad.reports.stock.backend import StockReportState, ALL


def _filter_select(label: str, value, options, on_change, search_value=None, on_search=None) -> rx.Component:
    # Якщо передано search_value/on_search — у випадаючому списку з'являється
    # поле живого пошуку (фільтрує options під час набору).
    content = []
    if on_search is not None:
        content.append(
            rx.input(
                rx.input.slot(rx.icon("search")),
                placeholder="Пошук",
                value=search_value,
                on_change=on_search,
                width="100%",
                margin_bottom="0.5em",
            )
        )
    content.append(rx.select.item("Усі", value=ALL))
    content.append(
        rx.foreach(options, lambda opt: rx.select.item(opt[1], value=opt[0]))
    )
    return rx.vstack(
        rx.text(label, size="2"),
        rx.select.root(
            rx.select.trigger(placeholder="Усі", width="100%"),
            rx.select.content(*content, width="100%"),
            value=value,
            on_change=on_change,
            width="100%",
        ),
        spacing="1",
        width="100%",
    )


def filter_card() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.hstack(
                _filter_select(
                    "Категорія",
                    StockReportState.filter_category_value,
                    StockReportState.list_categories,
                    StockReportState.on_change_category,
                ),
                _filter_select(
                    "Позиція каталогу",
                    StockReportState.filter_catalog_value,
                    StockReportState.filtered_list_catalog,
                    StockReportState.on_change_catalog,
                    search_value=StockReportState.search_catalog,
                    on_search=StockReportState.on_change_search_catalog,
                ),
                _filter_select(
                    "Місце зберігання",
                    StockReportState.filter_storage_value,
                    StockReportState.filtered_list_storages,
                    StockReportState.on_change_storage,
                    search_value=StockReportState.search_storage,
                    on_search=StockReportState.on_change_search_storage,
                ),
                _filter_select(
                    "Власник",
                    StockReportState.filter_owner_value,
                    StockReportState.list_owners,
                    StockReportState.on_change_owner,
                ),
                spacing="3",
                width="100%",
                align="end",
            ),
            rx.hstack(
                rx.text("Виключити:", size="2", weight="bold"),
                rx.checkbox(
                    "Склади",
                    checked=StockReportState.exclude_warehouse,
                    on_change=StockReportState.on_change_exclude_warehouse,
                ),
                rx.checkbox(
                    "Площадки",
                    checked=StockReportState.exclude_site,
                    on_change=StockReportState.on_change_exclude_site,
                ),
                rx.checkbox(
                    "Відділи",
                    checked=StockReportState.exclude_department,
                    on_change=StockReportState.on_change_exclude_department,
                ),
                rx.spacer(),
                rx.button(
                    "Скинути фільтри",
                    variant="soft",
                    size="2",
                    type="button",
                    on_click=StockReportState.reset_filters,
                ),
                spacing="4",
                width="100%",
                align="center",
            ),
            spacing="3",
            width="100%",
        ),
        width="100%",
    )


def units_dialog() -> rx.Component:
    # Деталізація позиції: перелік окремих одиниць ТМЦ на місцях зберігання.
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(f"Одиниці: {StockReportState.selected_title}"),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell(
                            "ID", color=rx.color("accent", 2),
                            width="1%", white_space="nowrap",
                        ),
                        rx.table.column_header_cell("Серійний номер", color=rx.color("accent", 2)),
                        rx.table.column_header_cell("Місце зберігання", color=rx.color("accent", 2)),
                        rx.table.column_header_cell("Власник", color=rx.color("accent", 2)),
                        rx.table.column_header_cell(
                            "Залишок", color=rx.color("accent", 2),
                            width="1%", white_space="nowrap",
                        ),
                    ),
                    background_color=rx.color("accent", 9),
                ),
                rx.table.body(
                    rx.foreach(
                        StockReportState.unit_rows,
                        lambda unit: rx.table.row(
                            rx.table.cell(unit[0], width="1%", white_space="nowrap"),
                            rx.table.cell(unit[1]),
                            rx.table.cell(unit[2]),
                            rx.table.cell(unit[3]),
                            rx.table.cell(unit[4], width="1%", white_space="nowrap"),
                            on_click=rx.redirect(
                                f"{routes.REPORTS_UNITS_VIEW_ID}{unit[0]}"
                            ),
                            cursor="pointer",
                            _hover={"background_color": rx.color("accent", 3)},
                        ),
                    ),
                ),
                variant="surface",
                width="100%",
                margin_top="1em",
            ),
            rx.flex(
                rx.dialog.close(
                    rx.button(
                        "Закрити",
                        on_click=StockReportState.set_units_open(False),
                    ),
                ),
                justify="end",
                margin_top="1em",
            ),
            max_width="50em",
        ),
        open=StockReportState.is_units_open,
        on_open_change=StockReportState.set_units_open,
    )


def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Назва позиції", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Одиниця виміру", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Загальна кількість", color=rx.color("accent", 2)),
                rx.table.column_header_cell(
                    "Одиниць", color=rx.color("accent", 2),
                    width="1%", white_space="nowrap",
                ),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(
                StockReportState.rows,
                lambda row: rx.table.row(
                    rx.table.cell(row[1]),
                    rx.table.cell(row[2]),
                    rx.table.cell(row[3]),
                    rx.table.cell(row[4], width="1%", white_space="nowrap"),
                    on_click=StockReportState.open_units(row[0], row[1]),
                    cursor="pointer",
                    _hover={"background_color": rx.color("accent", 3)},
                ),
            ),
        ),
        variant="surface",
        width="100%",
    )


def search_box() -> rx.Component:
    return rx.debounce_input(
        rx.input(
            rx.input.slot(rx.icon("search")),
            placeholder="Пошук за назвою ТМЦ або серійним номером",
            value=StockReportState.search_text,
            on_change=StockReportState.on_change_search_text,
            width="100%",
        ),
        debounce_timeout=400,
    )


def index() -> rx.Component:
    return rx.vstack(
        subpage_header("Звіти/Наявність ТМЦ"),
        search_box(),
        filter_card(),
        rx.cond(
            StockReportState.has_rows,
            table(),
            rx.center(
                rx.text("ТМЦ не знайдено", color="gray"),
                width="100%",
                padding="2em",
            ),
        ),
        units_dialog(),
        spacing="4",
        width="100%",
        height="100%",
    )
