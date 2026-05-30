import reflex as rx

from TrifleSklad import routes
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum

from TrifleSklad.catalog.nds_rates.backend import (
    AddNdsRateState,
    EditNdsRateState,
    ListNdsRateState,
    NdsRateState,
    ViewNdsRateState,
)
from TrifleSklad.models import NDSRate


def item_preview() -> rx.Component:
    return rx.vstack(
        rx.heading(ViewNdsRateState.title, size="7", width="100%"),
        rx.text(f"Ставка: {ViewNdsRateState.rate}%", width="100%"),
        rx.text(ViewNdsRateState.description, is_optional=True, width="100%"),

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
                        on_click=rx.redirect(routes.CATALOG_NDS_RATES)
                    ),
                    rx.heading("Ставки ПДВ/Перегляд", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.NDS_RATES_DELETE),
                            rx.button(
                                "Видалити",
                                color_scheme="red",
                                variant="ghost",
                                size="3",
                                on_click=NdsRateState.delete_one(ViewNdsRateState.item.id)
                            ),
                        ),
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.NDS_RATES_EDIT),
                            rx.button(
                                "Редагувати",
                                variant="ghost",
                                size="3",
                                on_click=rx.redirect(f"{routes.CATALOG_NDS_RATES_EDIT_ID}{ViewNdsRateState.item.id}")
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

        value=NdsRateState.Pages.VIEW
    )


def table_row(item: NDSRate) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(
            rx.link(
                item.title,
                href=f"{routes.CATALOG_NDS_RATES_VIEW_ID}{item.id}"
            ),

            align="left"
        ),
        rx.table.cell(item.rate, align="left"),
    )


def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Назва", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Ставка, %", color=rx.color("accent", 2)),
            ),

            background_color=rx.color("accent", 9)
        ),
        rx.table.body(
            rx.foreach(ListNdsRateState.items, table_row),

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
                    rx.heading("Ставки ПДВ", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.NDS_RATES_CREATE),
                            rx.button(
                                "Додати",
                                variant="ghost",
                                size="3",
                                on_click=rx.redirect(routes.CATALOG_NDS_RATES_ADD)
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
            rx.cond(ListNdsRateState.has_items,
                table(),
                rx.text("Записів немає")
            ),

            width="100%",
            height="100%",
        ),

        value=NdsRateState.Pages.LIST,
    )


def add_form() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text("*Назва:"),
            rx.input(id="title", required=True, size="3", value=AddNdsRateState.title, on_change=AddNdsRateState.on_change_title),
            rx.text("*Ставка, %:"),
            rx.input(id="rate", required=True, size="3", type="number", value=AddNdsRateState.rate, on_change=AddNdsRateState.on_change_rate),
            rx.text("Опис:"),
            rx.text_area(id="description", size="3", value=AddNdsRateState.description, on_change=AddNdsRateState.on_change_description),

            align="stretch"
        ),

        height="100%",
        width="100%"
    )


def edit_form() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text("*Назва:"),
            rx.input(id="title", value=EditNdsRateState.title, required=True, size="3", on_change=EditNdsRateState.on_change_title),
            rx.text("*Ставка, %:"),
            rx.input(id="rate", value=EditNdsRateState.rate, required=True, size="3", type="number", on_change=EditNdsRateState.on_change_rate),
            rx.text("Опис:"),
            rx.text_area(id="description", value=EditNdsRateState.description, size="3", is_optional=True, on_change=EditNdsRateState.on_change_description),

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
                        on_click=rx.redirect(routes.CATALOG_NDS_RATES)
                    ),
                    rx.heading("Ставки ПДВ/Додавання", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.NDS_RATES_CREATE),
                            rx.button(
                                "Зберегти",
                                variant="ghost",
                                size="3",
                                on_click=AddNdsRateState.add_one
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

        value=NdsRateState.Pages.ADD
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
                        on_click=rx.redirect(routes.CATALOG_NDS_RATES)
                    ),
                    rx.heading("Ставки ПДВ/Редагування", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.NDS_RATES_EDIT),
                            rx.button(
                                "Зберегти",
                                variant="ghost",
                                size="3",
                                on_click=EditNdsRateState.edit_one
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

        value=NdsRateState.Pages.EDIT
    )


def index() -> rx.Component:
    return rx.tabs.root(
        rx.cond(AppState.get_user_actions.contains(ActionEnum.NDS_RATES_LIST),
            list_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.NDS_RATES_CREATE),
            add_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.NDS_RATES_EDIT),
            edit_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.NDS_RATES_VIEW),
            item_preview_tab_content()),

        value=NdsRateState.current_page,

        height="100%",
        width="100%"
    )
