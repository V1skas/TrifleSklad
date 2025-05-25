import reflex as rx

from TrifleSklad import routes
from TrifleSklad.catalog.products.backend import *

from TrifleSklad.models import ProductCatalog
from TrifleSklad.dao import ProductCategoryDAO

def item_preview(item: Tuple[int, ProductCatalog]) -> rx.Component:
    return rx.vstack(
        rx.heading(item[1].title, size="7", width="100%"),
        rx.text(item[1].description, is_optional=True, width="100%"),
        rx.hstack(
            rx.text(f"Единица измерения: {item[1].unit}", width="50%"),
            rx.text(f"Количество: {item[1].count}", width="50%"),
            width="100%"
        ),
        rx.hstack(
            rx.cond(
                item[1].divisible,
                rx.text("Делимый: Да", width="50%"),
                rx.text("Делимый: Нет", width="50%")
            ),

            rx.text(f"Вместимость: {item[1].capacity}", width="50%"),
            width="100%"
        ),
        rx.cond(
            item[1].category,
            rx.text(f"Категория: {item[1].category.title}", width="100%"),
            rx.text("Категория не указана", width="100%")
        ),
        rx.spacer(),
        rx.hstack(
            rx.button(
                "Редактировать",
                on_click=rx.redirect(f"{routes.CATALOG_PRODUCTS_EDIT_ID}{item[1].id}")
            ),
            rx.spacer(),
            rx.button(
                "Удалить",
                color_scheme="red",
                on_click=ProductsState.delete_one
            ),
            width="100%",
        ),

        spacing="3",
        height="100%",
        width="100%"
    )

def item_preview_tab_content() -> rx.Component:
    return rx.tabs.content(
        item_preview(ProductsState.get_selected_item),
        value=ProductsState.Pages.VIEW
    )

def table_row(item: Tuple[int, ProductCatalog]) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(
            rx.link(
                item[1].title,
                href=f"{routes.CATALOG_PRODUCTS_VIEW_ID}{item[1].id}"
            ),
            align="left"
        ),
        rx.table.cell(
            rx.text(item[1].category.title)
        ),
        rx.table.cell(
            rx.text(item[1].unit)
        ),
        rx.table.cell(
            rx.cond(
                item[1].divisible,
                rx.text("Да"),
                rx.text("Нет")
            )
        ),
        rx.table.cell(
            rx.text(item[1].capacity)
        ),
    )

def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Название", align="left", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Категория", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Единица измерения", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Делимый", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Вместимость", color=rx.color("accent", 2)),
            ),

            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(
                ProductsState.get_items,
                table_row
            )
        ),

        variant="surface",
        width="100%"
    )

def table_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            rx.hstack(
                rx.heading("Товары", size="6"),
                rx.spacer(),
                rx.button(
                    "Добавить",
                    on_click=rx.redirect(routes.CATALOG_PRODUCTS_ADD)
                ),

                width="100%"
            ),
            rx.cond(
                ProductsState.has_items,
                table(),
                rx.text("Нет данных для отображения")
            ),

            spacing="3",
            width="100%"
        ),

        value=ProductsState.Pages.LIST
    )

def add_form() -> rx.Component:
    return rx.form(
        rx.vstack(
            rx.heading("Добавить товар", size="6"),
            
            rx.text("Название", size="3", width="100%"),
            rx.input(id="title", required=True, size="3", width="100%"),
            rx.text("Описание", size="3", width="100%"),
            rx.text_area(id="description", size="3", width="100%"),
            rx.text("Категория", size="3", width="100%"),
            rx.select(
                [category.title for category in ProductCategoryDAO.get_all()],

                name="id_category",
                required=True,
                placeholder="Выберите категорию",
                size="3",
                width="100%"
            ),
            rx.text("Единица измерения", size="3", width="100%"),
            rx.input(id="unit", required=True, size="3", width="100%"),
            rx.text("Вместимость", size="3", width="100%"),
            rx.input(id="capacity", required=True, size="3", width="100%"),
            rx.checkbox(
                "Делимый товар",
                id="divisible",
                size="3",
                width="100%"
            ),
            
            rx.hstack(
                rx.button(
                    "Отмена",
                    type="button",
                    variant="soft",
                    on_click=rx.redirect(routes.CATALOG_PRODUCTS)
                ),
                rx.spacer(),
                rx.button(
                    "Добавить",
                    type="submit"
                ),

                width="100%"
            ),

            spacing="3",
            width="100%"
        ),

        on_submit=ProductsState.add_one,
        width="100%"
    )

def add_tab_content() -> rx.Component:
    return rx.tabs.content(
        add_form(),
        value=ProductsState.Pages.ADD
    )

def edit_form(item: Tuple[int, ProductCatalog]) -> rx.Component:
    return rx.form(
        rx.vstack(
            rx.heading("Редактировать товар", size="6"),
            
            rx.text("Название", size="3", width="100%"),
            rx.input(id="title", required=True, default_value=item[1].title, size="3", width="100%"),
            rx.text("Описание", size="3", width="100%"),
            rx.text_area(id="description", default_value=item[1].description, is_optional=True, size="3", width="100%"),
            rx.text("Категория", size="3", width="100%"),
            rx.select(
                [category.title for category in ProductCategoryDAO.get_all()],
                default_value=item[1].category.title,

                name="id_category",
                required=True,
                placeholder="Выберите категорию",
                size="3",
                width="100%"
            ),
            rx.text("Единица измерения", size="3", width="100%"),
            rx.input(id="unit", required=True, default_value=item[1].unit, size="3", width="100%"),
            rx.text("Вместимость", size="3", width="100%"),
            rx.input(id="capacity", required=True, default_value=str(item[1].capacity), size="3", width="100%"),
            rx.checkbox(
                "Делимый товар",
                default_value=item[1].divisible,
                id="divisible",
                size="3",
                width="100%"
            ),
            
            rx.hstack(
                rx.button(
                    "Отмена",
                    type="button",
                    variant="soft",
                    on_click=rx.redirect(routes.CATALOG_PRODUCTS)
                ),
                rx.spacer(),
                rx.button(
                    "Добавить",
                    type="submit"
                ),

                width="100%"
            ),

            spacing="3",
            width="100%"
        ),

        on_submit=ProductsState.edit_one,
        width="100%"
    )

def edit_tab_content() -> rx.Component:
    return rx.tabs.content(
        edit_form(ProductsState.get_selected_item),
        value=ProductsState.Pages.EDIT
    )

def index() -> rx.Component:
    return rx.tabs.root(
        table_tab_content(),
        item_preview_tab_content(),
        add_tab_content(),
        edit_tab_content(),

        value=ProductsState.current_page,
        on_change=ProductsState.set_current_page,

        orientation="horizontal",
        width="100%"
    )
