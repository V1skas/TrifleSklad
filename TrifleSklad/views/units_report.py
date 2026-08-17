import reflex as rx

from TrifleSklad import routes
from TrifleSklad.models import Product
from TrifleSklad.movement.list_components import pagination
from TrifleSklad.movement.list_mixin import ALL
from TrifleSklad.states.units_report import ListUnitsReportState, ViewUnitsReportState
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.templates import controls
from TrifleSklad.views.templates.layouts import field_row, header_subpage, page_wrapper, titled_section


def _list_table_row(item: Product) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(item.id, width="1%", white_space="nowrap"),
        rx.table.cell(item.product_catalog.title),
        rx.table.cell(
            rx.cond(item.product_catalog.uniq, rx.text(rx.cond(item.serial_number, item.serial_number, "—")), rx.text("—", color="gray")),
            width="1%", white_space="nowrap",
        ),
        rx.table.cell(
            rx.cond(item.product_catalog.divisible, rx.text(item.count), rx.text("—", color="gray")),
            width="1%", white_space="nowrap",
        ),
        rx.table.cell(item.storage.title),
        rx.table.cell(item.owner.title),
        on_click=rx.redirect(f"{routes.REPORTS_UNITS_VIEW_ID}{item.id}"),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def _list_table() -> rx.Component:
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
        rx.table.body(rx.foreach(ListUnitsReportState.items, _list_table_row)),
        variant="surface",
        width="100%",
    )


def list_page_content() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            controls.search_field(
                placeholder="Пошук за назвою / серійним номером / id",
                value=ListUnitsReportState.get_search_str,
                on_change=ListUnitsReportState.on_change_search_str,
                flex="1",
                min_width="0",
            ),
            rx.select.root(
                # width/flex_shrink — на trigger, не на root (rx.select.root
                # не рендерить власний стилізовний DOM-елемент).
                rx.select.trigger(placeholder="Усі позиції", width="18em", flex_shrink="0"),
                rx.select.content(
                    rx.select.item("Усі позиції", value=ALL),
                    rx.foreach(ListUnitsReportState.list_catalog, lambda c: rx.select.item(c[0], value=c[1])),
                ),
                value=ListUnitsReportState.filter_catalog_id,
                on_change=ListUnitsReportState.on_change_filter_catalog,
            ),
            width="100%",
            spacing="3",
            align="center",
        ),
        rx.cond(
            ListUnitsReportState.has_items,
            _list_table(),
            controls.empty_placeholder("Одиниць ТМЦ не знайдено"),
        ),
        pagination(ListUnitsReportState),
        spacing="4",
        width="100%",
    )


@require_login
def list_page() -> rx.Component:
    return page_wrapper(
        header_subpage("Звіти/Одиниці ТМЦ", width="100%"),
        rx.skeleton(list_page_content(), loading=ListUnitsReportState.in_progress, height="100%"),
        on_mount=ListUnitsReportState.on_load,
    )


def _history_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("№", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                rx.table.column_header_cell("Тип", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Дата", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Маршрут", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Власник", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Статус", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(
                ViewUnitsReportState.history_rows,
                lambda row: rx.table.row(
                    rx.table.cell(row[0], width="1%", white_space="nowrap"),
                    rx.table.cell(row[1]),
                    rx.table.cell(row[2]),
                    rx.table.cell(row[3]),
                    rx.table.cell(row[4]),
                    rx.table.cell(row[5]),
                    on_click=rx.redirect(row[6]),
                    cursor="pointer",
                    _hover={"background_color": rx.color("accent", 3)},
                ),
            ),
        ),
        variant="surface",
        width="100%",
    )


def _remain_row(state) -> rx.Component:
    """Рядок «Залишок» для подільного ТМЦ — та сама розмітка мітки, що й у
    `field_row`, але значення не текст, а смуга заповнення (`field_row`
    обгортає value в `rx.text`, тому для нетекстового вмісту потрібен
    окремий рядок)."""
    return rx.hstack(
        rx.text(
            "Залишок:",
            weight="medium",
            color=rx.color("accent", 11),
            min_width="12em",
            flex_shrink="0",
        ),
        rx.vstack(
            rx.text(state.unit_remain_label),
            rx.progress(
                value=state.unit_fill_percent,
                max=100,
                color_scheme="green",
                height="0.5em",
                width="100%",
            ),
            spacing="1",
            width="100%",
            max_width="22em",
        ),
        width="100%",
        wrap="wrap",
        spacing="2",
        align="center",
    )


def view_page_content() -> rx.Component:
    return rx.vstack(
        titled_section(
            "Інформація",
            field_row("ID одиниці", ViewUnitsReportState.unit.id),
            field_row("Позиція каталогу", ViewUnitsReportState.unit_title),
            field_row("Одиниця виміру", ViewUnitsReportState.unit_unit),
            rx.cond(ViewUnitsReportState.unit_uniq, field_row("Серійний номер", ViewUnitsReportState.unit_serial)),
            rx.cond(ViewUnitsReportState.unit_divisible, _remain_row(ViewUnitsReportState)),
            field_row("Місце зберігання", ViewUnitsReportState.unit_storage),
            field_row("Власник", ViewUnitsReportState.unit_owner),
        ),
        titled_section(
            "Історія руху",
            rx.cond(
                ViewUnitsReportState.has_history,
                _history_table(),
                controls.empty_placeholder("Рухів за цією одиницею немає"),
            ),
        ),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def view_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Звіти/Одиниці ТМЦ/Перегляд",
            left=controls.button_back(routes.REPORTS_UNITS, label="Повернутись"),
            width="100%",
        ),
        rx.skeleton(view_page_content(), loading=ViewUnitsReportState.in_process, height="100%"),
    )
