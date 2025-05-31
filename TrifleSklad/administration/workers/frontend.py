import reflex as rx
from reflex.utils.types import is_optional

from TrifleSklad import routes
from TrifleSklad.administration.workers.backend import *

def item_preview(item: Tuple[int, Worker]) -> rx.Component:
    return rx.vstack(
        rx.heading(item[1].fio, size="7", width="100%"),
        rx.text(item[1].position, width="100%"),
        rx.text(item[1].phone_number, width="100%"),
        rx.text(item[1].email, width="100%"),
        rx.spacer(),
        rx.hstack(
            rx.button(
                "Редактировать",

                on_click=rx.redirect(f"{routes.ADMIN_WORKERS_EDIT_ID}{item[1].id}")
            ),
            rx.spacer(),
            rx.button(
                "Удалить",
                color_scheme="red",

                on_click=WorkersState.delete_one
            ),

            width="100%",
        ),

        spacing="3",

        height="100%",
        width="100%"
    )

def item_preview_tab_content() -> rx.Component:
    return rx.tabs.content(
        item_preview(WorkersState.get_selected_item),

        value=WorkersState.Pages.VIEW
    )

def table_row(item: Tuple[int, Worker]) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(
            rx.link(
                item[1].fio,
                href=f"{routes.ADMIN_WORKERS_VIEW_ID}{item[1].id}",
            ),

            align="left"
        ),
        rx.table.cell(
            item[1].position,
            align="left"
        ),
        rx.table.cell(
            item[1].phone_number,
            align="left"
        ),
        rx.table.cell(
            item[1].email,
            align="left"
        ),
    )

def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Фамилия И.О.", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Должность", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Телефон", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Email", color=rx.color("accent", 2)),
            ),

            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(WorkersState.get_items, table_row),

            height="100px",
            width="100%"
        ),

        variant="surface",
        height="100%",
        width="100%"
    )

def list_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            rx.hstack(
                rx.heading("Сотрудники", size="6"),
                rx.spacer(),
                rx.button(
                    "Добавить",
                    on_click=rx.redirect(routes.CATALOG_PRODUCTS_ADD)
                ),

                width="100%"
            ),
            rx.cond(WorkersState.has_items,
                table(),
                rx.text("Записей нет.")
            ),

            width="100%",
            height="100%",
        ),

        value=WorkersState.Pages.LIST,
    )

def add_form() -> rx.Component:
    return rx.card(
        rx.form(
            rx.vstack(
                rx.text("Фамилия И.О.:"),
                rx.input(
                    name="fio",
                    required=True,
                    width="100%",
                ),
                rx.text("Должность:"),
                rx.input(
                    name="position",
                    required=True,
                    width="100%",
                ),
                rx.text("Телефон:"),
                rx.input(
                    type="tel",
                    name="phone_number",
                    required=True,
                    width="100%",
                ),
                rx.text("Email:"),
                rx.input(
                    type="email",
                    name="email",
                    required=True,
                    width="100%",
                ),
                rx.hstack(
                    rx.button("Отмена", type="reset", color_scheme="red", on_click=rx.redirect(routes.ADMIN_WORKERS)),
                    rx.button("Сохранить", color_scheme="green", type="submit"),

                    justify="end"
                ),

                align="stretch"
            ),

            on_submit=WorkersState.add_one,
        ),

        height="100%",
        width="100%",
    )

def edit_form(item: Tuple[int, Worker]) -> rx.Component:
    return rx.card(
        rx.form(
            rx.vstack(
                rx.text("Фамилия И.О.:"),
                rx.input(
                    name="fio",
                    required=True,
                    default_value=item[1].fio,
                    width="100%",
                ),
                rx.text("Должность:"),
                rx.input(
                    name="position",
                    required=True,
                    default_value=item[1].position,
                    is_optional=True,
                    width="100%",
                ),
                rx.text("Телефон:"),
                rx.input(
                    type="tel",
                    name="phone_number",
                    required=True,
                    default_value=item[1].phone_number,
                    is_optional=True,
                    width="100%",
                ),
                rx.text("Email:"),
                rx.input(
                    type="email",
                    name="email",
                    required=True,
                    default_value=item[1].email,
                    width="100%",
                ),
                rx.hstack(
                    rx.button("Отмена", type="reset", color_scheme="red", on_click=rx.redirect(f"{routes.ADMIN_WORKERS_VIEW_ID}{item[1].id}")),
                    rx.button("Сохранить", color_scheme="green", type="submit"),

                    justify="end"
                ),

                align="stretch"
            ),

            on_submit=WorkersState.edit_one,
        ),

        height="100%",
        width="100%",
    )

def add_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading("Добавление информации о сотруднике", size="7", width="100%", margin_bottom="0.5em"),
        add_form(),

        value=WorkersState.Pages.ADD
    )

def edit_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading("Редактирование информации о сотруднике", size="7", width="100%", margin_bottom="0.5em"),
        edit_form(WorkersState.get_selected_item),

        value=WorkersState.Pages.EDIT
    )

def index() -> rx.Component:
    return rx.tabs.root(
        list_tab_content(),
        add_tab_content(),
        edit_tab_content(),
        item_preview_tab_content(),

        value=WorkersState.current_page,

        height="100%",
        width="100%"
    )
