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

            width="29em",
            height="35em"
        ),

        open=ProductsMovementListState.dialog_open,
        on_open_change=ProductsMovementListState.close_dialog,
    )

def table_row_view_mode(item: Tuple[int, Product]):
    return rx.table.row(
        rx.table.cell(item[1].id, width="1%", white_space="nowrap"),
        rx.table.cell(item[1].product_catalog.title)
    )

def table_row(item: Tuple[int, Product]):
    return rx.table.row(
        rx.table.cell(item[1].id, width="1%", white_space="nowrap"),
        rx.table.cell(item[1].product_catalog.title),
        rx.table.cell(rx.button("Видалити", color_scheme="red", on_click=ProductsMovementListState.on_remove_selected(item[0])), width="1", white_space="nowrap"),
    )

def table():
    return rx.table.root(
        rx.table.header(
            rx.cond(ProductsMovementListState.is_view_mode,
                    rx.table.row(
                        rx.table.column_header_cell("ID ТМЦ", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                        rx.table.column_header_cell("Назва", color=rx.color("accent", 2))),
                    rx.table.row(
                        rx.table.column_header_cell("ID ТМЦ", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                        rx.table.column_header_cell("Назва", color=rx.color("accent", 2)),
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

        *args,
        **kwargs
    )