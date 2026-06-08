from textwrap import wrap

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum

from TrifleSklad.catalog.products.backend import AddProductsState, EditProductsState, ViewProductsState, ListProductsState, ProductsState

from TrifleSklad.models import ProductCatalog


def create_category_dialog(State) -> rx.Component:
    # Вкладений діалог створення нової категорії прямо з форми товару.
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Створення категорії"),
            rx.vstack(
                rx.text("*Назва:", size="2"),
                rx.input(
                    value=State.new_category_title,
                    on_change=State.on_change_new_category_title,
                    width="100%",
                ),
                rx.text("Опис:", size="2"),
                rx.text_area(
                    value=State.new_category_description,
                    on_change=State.on_change_new_category_description,
                    width="100%",
                ),
                rx.hstack(
                    rx.button(
                        "Скасувати",
                        variant="outline",
                        type="button",
                        on_click=State.set_create_category_open(False),
                    ),
                    rx.spacer(),
                    rx.button("Створити", type="button", on_click=State.create_category),
                    width="100%",
                    padding_top="0.5em",
                ),
                spacing="2",
                width="100%",
            ),
            width="28em",
        ),
        open=State.is_create_category_open,
        on_open_change=State.set_create_category_open,
    )


def category_select_row(State) -> rx.Component:
    # Селект категорії + кнопка створення нової категорії на льоту.
    return rx.vstack(
        rx.select.root(
            rx.select.trigger(
                placeholder="Оберіть зі списку",
                width="100%",
            ),
            rx.select.content(
                rx.foreach(
                    State.list_categories,
                    lambda category: rx.select.item(
                        category[1],
                        value=category[0],
                    ),
                ),
                width="100%",
            ),
            name="id_category",
            required=True,
            value=State.category_id,
            on_change=State.on_change_category,
            size="3",
            width="100%",
        ),
        rx.hstack(
            rx.spacer(),
            rx.cond(
                AppState.get_user_actions.contains(ActionEnum.CATEGORIES_CREATE),
                rx.button(
                    rx.icon("plus", size=14),
                    "Створити категорію",
                    variant="ghost",
                    size="2",
                    type="button",
                    on_click=State.open_create_category,
                ),
            ),
            width="100%",
        ),
        create_category_dialog(State),
        spacing="1",
        width="100%",
    )


def item_preview() -> rx.Component:
    return rx.vstack(
        rx.heading(ViewProductsState.title, size="7", width="100%"),
        rx.text(ViewProductsState.description, is_optional=True, width="100%"),
        rx.hstack(
            rx.text(f"Единица измерения: {ViewProductsState.unit}", width="50%"),
            rx.text(f"Количество: {ViewProductsState.count}", width="50%"),
            width="100%"
        ),
        rx.hstack(
            rx.cond(
                ViewProductsState.divisible,
                rx.text("Подільний: Так", width="50%"),
                rx.text("Подільний: Ні", width="50%")
            ),
            
            rx.cond(ViewProductsState.divisible,
                rx.text(f"Місткість: {ViewProductsState.capacity}", width="50%"),
                rx.text("Місткість: -", width="50%")
            ),
            width="100%"
        ),
        rx.hstack(
            rx.cond(
                ViewProductsState.uniq,
                rx.text("Має серійний номер: Так", width="50%"),
                rx.text("Має серійний номер: Ні", width="50%")
            ),

            rx.cond(
                ViewProductsState.category,
                rx.text(f"Категорія: {ViewProductsState.category}", width="50%"),
                rx.text("Категорія не зазначена", width="50%")
            ),

            width="100%"
        ),

        spacing="3",
        height="100%",
        width="100%"
    )

