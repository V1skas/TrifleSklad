import reflex as rx

from typing import Tuple

from TrifleSklad import routes
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.catalog.categories.backend import ViewCategoriesState, AddCategoriesState, EditCategoriesState, ListCategoriesState, CategoriesState, NONE

from TrifleSklad.models import ProductCategory

def item_preview() -> rx.Component:
    return rx.vstack(
        rx.heading(ViewCategoriesState.item.title, size="7", width="100%"),
        rx.hstack(rx.text("Опис:"), rx.text(ViewCategoriesState.item.description, is_optional=True), width="100%"),
        rx.cond(
            ViewCategoriesState.item.id_parent,
            rx.hstack(rx.text("Батьківська категорія:"), rx.text(ViewCategoriesState.parent_title), width="100%"),
        ),
        rx.cond(
            ViewCategoriesState.children.length() > 0,
            rx.vstack(
                rx.text("Підкатегорії:"),
                rx.foreach(ViewCategoriesState.children, lambda c: rx.text(f"— {c.title}")),
                align="start",
                width="100%",
            ),
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
            rx.cond(item.id_parent, f"— {item.title}", item.title),
            align="left",
            padding_left=rx.cond(item.id_parent, "2em", "1em"),
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

def parent_select(list_parent_categories, value, on_change) -> rx.Component:
    return rx.select.root(
        rx.select.trigger(
            placeholder="Без батьківської категорії",
            width="100%",
        ),
        rx.select.content(
            rx.select.item("— Без батьківської —", value=NONE),
            rx.foreach(
                list_parent_categories,
                lambda category: rx.select.item(category[1], value=category[0]),
            ),
            width="100%",
        ),
        value=value,
        on_change=on_change,
        size="3",
        width="100%",
    )

def add_form() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text("*Назва:"),
            rx.input(id="title", required=True, size="3", value=AddCategoriesState.item.title, on_change=AddCategoriesState.on_change_title),
            rx.text("Опис:"),
            rx.text_area(id="description", size="3", value=AddCategoriesState.item.description, on_change=AddCategoriesState.on_change_description),
            rx.text("Батьківська категорія:"),
            parent_select(AddCategoriesState.list_parent_categories, AddCategoriesState.parent_id, AddCategoriesState.on_change_parent),

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
            rx.text("Батьківська категорія:"),
            rx.cond(
                EditCategoriesState.can_set_parent,
                parent_select(EditCategoriesState.list_parent_categories, EditCategoriesState.parent_id, EditCategoriesState.on_change_parent),
                rx.text("Категорія має підкатегорії — батьківську призначити не можна", color=rx.color("gray", 10)),
            ),

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
