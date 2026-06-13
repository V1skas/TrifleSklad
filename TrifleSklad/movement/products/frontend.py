import reflex as rx

from typing import Tuple

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

def table_row_view_mode(item: Tuple[int, Product]):
    return rx.table.row(
        rx.table.cell(item[1].id, width="1%", white_space="nowrap"),
        rx.table.cell(item[1].product_catalog.title),
        divisible_cell_text(item),
        serial_cell_text(item),
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
    # Для ТМЦ із серійним номером (uniq) — обов'язкове поле s/n, інакше прочерк.
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
                    {"border": "1px solid red", "box-shadow": "0 0 0 1px red"},
                ),
            ),
            rx.text("—", color="gray"),
        ),
        width="1%", white_space="nowrap",
    )

def table_row(item: Tuple[int, Product]):
    return rx.table.row(
        rx.table.cell(item[1].id, width="1%", white_space="nowrap"),
        rx.table.cell(item[1].product_catalog.title),
        rx.table.cell(
            rx.cond(item[1].product_catalog.divisible, rx.text(item[1].count), rx.text("—")),
            width="1%", white_space="nowrap",
        ),
        rx.table.cell(
            rx.cond(item[1].product_catalog.divisible, split_controls(item), rx.text("Цілком", color="gray")),
        ),
        rx.cond(ProductsMovementListState.require_serial, serial_cell_input(item)),
        rx.table.cell(rx.button("Видалити", color_scheme="red", on_click=ProductsMovementListState.on_remove_selected(item[0])), width="1", white_space="nowrap"),
    )

def table():
    return rx.table.root(
        rx.table.header(
            rx.cond(ProductsMovementListState.is_view_mode,
                    rx.table.row(
                        rx.table.column_header_cell("ID ТМЦ", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                        rx.table.column_header_cell("Назва", color=rx.color("accent", 2)),
                        rx.table.column_header_cell("Залишок", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                        rx.table.column_header_cell("Серійний номер", color=rx.color("accent", 2), width="1%", white_space="nowrap")),
                    rx.table.row(
                        rx.table.column_header_cell("ID ТМЦ", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                        rx.table.column_header_cell("Назва", color=rx.color("accent", 2)),
                        rx.table.column_header_cell("Ємність", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                        rx.table.column_header_cell("Передача", color=rx.color("accent", 2)),
                        rx.cond(ProductsMovementListState.require_serial,
                                rx.table.column_header_cell("Серійний номер", color=rx.color("accent", 2), width="1%", white_space="nowrap")),
                        rx.table.column_header_cell("Дія", color=rx.color("accent", 2), width="1%", white_space="nowrap")),
                    ),

            background_color=rx.color("accent", 9)
        ),
        rx.table.body(
            rx.cond(
                ProductsMovementListState.is_view_mode,
                rx.foreach(ProductsMovementListState.get_items, table_row_view_mode),
                rx.foreach(ProductsMovementListState.get_items, table_row)
            ),

            height="100%",
            width="100%"
        ),

        variant="surface",
        height="100%",
        width="100%"
    )

def price_row(item: Tuple[int, str, int]):
    # item = (id позиції каталогу, назва, кількість одиниць).
    return rx.table.row(
        rx.table.cell(item[1]),
        rx.table.cell(item[2], width="1%", white_space="nowrap"),
        rx.table.cell(
            rx.input(
                type="number",
                min=0,
                step="0.01",
                value=ProductsMovementListState.prices[item[0]],
                on_change=lambda value: ProductsMovementListState.set_price(item[0], value),
                placeholder="Ціна за одиницю",
                size="1",
                width="11em",
            ),
            width="1%", white_space="nowrap",
        ),
    )

def prices_section():
    # Секція вводу цін за позиціями (лише там, де require_price — напр. продаж).
    return rx.cond(
        ProductsMovementListState.require_price & ProductsMovementListState.has_items,
        rx.vstack(
            rx.heading("Вартість позицій:", size="3", width="100%"),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Позиція", color=rx.color("accent", 2)),
                        rx.table.column_header_cell("Кількість", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                        rx.table.column_header_cell("Ціна за одиницю", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                    ),
                    background_color=rx.color("accent", 9),
                ),
                rx.table.body(
                    rx.foreach(ProductsMovementListState.price_positions, price_row),
                ),
                variant="surface",
                width="100%",
            ),
            rx.hstack(
                rx.spacer(),
                rx.heading(
                    f"Загальна вартість: {ProductsMovementListState.total_cost}",
                    size="4",
                ),
                width="100%",
            ),
            width="100%",
            spacing="2",
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
        rx.cond(ProductsMovementListState.has_items,
                table(),
                rx.center(rx.text("Нічого не обрано", color="gray"), width="100%", size="3")),
        prices_section(),

        *args,
        **kwargs
    )