def item_preview_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            rx.box(
                rx.hstack(
                    rx.button(
                        "Повернутись",
                        variant="ghost",
                        size="3",
                        on_click=rx.redirect(routes.CATALOG_PRODUCTS)
                    ),
                    rx.heading("Каталог ТМЦ/Перегляд", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.PRODUCTS_DELETE),
                            rx.button(
                                "Видалити",
                                color_scheme="red",
                                variant="ghost",
                                size="3",
                                on_click=ProductsState.delete_one(ViewProductsState.item.id)
                            ),                            
                        ),
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.PRODUCTS_EDIT),
                            rx.button(
                                "Редагувати",
                                variant="ghost",
                                size="3",
                                on_click=rx.redirect(f"{routes.CATALOG_PRODUCTS_EDIT_ID}{ViewProductsState.item.id}")
                            ),                          
                        ),

                        spacing="6",
                    ),

                    align="center",
                    justify="between",
                    padding="0.5em",
                    width="100%"
                ),

                width="100%",

                style={
                    "border_bottom": f"1px solid {rx.color('accent', 9)}",
                }
            ),
            item_preview(),

            width="100%"
        ),
        value=ProductsState.Pages.VIEW
    )

def table_row(item: ProductCatalog) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(
            rx.link(
                item.title,
                href=f"{routes.CATALOG_PRODUCTS_VIEW_ID}{item.id}"
            ),
            align="left"
        ),
        rx.table.cell(
            rx.text(item.category.title)
        ),
        rx.table.cell(
            rx.text(item.unit)
        ),
        rx.table.cell(
            rx.cond(
                item.divisible,
                rx.text("Так"),
                rx.text("Ні")
            )
        ),
        rx.table.cell(
            rx.cond(item.divisible,
                    rx.text(item.capacity),
                    rx.text("-")
                    )
        ),
    )

def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Назва", align="left", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Категорія", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Одиниця виміру", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Подільний", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Місткість", color=rx.color("accent", 2)),
            ),

            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(
                ListProductsState.items,
                table_row
            )
        ),

        variant="surface",
        width="100%"
    )

def table_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            rx.box(
                rx.hstack(
                    rx.heading("Каталог ТМЦ", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.PRODUCTS_CREATE),
                            rx.button(
                                "Додати",
                                variant="ghost",
                                size="3",
                                on_click=rx.redirect(routes.CATALOG_PRODUCTS_ADD)
                            ),                          
                        ),

                        spacing="6",
                    ),

                    align="center",
                    justify="between",
                    padding="0.5em",
                    width="100%"
                ),

                width="100%",

                style={
                    "border_bottom": f"1px solid {rx.color('accent', 9)}",
                }
            ),
            rx.hstack(
                rx.input(
                    value=ListProductsState.get_search_str,
                    on_change=ListProductsState.on_change_search_str
                ),
                rx.button("Пошук", on_click=ListProductsState.on_click_search),

                width="100%"
            ),
            rx.cond(ListProductsState.has_items,
                table(),
                rx.text("Записів немає")
            ),
            rx.hstack(
                rx.button("Назад", on_click=ListProductsState.current_page_decrement),
                rx.input(
                    value=ListProductsState.get_current_page,
                    on_change=ListProductsState.on_change_current_page,
                    type="number",
                    min="1",
                    max=ListProductsState.get_all_pages),
                rx.text("/"),
                rx.text(ListProductsState.get_all_pages),
                rx.button("Вперед", on_click=ListProductsState.current_page_increment),

                justify="center",

                width="100%"
            ),

            width="100%",
            height="100%",
        ),

        value=ProductsState.Pages.LIST
    )

def add_form() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text("*Назва", size="3", width="100%"),
            rx.input(id="title", required=True, size="3", value=AddProductsState.title, on_change=AddProductsState.on_change_title, width="100%"),
            rx.text("Опис", size="3", width="100%"),
            rx.text_area(id="description", size="3", width="100%", value=AddProductsState.description, on_change=AddProductsState.on_change_description),
            rx.text("*Категорія", size="3", width="100%"),
            category_select_row(AddProductsState),
            rx.text("Одиниця виміру", size="3", width="100%"),
            rx.input(id="unit", required=True, size="3", width="100%", list="units-datalist", value=AddProductsState.unit, on_change=AddProductsState.on_change_unit
            ),
            rx.el.datalist(
                rx.foreach(
                    AddProductsState.all_units_cache,
                    lambda unit: rx.el.option(value=unit)
                ),
                id="units-datalist"
            ),
            rx.text("Місткість", size="3", width="100%"),
            rx.input(id="capacity", required=True, size="3", width="100%", value=AddProductsState.capacity, on_change=AddProductsState.on_change_capacity, disabled=AddProductsState.uniq),
            rx.checkbox(
                text="Має серійний номер",
                id="uniq",
                size="3",
                checked=AddProductsState.uniq,
                on_change=AddProductsState.on_change_uniq
            ),
            rx.checkbox(
                text="Подільний",
                id="divisible",
                size="3",
                checked=AddProductsState.divisible,
                on_change=AddProductsState.on_change_divisible,
                disabled=AddProductsState.uniq
            ),

            spacing="3",
            width="100%"
        ),

        width="100%",
        height="100%",
    )

