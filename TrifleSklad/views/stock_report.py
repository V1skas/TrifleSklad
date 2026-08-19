import reflex as rx

from TrifleSklad import routes
from TrifleSklad.states.stock_report import ALL, StockReportState
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.templates.layouts import header_subpage, page_wrapper
from TrifleSklad.views.templates import controls


def _filter_select(label: str, value, options, on_change, search_value=None, on_search=None) -> rx.Component:
    content = []
    if on_search is not None:
        content.append(
            controls.input_field(
                rx.input.slot(rx.icon("search")),
                placeholder="Пошук",
                value=search_value,
                on_change=on_search,
                width="100%",
                margin_bottom="0.5em",
            )
        )
    content.append(rx.select.item("Усі", value=ALL))
    content.append(rx.foreach(options, lambda opt: rx.select.item(opt[1], value=opt[0])))
    return controls.filter_group(
        label,
        rx.select.root(
            rx.select.trigger(placeholder="Усі", width="100%"),
            rx.select.content(*content, width="100%"),
            value=value,
            on_change=on_change,
            width="100%",
        ),
    )


def _filter_card() -> rx.Component:
    return rx.card(
        rx.vstack(
            controls.filter_grid(
                controls.filter_group(
                    "Пошук",
                    controls.search_field(
                        rx.input.slot(rx.icon("search")),
                        placeholder="Назва ТМЦ або серійний номер",
                        value=StockReportState.search_text,
                        on_change=StockReportState.on_change_search_text,
                        width="100%",
                    ),
                    wide=True,
                ),
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
            ),
            controls.filter_group(
                "Виключити місця",
                rx.hstack(
                    rx.checkbox("Склади", checked=StockReportState.exclude_warehouse, on_change=StockReportState.on_change_exclude_warehouse),
                    rx.checkbox("Площадки", checked=StockReportState.exclude_site, on_change=StockReportState.on_change_exclude_site),
                    rx.checkbox("Відділи", checked=StockReportState.exclude_department, on_change=StockReportState.on_change_exclude_department),
                    rx.checkbox("Клієнти", checked=StockReportState.exclude_client, on_change=StockReportState.on_change_exclude_client),
                    spacing="5",
                    wrap="wrap",
                    align="center",
                ),
                height="auto",
            ),
            controls.filter_actions(
                rx.button("Скинути фільтри", variant="soft", type="button", on_click=StockReportState.reset_filters),
            ),
            spacing="3",
            width="100%",
        ),
        width="100%",
    )


def _units_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(f"Одиниці: {StockReportState.selected_title}"),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("ID", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                        rx.table.column_header_cell("Серійний номер", color=rx.color("accent", 2)),
                        rx.table.column_header_cell("Місце зберігання", color=rx.color("accent", 2)),
                        rx.table.column_header_cell("Власник", color=rx.color("accent", 2)),
                        rx.table.column_header_cell("Залишок", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                        rx.table.column_header_cell("Облік", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
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
                            rx.table.cell(
                                rx.cond(
                                    unit[5],
                                    rx.badge("Поза обліком", color_scheme="orange", size="1", variant="soft"),
                                    rx.text("—", color="gray"),
                                ),
                                width="1%", white_space="nowrap",
                            ),
                            on_click=rx.redirect(f"{routes.REPORTS_UNITS_VIEW_ID}{unit[0]}"),
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
                rx.dialog.close(rx.button("Закрити", on_click=StockReportState.set_units_open(False))),
                justify="end",
                margin_top="1em",
            ),
            max_width="50em",
        ),
        open=StockReportState.is_units_open,
        on_open_change=StockReportState.set_units_open,
    )


def _table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Назва позиції", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Одиниця виміру", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Загальна кількість", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Одиниць", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
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


def page_content() -> rx.Component:
    return rx.vstack(
        _filter_card(),
        rx.cond(
            StockReportState.has_rows,
            _table(),
            rx.center(rx.text("ТМЦ не знайдено", color="gray"), width="100%", padding="2em"),
        ),
        _units_dialog(),
        spacing="4",
        width="100%",
    )


@require_login
def page() -> rx.Component:
    return page_wrapper(
        header_subpage("Звіти/Наявність ТМЦ", width="100%"),
        rx.skeleton(page_content(), loading=StockReportState.in_progress, height="100%"),
        on_mount=StockReportState.on_load,
    )
