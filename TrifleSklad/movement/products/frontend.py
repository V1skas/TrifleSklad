import reflex as rx

from typing import Tuple

from TrifleSklad import routes
from TrifleSklad.models import Product
from TrifleSklad.movement.products.backend import ProductsMovementListState
from TrifleSklad.movement.products_selector.frontend import selector as products_selector


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
    return rx.table.cell(
        rx.cond(
            item[1].product_catalog.uniq,
            rx.text(rx.cond(item[1].serial_number, item[1].serial_number, "—")),
            rx.text("—", color="gray"),
        ),
        width="1%", white_space="nowrap",
    )

def divisible_cell_text(item: Tuple[int, Product]):
    # Залишок (обсяг) показуємо лише для подільного ТМЦ — щоб бачити, скільки
    # одиниць виміру було переміщено/видано/продано/списано.
    return rx.table.cell(
        rx.cond(
            item[1].product_catalog.divisible,
            rx.text(item[1].count),
            rx.text("—", color="gray"),
        ),
        width="1%", white_space="nowrap",
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
            rx.input(
                type="number",
                min=1,
                max=item[1].count - 1,
                value=ProductsMovementListState.split_amount[item[1].id],
                on_change=lambda value: ProductsMovementListState.set_split_amount(item[1].id, value),
                placeholder="Обсяг",
                width="6em",
                size="1",
            ),
        ),
        spacing="2",
        align="center",
    )

def serial_cell_input(item: Tuple[int, Product]):
    # Для ТМЦ із серійним номером (uniq) — поле s/n, інакше прочерк. Червона
    # рамка (помилка) лише там, де s/n обов'язковий (require_serial) і не заповнений;
    # при переміщенні поле необов'язкове — рамку не підсвічуємо.
    return rx.table.cell(
        rx.cond(
            item[1].product_catalog.uniq,
            rx.input(
                type="text",
                value=item[1].serial_number,
                on_change=lambda value: ProductsMovementListState.set_serial_number(item[1].id, value),
                placeholder="Серійний номер",
                size="1",
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
        width="1%", white_space="nowrap",
    )

# Внутрішні рядки одиниць ТМЦ (показуються при розгортанні позиції каталогу)
# ======================
def unit_row_view(item: Tuple[int, Product]):
    # Перегляд: клік по одиниці → її детальна сторінка.
    return rx.table.row(
        rx.table.cell(item[1].id, width="1%", white_space="nowrap"),
        serial_cell_text(item),
        divisible_cell_text(item),
        on_click=rx.redirect(f"{routes.REPORTS_UNITS_VIEW_ID}{item[1].id}"),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 4)},
    )

def unit_row_edit(item: Tuple[int, Product]):
    # Додавання/редагування: контроли поділу/серійного номера + видалення.
    return rx.table.row(
        rx.table.cell(item[1].id, width="1%", white_space="nowrap"),
        rx.table.cell(
            rx.cond(item[1].product_catalog.divisible, rx.text(item[1].count), rx.text("—", color="gray")),
            width="1%", white_space="nowrap",
        ),
        rx.table.cell(
            rx.cond(item[1].product_catalog.divisible, split_controls(item), rx.text("Цілком", color="gray")),
        ),
        rx.cond(ProductsMovementListState.serial_visible, serial_cell_input(item)),
        rx.table.cell(
            rx.button(
                "Видалити",
                color_scheme="red",
                size="1",
                type="button",
                on_click=ProductsMovementListState.on_remove_selected(item[0]),
            ),
            width="1%", white_space="nowrap",
        ),
    )

def units_subtable(group):
    # Вкладена таблиця одиниць однієї позиції каталогу (group[6] — перелік одиниць).
    return rx.table.root(
        rx.table.header(
            rx.cond(
                ProductsMovementListState.is_view_mode,
                rx.table.row(
                    rx.table.column_header_cell("ID ТМЦ", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                    rx.table.column_header_cell("Серійний номер", color=rx.color("accent", 2)),
                    rx.table.column_header_cell("Залишок", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                ),
                rx.table.row(
                    rx.table.column_header_cell("ID ТМЦ", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                    rx.table.column_header_cell("Залишок", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                    rx.table.column_header_cell("Передача", color=rx.color("accent", 2)),
                    rx.cond(
                        ProductsMovementListState.serial_visible,
                        rx.table.column_header_cell("Серійний номер", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                    ),
                    rx.table.column_header_cell("Дія", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                ),
            ),
            background_color=rx.color("accent", 6),
        ),
        rx.table.body(
            rx.cond(
                ProductsMovementListState.is_view_mode,
                rx.foreach(group[6], unit_row_view),
                rx.foreach(group[6], unit_row_edit),
            ),
        ),
        variant="surface",
        width="100%",
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
                        rx.input(
                            type="number",
                            min=0,
                            step="0.01",
                            value=ProductsMovementListState.prices[group[0]],
                            on_change=lambda value: ProductsMovementListState.set_price(group[0], value),
                            placeholder="Ціна за одиницю",
                            size="1",
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
                    units_subtable(group),
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

            height="100%",
            width="100%"
        ),

        variant="surface",
        height="100%",
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

def serial_range_bar():
    # Пакетне заповнення серійних номерів діапазоном за маскою (напр. "СН-{n}").
    return rx.cond(
        ProductsMovementListState.serial_visible & ~ProductsMovementListState.is_view_mode & ProductsMovementListState.has_items,
        rx.vstack(
            rx.hstack(
                rx.input(
                    placeholder="Маска, напр. СН-{n}",
                    value=ProductsMovementListState.serial_mask,
                    on_change=ProductsMovementListState.on_change_serial_mask,
                    size="2",
                    width="40%",
                ),
                rx.input(
                    placeholder="Від",
                    type="text",
                    value=ProductsMovementListState.serial_range_from,
                    on_change=ProductsMovementListState.on_change_serial_range_from,
                    size="2",
                    width="20%",
                ),
                rx.input(
                    placeholder="До",
                    type="text",
                    value=ProductsMovementListState.serial_range_to,
                    on_change=ProductsMovementListState.on_change_serial_range_to,
                    size="2",
                    width="20%",
                ),
                rx.button(
                    "Заповнити серійні номери",
                    type="button",
                    size="2",
                    on_click=ProductsMovementListState.fill_serial_range,
                ),
                width="100%",
                spacing="2",
            ),
            rx.text(
                rx.checkbox(
                    checked=ProductsMovementListState.serial_range_hex,
                    on_change=ProductsMovementListState.on_change_serial_range_hex,
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
                    rx.Component(),
                    rx.button("Додати",
                                type="button",
                                disabled=rx.cond(ProductsMovementListState.ability_open_dialog, False, True),
                                on_click=ProductsMovementListState.open_dialog,
                              )
                    ),
            width="100%"
        ),
        dialog(),
        serial_range_bar(),
        rx.cond(ProductsMovementListState.has_items,
                table(),
                rx.center(rx.text("Нічого не обрано", color="gray"), width="100%", size="3")),
        total_section(),

        *args,
        **kwargs
    )