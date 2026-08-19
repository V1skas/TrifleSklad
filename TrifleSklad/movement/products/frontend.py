import reflex as rx

from typing import Tuple

from TrifleSklad import routes
from TrifleSklad.models import Product
from TrifleSklad.movement.products.backend import ProductsMovementListState
from TrifleSklad.movement.products_selector.frontend import selector as products_selector
from TrifleSklad.views.templates import controls
from TrifleSklad.views.templates.layouts import (
    NESTED_DETAIL_TABLE,
    NESTED_DETAIL_TD,
    NESTED_DETAIL_TH,
    NESTED_DETAIL_THEAD,
)

# Вузька колонка вкладеної таблиці (по вмісту, без переносів).
_TD_TIGHT = {**NESTED_DETAIL_TD, "width": "1%", "white_space": "nowrap"}
_TH_TIGHT = {**NESTED_DETAIL_TH, "width": "1%", "white_space": "nowrap"}


def dialog():
    return rx.dialog.root(
        rx.dialog.content(
            products_selector(
                rx.hstack(
                    rx.spacer(),
                    rx.button("Обрати", type="button", on_click=ProductsMovementListState.on_save_selected)
                ),
                width="100%",
                height="100%"
            ),

            width="min(56em, 95vw)",
            height="min(40em, 90vh)",
            max_width="56em",
            # Прокрутка лише всередині списку ТМЦ, а не всього діалогу.
            overflow="hidden",
            display="flex",
            flex_direction="column",
        ),

        open=ProductsMovementListState.dialog_open,
        on_open_change=ProductsMovementListState.close_dialog,
    )

def serial_cell_text(item: Tuple[int, Product]):
    # Серійний номер показуємо лише для ТМЦ, у якого він має бути (uniq).
    return rx.el.td(
        rx.cond(
            item[1].product_catalog.uniq,
            rx.text(rx.cond(item[1].serial_number, item[1].serial_number, "—")),
            rx.text("—", color="gray"),
        ),
        style=_TD_TIGHT,
    )

def divisible_cell_text(item: Tuple[int, Product]):
    # Залишок (обсяг) показуємо лише для подільного ТМЦ — щоб бачити, скільки
    # одиниць виміру було переміщено/видано/продано/списано.
    return rx.el.td(
        rx.cond(
            item[1].product_catalog.divisible,
            rx.text(item[1].count),
            rx.text("—", color="gray"),
        ),
        style=_TD_TIGHT,
    )

def split_controls(item: Tuple[int, Product]):
    # Перемикач «Передати цілком / Розділити» (за замовчуванням — цілком) і поле обсягу.
    return rx.hstack(
        rx.segmented_control.root(
            rx.segmented_control.item("Цілком", value="whole"),
            rx.segmented_control.item("Розділити", value="split"),
            value=rx.cond(ProductsMovementListState.split_mode[item[1].id], "split", "whole"),
            on_change=lambda value: ProductsMovementListState.set_split_mode_value(item[1].id, value),
            size="1",
        ),
        rx.cond(
            ProductsMovementListState.split_mode[item[1].id],
            controls.input_field(
                type="number",
                min=1,
                max=item[1].count - 1,
                value=ProductsMovementListState.split_amount[item[1].id],
                on_change=lambda value: ProductsMovementListState.set_split_amount(item[1].id, value),
                placeholder="Обсяг",
                width="6em",
            ),
        ),
        spacing="2",
        align="center",
    )

def serial_cell_input(item: Tuple[int, Product]):
    # Для ТМЦ із серійним номером (uniq) — поле s/n, інакше прочерк. Червона
    # рамка (помилка) лише там, де s/n обов'язковий (require_serial) і не заповнений;
    # при переміщенні поле необов'язкове — рамку не підсвічуємо.
    return rx.el.td(
        rx.cond(
            item[1].product_catalog.uniq,
            controls.input_field(
                type="text",
                value=item[1].serial_number,
                on_change=lambda value: ProductsMovementListState.set_serial_number(item[1].id, value),
                placeholder="Серійний номер",
                style=rx.cond(
                    item[1].serial_number,
                    {},
                    rx.cond(
                        ProductsMovementListState.require_serial,
                        {"border": "1px solid red", "box-shadow": "0 0 0 1px red"},
                        {},
                    ),
                ),
            ),
            rx.text("—", color="gray"),
        ),
        style=_TD_TIGHT,
    )

def excluded_badge_cell(item: Tuple[int, Product]):
    return rx.el.td(
        rx.cond(
            item[1].excluded_from_accounting,
            rx.badge("Поза обліком", color_scheme="orange", size="1", variant="soft"),
            rx.text("—", color="gray"),
        ),
        style=_TD_TIGHT,
    )

# Внутрішні рядки одиниць ТМЦ (показуються при розгортанні позиції каталогу)
# ======================
def unit_row_view(item: Tuple[int, Product]):
    # Перегляд: клік по одиниці → її детальна сторінка.
    return rx.el.tr(
        rx.el.td(item[1].id, style=_TD_TIGHT),
        serial_cell_text(item),
        divisible_cell_text(item),
        excluded_badge_cell(item),
        on_click=rx.redirect(f"{routes.REPORTS_UNITS_VIEW_ID}{item[1].id}"),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 4)},
    )