def add_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            rx.box(
                rx.hstack(
                    rx.button(
                        "Скасувати",
                        variant="ghost",
                        size="3",
                        on_click=rx.redirect(routes.CATALOG_PRODUCTS)
                    ),
                    rx.heading("Каталог ТМЦ/Додавання", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.PRODUCTS_CREATE),
                            rx.button(
                                "Зберегти",
                                variant="ghost",
                                size="3",
                                on_click=AddProductsState.add_one
                            ),                          
                        ),

                        spacing="6",
                    ),

                    align="center",
                    justify="between",
                    padding="0.5em",
                    width="100%"
                ),

                width="100%",

                style={
                    "border_bottom": f"1px solid {rx.color('accent', 9)}",
                }
            ),
            add_form(),

            width="100%"
        ),
        value=ProductsState.Pages.ADD
    )

def edit_form() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text("*Назва", size="3", width="100%"),
            rx.input(id="title", required=True, size="3", value=EditProductsState.title, on_change=EditProductsState.on_change_title, width="100%"),
            rx.text("Опис", size="3", width="100%"),
            rx.text_area(id="description", size="3", width="100%", value=EditProductsState.description, on_change=EditProductsState.on_change_description),
            rx.text("*Категорія", size="3", width="100%"),
            category_select_row(EditProductsState),
            rx.text("Одиниця виміру", size="3", width="100%"),
            rx.input(id="unit", required=True, size="3", width="100%", list="units-datalist", value=EditProductsState.unit, on_change=EditProductsState.on_change_unit),
            rx.el.datalist(
                rx.foreach(
                    EditProductsState.all_units_cache,
                    lambda unit: rx.el.option(value=unit)
                ),
                id="units-datalist"
            ),
            rx.text("Місткість", size="3", width="100%"),
            rx.input(id="capacity", required=True, size="3", width="100%", value=EditProductsState.capacity, on_change=EditProductsState.on_change_capacity, disabled=EditProductsState.uniq),
            rx.checkbox(
                "Має серійний номер",
                id="uniq",
                size="3",
                checked=EditProductsState.uniq,
                on_change=EditProductsState.on_change_uniq,
                disabled=True,
            ),
            rx.checkbox(
                "Подільний",
                id="divisible",
                size="3",
                checked=EditProductsState.divisible,
                on_change=EditProductsState.on_change_divisible,
                disabled=True,
            ),

            spacing="3",
            width="100%"
        ),

        width="100%",
        height="100%",
    )

def edit_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            rx.box(
                rx.hstack(
                    rx.button(
                        "Скасувати",
                        variant="ghost",
                        size="3",
                        on_click=rx.redirect(routes.CATALOG_PRODUCTS)
                    ),
                    rx.heading("Каталог ТМЦ/Редагування", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.PRODUCTS_EDIT),
                            rx.button(
                                "Зберегти",
                                variant="ghost",
                                size="3",
                                on_click=EditProductsState.edit_one
                            ),                          
                        ),

                        spacing="6",
                    ),

                    align="center",
                    justify="between",
                    padding="0.5em",
                    width="100%"
                ),

                width="100%",

                style={
                    "border_bottom": f"1px solid {rx.color('accent', 9)}",
                }
            ),
            edit_form(),

            width="100%"
        ),
        value=ProductsState.Pages.EDIT
    )

def index() -> rx.Component:
    return rx.tabs.root(
        rx.cond(AppState.get_user_actions.contains(ActionEnum.PRODUCTS_LIST),
            table_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.PRODUCTS_CREATE),
            add_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.PRODUCTS_EDIT),
            edit_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.PRODUCTS_VIEW),
            item_preview_tab_content()),

        value=ProductsState.current_page,

        orientation="horizontal",
        width="100%"
    )
