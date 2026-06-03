import reflex as rx

from typing import Tuple

from TrifleSklad.models import MovementProductsCatalog
from TrifleSklad.movement.products_catalog.backend import MovementProductCatalogState, MovementProductCatalogListState

def view_page():
    return rx.vstack(
        rx.heading("Товарна позиція"),
        rx.hstack(
            rx.text("Назва:"),
            rx.text(rx.cond(MovementProductCatalogState.item.product,
                            MovementProductCatalogState.item.product.title, "Не вказано"))
        ),
        rx.hstack(
            rx.text("Кількість:"),
            rx.text(MovementProductCatalogState.item.count)
        ),
        rx.hstack(
            rx.text("Вартість за одиницю:"),
            rx.text(MovementProductCatalogState.item.price)
        ),

        width="100%",
        height="100%"
    )

def add_page():
    return rx.vstack(
        rx.heading("Додавання товарної позиції"),
        rx.text("Назва:"),
        rx.select.root(
            rx.select.trigger(
                placeholder="Оберіть зі списку",

                style=rx.cond(
                    MovementProductCatalogState.product_error,
                    {"border": "1px solid red", "background-color": "#fef2f2"},
                    {}
                ),

                width="100%",
            ),
            rx.select.content(
                rx.foreach(
                    MovementProductCatalogState.products_catalog_list,
                    lambda product: rx.select.item(product[0], value=product[1])
                ),

                width="100%",
            ),

            value=MovementProductCatalogState.product,

            on_change=MovementProductCatalogState.on_change_product,

            width="100%"
        ),
        rx.text("Кількість:"),
        rx.input(
            type="number",
            min="0",
            default_value="0",
            value=MovementProductCatalogState.count,

            style=rx.cond(
                MovementProductCatalogState.count_error,
                {"border": "1px solid red", "background-color": "#fef2f2"},
                {}
            ),

            width="100%",

            on_change=MovementProductCatalogState.on_change_count
        ),

        rx.text("Вартість за одиницю:"),
        rx.input(
            type="number",
            min="0.0",
            default_value="0.0",
            value=MovementProductCatalogState.price,

            style=rx.cond(
                MovementProductCatalogState.price_error,
                {"border": "1px solid red", "background-color": "#fef2f2"},
                {}
            ),

            width="100%",

            on_change=MovementProductCatalogState.on_change_price
        ),

        width="100%",
        height="100%"
    )


def edit_page():
    return rx.vstack(
        rx.heading("Редагування товарної позиції"),
        rx.text("Назва:"),
        rx.select.root(
            rx.select.trigger(
                placeholder="Оберіть зі списку",

                style=rx.cond(
                    MovementProductCatalogState.product_error,
                    {"border": "1px solid red", "background-color": "#fef2f2"},
                    {}
                ),

                width="100%",
            ),
            rx.select.content(
                rx.foreach(
                    MovementProductCatalogState.products_catalog_list,
                    lambda product: rx.select.item(product[0], value=product[1])
                ),

                width="100%",
            ),

            value=MovementProductCatalogState.product,

            on_change=MovementProductCatalogState.on_change_product,

            width="100%"
        ),
        rx.text("Кількість:"),
        rx.input(
            type="number",
            min="0",
            default_value="0",
            value=MovementProductCatalogState.count,
            style=rx.cond(
                MovementProductCatalogState.count_error,
                {"border": "1px solid red", "background-color": "#fef2f2"},
                {}
            ),
            width="100%",
            on_change=MovementProductCatalogState.on_change_count
        ),
        rx.text("Вартість за одиницю:"),
        rx.input(
            type="number",
            min="0.0",
            default_value="0.0",
            value=MovementProductCatalogState.price,
            style=rx.cond(
                MovementProductCatalogState.price_error,
                {"border": "1px solid red", "background-color": "#fef2f2"},
                {}
            ),
            width="100%",
            on_change=MovementProductCatalogState.on_change_price
        ),

        width="100%",
        height="100%"
    )

def dialog():
    return rx.dialog.root(
        rx.dialog.content(
            rx.tabs.root(
                rx.tabs.content(
                    rx.vstack(
                        add_page(),
                        rx.cond(MovementProductCatalogState.has_error,
                                rx.text(MovementProductCatalogState.error_text, color="red")),
                        rx.hstack(
                            rx.button("Зберегти", on_click=MovementProductCatalogListState.on_save),
                            rx.button("Скасувати", on_click=MovementProductCatalogListState.close_dialog),

                            width="100%"
                        ),

                        width="100%",
                        height="100%"
                    ),

                    value=MovementProductCatalogState.Pages.ADD,

                    width="100%",
                    height="100%"
                ),
                rx.tabs.content(
                    rx.vstack(
                        edit_page(),
                        rx.cond(MovementProductCatalogState.has_error,
                                rx.text(MovementProductCatalogState.error_text, color_scheme="red")),
                        rx.hstack(
                            rx.button("Зберегти", on_click=MovementProductCatalogListState.on_save),
                            rx.button("Скасувати", on_click=MovementProductCatalogListState.close_dialog)
                        ),

                        width="100%",
                        height="100%"
                    ),

                    value=MovementProductCatalogState.Pages.EDIT,

                    width="100%",
                    height="100%"
                ),
                rx.tabs.content(
                    rx.vstack(
                        view_page(),
                        rx.spacer(),
                        rx.hstack(
                            rx.button("Редагувати", on_click=MovementProductCatalogState.on_click_edit()),
                            rx.button("Видалити", color_scheme="red", on_click=MovementProductCatalogListState.on_delete())
                        ),

                        width="100%",
                        height="100%"
                    ),

                    value=MovementProductCatalogState.Pages.VIEW,

                    width="100%",
                    height="100%"
                ),

                value=MovementProductCatalogState.current_page,

                width="100%",
                height="100%"
            ),

            width="35em",
            height="25em"
        ),

        open=MovementProductCatalogListState.is_open_dialog,
        on_open_change=MovementProductCatalogListState.close_dialog

    )

def table_row_view_mode(item: Tuple[int, MovementProductsCatalog]):
    return rx.table.row(
        rx.table.cell(item[1].product.title),
        rx.table.cell(item[1].count),
        rx.table.cell(item[1].price)
    )

def table_row(item: Tuple[int, MovementProductsCatalog]):
    return rx.table.row(
        rx.table.cell(rx.link(item[1].product.title, on_click=MovementProductCatalogListState.on_view(item[0]))),
        rx.table.cell(item[1].count),
        rx.table.cell(item[1].price)
    )

def table():
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Товар", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Количество", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Вартість", color=rx.color("accent", 2)),
            ),

            background_color=rx.color("accent", 9)
        ),
        rx.table.body(
            rx.cond(
                MovementProductCatalogListState.is_view_mode,
                rx.foreach(MovementProductCatalogListState.get_items, table_row_view_mode),
                rx.foreach(MovementProductCatalogListState.get_items, table_row)
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
            rx.cond(MovementProductCatalogListState.is_view_mode,
                    rx.Component(),
                    rx.button("Додати", type="button", on_click=MovementProductCatalogListState.on_add)),
            width="100%"
        ),
        rx.cond(MovementProductCatalogListState.has_items,
                table(),
                rx.center(rx.text("Нічого не обрано", color="gray"), width="100%", size="3")),
        dialog(),
        rx.cond(MovementProductCatalogListState.is_view_mode,
                rx.Component(),
                rx.hstack(
                    rx.text("Загальна вартість:"),
                    rx.input(id="total_cost", type="number", read_only=True,
                             value=f"{MovementProductCatalogListState.total_cost}")
                )),

        *args,
        **kwargs
    )