def excluded_cell(item: Tuple[int, Product]):
    # Редагована позначка — лише там, де вмикається (повернення); інакше —
    # інформаційний бейдж поточного стану (як у перегляді).
    return rx.cond(
        ProductsMovementListState.show_excluded,
        rx.el.td(
            rx.checkbox(
                checked=ProductsMovementListState.excluded[item[1].id],
                on_change=lambda value: ProductsMovementListState.set_excluded(item[1].id, value),
            ),
            style=_TD_TIGHT,
        ),
        excluded_badge_cell(item),
    )

def unit_row_edit(item: Tuple[int, Product]):
    # Додавання/редагування: контроли поділу/серійного номера + видалення.
    return rx.el.tr(
        rx.el.td(item[1].id, style=_TD_TIGHT),
        rx.el.td(
            rx.cond(item[1].product_catalog.divisible, rx.text(item[1].count), rx.text("—", color="gray")),
            style=_TD_TIGHT,
        ),
        rx.el.td(
            rx.cond(item[1].product_catalog.divisible, split_controls(item), rx.text("Цілком", color="gray")),
            style=NESTED_DETAIL_TD,
        ),
        rx.cond(ProductsMovementListState.serial_visible, serial_cell_input(item)),
        excluded_cell(item),
        rx.el.td(
            rx.button(
                "Видалити",
                color_scheme="red",
                size="1",
                type="button",
                on_click=ProductsMovementListState.on_remove_selected(item[0]),
            ),
            style=_TD_TIGHT,
        ),
    )

def units_subtable(group):
    # Вкладена таблиця одиниць однієї позиції каталогу (group[6] — перелік одиниць).
    # Сирий rx.el.table (не rx.table.root) — Radix Table.Root безумовно загортає
    # <table> у ScrollArea з height:100%, яка всередині <td> (display:table-cell)
    # у Safari нестабільно резолвиться в 0 по-рядково, і контент розгорнутого
    # рядка (найчастіше останнього) не зʼявляється. Див. NESTED_DETAIL_* у
    # layouts.py — той самий підхід, що в перегляді продажу/повернення продажу.
    return rx.el.table(
        rx.el.thead(
            rx.cond(
                ProductsMovementListState.is_view_mode,
                rx.el.tr(
                    rx.el.th("ID ТМЦ", style=_TH_TIGHT),
                    rx.el.th("Серійний номер", style=NESTED_DETAIL_TH),
                    rx.el.th("Залишок", style=_TH_TIGHT),
                    rx.el.th("Поза обліком", style=_TH_TIGHT),
                ),
                rx.el.tr(
                    rx.el.th("ID ТМЦ", style=_TH_TIGHT),
                    rx.el.th("Залишок", style=_TH_TIGHT),
                    rx.el.th("Передача", style=NESTED_DETAIL_TH),
                    rx.cond(
                        ProductsMovementListState.serial_visible,
                        rx.el.th("Серійний номер", style=_TH_TIGHT),
                    ),
                    rx.el.th("Поза обліком", style=_TH_TIGHT),
                    rx.el.th("Дія", style=_TH_TIGHT),
                ),
            ),
            style=NESTED_DETAIL_THEAD,
        ),
        rx.el.tbody(
            rx.cond(
                ProductsMovementListState.is_view_mode,
                rx.foreach(group[6], unit_row_view),
                rx.foreach(group[6], unit_row_edit),
            ),
        ),
        style=NESTED_DETAIL_TABLE,
    )
# ======================

def group_fragment(group):
    # group = (id каталогу, назва, к-сть одиниць, подільне?, унікальне?, залишок, одиниці).
    # Клік по основних клітинках рядка розгортає/згортає перелік одиниць;
    # клітинки ціни/суми (продаж) не тогглять — щоб не заважати вводу ціни.
    clickable = dict(
        on_click=ProductsMovementListState.toggle_catalog(group[0]),
        cursor="pointer",
    )
    return rx.fragment(
        rx.table.row(
            rx.table.cell(
                rx.icon(
                    "chevron-down",
                    size=16,
                    color=rx.color("accent", 9),
                    style={
                        "transform": rx.cond(
                            ProductsMovementListState.expanded_catalogs[group[0]],
                            "rotate(0deg)",
                            "rotate(-90deg)",
                        ),
                        "transition": "transform 0.15s",
                    },
                ),
                width="1%", white_space="nowrap", **clickable,
            ),
            rx.table.cell(group[1], **clickable),
            rx.table.cell(group[2], width="1%", white_space="nowrap", **clickable),
            rx.table.cell(group[5], width="1%", white_space="nowrap", **clickable),
            rx.cond(
                ProductsMovementListState.require_price,
                rx.fragment(
                    rx.table.cell(
                        controls.input_field(
                            type="number",
                            min=0,
                            step="0.01",
                            value=ProductsMovementListState.prices[group[0]],
                            on_change=lambda value: ProductsMovementListState.set_price(group[0], value),
                            placeholder="Ціна за одиницю",
                            width="11em",
                        ),
                        width="1%", white_space="nowrap",
                    ),
                    rx.table.cell(
                        ProductsMovementListState.group_sums[group[0]],
                        width="1%", white_space="nowrap",
                    ),
                ),
            ),
            _hover={"background_color": rx.color("accent", 3)},
        ),
        rx.cond(
            ProductsMovementListState.expanded_catalogs[group[0]],
            rx.table.row(
                rx.table.cell(
                    rx.vstack(
                        serial_range_bar(group),
                        units_subtable(group),
                        width="100%",
                        spacing="2",
                    ),
                    custom_attrs={"colSpan": "6"},
                    padding="0.5em",
                ),
            ),
        ),
    )

