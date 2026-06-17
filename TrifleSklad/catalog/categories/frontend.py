import reflex as rx

from typing import Tuple

from TrifleSklad import routes
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.catalog.categories.backend import ViewCategoriesState, AddCategoriesState, EditCategoriesState, ListCategoriesState, CategoriesState

from TrifleSklad.models import ProductCategory

def item_preview() -> rx.Component:
    return rx.vstack(
        rx.heading(ViewCategoriesState.item.title, size="7", width="100%"),
        rx.hstack(rx.text("Опис:"), rx.text(ViewCategoriesState.item.description, is_optional=True), width="100%"),

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
                        on_click=rx.redirect(routes.CATALOG_CATEGORIES)
                    ),
                    rx.heading("Категорії ТМЦ/Перегляд", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.CATEGORIES_DELETE),
                            rx.button(
                                "Видалити",
                                color_scheme="red",
                                variant="ghost",
                                size="3",
                                on_click=CategoriesState.delete_one(ViewCategoriesState.item.id)
                            ),                            
                        ),
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.CATEGORIES_EDIT),
                            rx.button(
                                "Редагувати",
                                variant="ghost",
                                size="3",
                                on_click=rx.redirect(f"{routes.CATALOG_CATEGORIES_EDIT_ID}{ViewCategoriesState.item.id}")
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

        value=CategoriesState.Pages.VIEW
    )

def table_row(item: ProductCategory) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(
            item.title,
            align="left"
        ),
        on_click=rx.redirect(f"{routes.CATALOG_CATEGORIES_VIEW_ID}{item.id}"),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )

def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Назва", color=rx.color("accent", 2)),
            ),

            background_color=rx.color("accent", 9)
        ),
        rx.table.body(
            rx.foreach(ListCategoriesState.items, table_row),

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
            rx.box(
                rx.hstack(
                    rx.heading("Категорії ТМЦ", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.CATEGORIES_CREATE),
                            rx.button(
                                "Додати",
                                variant="ghost",
                                size="3",
                                on_click=rx.redirect(routes.CATALOG_CATEGORIES_ADD)
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
            rx.cond(ListCategoriesState.has_items,
                table(),
                rx.text("Записів немає")
            ),

            width="100%",
            height="100%",
        ),

        value=CategoriesState.Pages.LIST,
    )

def add_form() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text("*Назва:"),
            rx.input(id="title", required=True, size="3", value=AddCategoriesState.item.title, on_change=AddCategoriesState.on_change_title),
            rx.text("Опис:"),
            rx.text_area(id="description", size="3", value=AddCategoriesState.item.description, on_change=AddCategoriesState.on_change_description),

            align="stretch"
        ),

        height="100%",
        width="100%"
    )

def edit_form() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text("*Назва:"),
            rx.input(id="title", required=True, size="3", value=EditCategoriesState.item.title, on_change=EditCategoriesState.on_change_title),
            rx.text("Опис:"),
            rx.text_area(id="description", size="3", is_optional=True, value=EditCategoriesState.item.description, on_change=EditCategoriesState.on_change_description),

            align="stretch"
        ),

        height="100%",
        width="100%"
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
                        on_click=rx.redirect(routes.CATALOG_CATEGORIES)
                    ),
                    rx.heading("Категорії ТМЦ/Додавання", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.CATEGORIES_CREATE),
                            rx.button(
                                "Зберегти",
                                variant="ghost",
                                size="3",
                                on_click=AddCategoriesState.add_one
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

        value=CategoriesState.Pages.ADD
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
                        on_click=rx.redirect(routes.CATALOG_CATEGORIES)
                    ),
                    rx.heading("Категорії ТМЦ/Редагування", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.CATEGORIES_EDIT),
                            rx.button(
                                "Зберегти",
                                variant="ghost",
                                size="3",
                                on_click=EditCategoriesState.edit_one
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

        value=CategoriesState.Pages.EDIT
    )

def index() -> rx.Component:
    return rx.tabs.root(
        rx.cond(AppState.get_user_actions.contains(ActionEnum.CATEGORIES_LIST),
            list_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.CATEGORIES_CREATE),
            add_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.CATEGORIES_EDIT),
            edit_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.CATEGORIES_VIEW),
            item_preview_tab_content()),

        value=CategoriesState.current_page,

        height="100%",
        width="100%"
    )
