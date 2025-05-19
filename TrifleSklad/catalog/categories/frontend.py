import reflex as rx

from TrifleSklad import routes
from TrifleSklad.catalog.categories.backend import *

from TrifleSklad.models import ProductCategory

def item_preview(item: Tuple[int, ProductCategory]) -> rx.Component:
    return rx.vstack(
        rx.heading(item[1].title, size="7", width="100%"),
        rx.text(item[1].description, is_optional=True, width="100%"),
        rx.spacer(),
        rx.hstack(
            rx.button(
                "Редактировать",

                on_click=rx.redirect(f"{routes.CATALOG_CATEGORIES_EDIT_ID}{item[1].id}")
            ),
            rx.spacer(),
            rx.button(
                "Удалить",
                color_scheme="red",

                on_click=CategoriesState.delete_one
            ),

            width="100%",
        ),

        spacing="3",

        height="100%",
        width="100%"
    )

def item_preview_tab_content() -> rx.Component:
    return rx.tabs.content(
        item_preview(CategoriesState.get_selected_item),

        value=CategoriesState.Pages.VIEW
    )

def table_row(item: Tuple[int, ProductCategory]) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(
            rx.link(
                item[1].title,
                href=f"{routes.CATALOG_CATEGORIES_VIEW_ID}{item[1].id}"
            ),

            align="left"
        )
    )

def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Название", color=rx.color("accent", 2)),
            ),

            background_color=rx.color("accent", 9)
        ),
        rx.table.body(
            rx.foreach(CategoriesState.get_items, table_row),

            height="100%",
            width="100%"
        ),

        variant="surface",
        height="100%",
        width="100%"
    )

def list_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            rx.heading("Категории ТМЦ", size="7", width="100%"),
            rx.cond(CategoriesState.has_items,
                table(),
                rx.text("Записей нет.")
            ),
            rx.hstack(
                rx.button("Добавить", on_click=rx.redirect(routes.CATALOG_CATEGORIES_ADD)),

                justify="end"
            ),

            width="100%",
            height="100%",
        ),

        value=CategoriesState.Pages.LIST,
    )

def add_form() -> rx.Component:
    return rx.card(
        rx.form(
            rx.vstack(
                rx.text("Название:"),
                rx.input(id="title", required=True, size="3"),
                rx.text("Описание:"),
                rx.text_area(id="description", size="3"),
                rx.hstack(
                    rx.button("Отмена", type="reset", color_scheme="red", on_click=rx.redirect(routes.CATALOG_CATEGORIES)),
                    rx.button("Сохранить", color_scheme="green", type="submit"),

                    justify="end"
                ),

                align="stretch"
            ),

            on_submit=CategoriesState.add_one,
        ),

        height="100%",
        width="100%"
    )

def edit_form(item: Tuple[int, ProductCategory]) -> rx.Component:
    return rx.card(
        rx.form(
            rx.vstack(
                rx.text("Название:"),
                rx.input(id="title", default_value=item[1].title, required=True, size="3"),
                rx.text("Описание:"),
                rx.text_area(id="description", default_value=item[1].description, size="3", is_optional=True),
                rx.hstack(
                    rx.button("Отмена", type="reset", color_scheme="red", on_click=rx.redirect(routes.CATALOG_CATEGORIES)),
                    rx.button("Сохранить", color_scheme="green", type="submit"),

                    justify="end"
                ),

                align="stretch"
            ),

            on_submit=CategoriesState.edit_one,
        ),

        height="100%",
        width="100%"
    )

def add_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading("Добавление категории", size="7", width="100%", margin_bottom="0.5em"),
        add_form(),

        value=CategoriesState.Pages.ADD
    )

def edit_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading("Редактирование категории", size="7", width="100%", margin_bottom="0.5em"),
        edit_form(CategoriesState.get_selected_item),

        value=CategoriesState.Pages.EDIT
    )

def index() -> rx.Component:
    return rx.tabs.root(
        list_tab_content(),
        add_tab_content(),
        edit_tab_content(),
        item_preview_tab_content(),

        value=CategoriesState.current_page,

        height="100%",
        width="100%"
    )