def table():
    return rx.table.root(
        rx.table.header(
            rx.cond(
                ProductsMovementListState.require_price,
                rx.table.row(
                    rx.table.column_header_cell("", width="1%", white_space="nowrap"),
                    rx.table.column_header_cell("Назва", color=rx.color("accent", 2)),
                    rx.table.column_header_cell("К-сть одиниць", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                    rx.table.column_header_cell("Залишок", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                    rx.table.column_header_cell("Ціна за од.", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                    rx.table.column_header_cell("Сума", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                ),
                rx.table.row(
                    rx.table.column_header_cell("", width="1%", white_space="nowrap"),
                    rx.table.column_header_cell("Назва", color=rx.color("accent", 2)),
                    rx.table.column_header_cell("К-сть одиниць", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                    rx.table.column_header_cell("Залишок", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                ),
            ),

            background_color=rx.color("accent", 9)
        ),
        rx.table.body(
            rx.foreach(ProductsMovementListState.grouped, group_fragment),

            width="100%"
        ),

        # Без height="100%": у Radix `.rt-TableRootTable` має `height: 0` +
        # `overflow: hidden` (variant=surface) і є flex-елементом ScrollArea.
        # Поки висота батька auto, таблиця росте по контенту; щойно вона стає
        # визначеною (height:100%), ScrollArea фіксується й розгорнуті рядки
        # обрізаються. Висота тут не потрібна — віджет живе у vstack по контенту.
        variant="surface",
        width="100%"
    )

def total_section():
    # Загальна вартість (лише там, де require_price — напр. продаж).
    return rx.cond(
        ProductsMovementListState.require_price & ProductsMovementListState.has_items,
        rx.hstack(
            rx.spacer(),
            rx.heading(
                f"Загальна вартість: {ProductsMovementListState.total_cost}",
                size="4",
            ),
            width="100%",
        ),
    )

def serial_range_bar(group):
    # Пакетне заповнення серійних номерів діапазоном за маскою (напр. "СН-{n}") —
    # індивідуально для цієї позиції каталогу (різний ТМЦ може мати різні правила).
    catalog_id = group[0]
    return rx.cond(
        ProductsMovementListState.serial_visible & ~ProductsMovementListState.is_view_mode & group[4],
        rx.vstack(
            rx.hstack(
                controls.input_field(
                    placeholder="Маска, напр. СН-{n}",
                    value=ProductsMovementListState.serial_mask[catalog_id],
                    on_change=lambda value: ProductsMovementListState.on_change_serial_mask(catalog_id, value),
                    width="40%",
                ),
                controls.input_field(
                    placeholder="Від",
                    type="text",
                    value=ProductsMovementListState.serial_range_from[catalog_id],
                    on_change=lambda value: ProductsMovementListState.on_change_serial_range_from(catalog_id, value),
                    width="20%",
                ),
                controls.input_field(
                    placeholder="До",
                    type="text",
                    value=ProductsMovementListState.serial_range_to[catalog_id],
                    on_change=lambda value: ProductsMovementListState.on_change_serial_range_to(catalog_id, value),
                    width="20%",
                ),
                rx.button(
                    "Заповнити серійні номери",
                    type="button",
                    size="2",
                    on_click=ProductsMovementListState.fill_serial_range(catalog_id),
                ),
                width="100%",
                spacing="2",
            ),
            rx.text(
                rx.checkbox(
                    checked=ProductsMovementListState.serial_range_hex[catalog_id],
                    on_change=lambda value: ProductsMovementListState.on_change_serial_range_hex(catalog_id, value),
                ),
                " 16-та система числення (0-9, A-F)",
                as_="label",
                size="1",
            ),
            width="100%",
            spacing="1",
        ),
    )

def index(*args, **kwargs):
    return rx.vstack(
        rx.hstack(
            rx.heading("Товари:", size="3"),
            rx.spacer(),
            rx.cond(ProductsMovementListState.is_view_mode,
                    rx.fragment(),
                    rx.button("Додати",
                                type="button",
                                disabled=rx.cond(ProductsMovementListState.ability_open_dialog, False, True),
                                on_click=ProductsMovementListState.open_dialog,
                              )
                    ),
            width="100%"
        ),
        dialog(),
        rx.cond(ProductsMovementListState.has_items,
                table(),
                rx.center(rx.text("Нічого не обрано", color="gray"), width="100%", size="3")),
        total_section(),

        *args,
        **kwargs
    )