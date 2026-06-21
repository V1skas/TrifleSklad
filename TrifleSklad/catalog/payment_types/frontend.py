import reflex as rx

from TrifleSklad import routes
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum

from TrifleSklad.catalog.payment_types.backend import AddPaymentTypeState, EditPaymentTypeState, ListPaymentTypeState, PaymentTypeState, ViewPaymentTypeState
from TrifleSklad.models import PaymentType

def item_preview() -> rx.Component:
    return rx.vstack(
        rx.heading(ViewPaymentTypeState.title, size="7", width="100%"),
        rx.hstack(rx.text("Опис:"), rx.text(ViewPaymentTypeState.description, is_optional=True), width="100%"),
        rx.hstack(
            rx.text("За замовчуванням для рухів:"),
            rx.text(rx.cond(ViewPaymentTypeState.is_default, "Так", "Ні")),
            width="100%",
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
                        on_click=rx.redirect(routes.CATALOG_PAYMENT_TYPES)
                    ),
                    rx.heading("Типи оплат/Перегляд", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.PAYMENT_TYPE_DELETE),
                            rx.button(
                                "Видалити",
                                color_scheme="red",
                                variant="ghost",
                                size="3",
                                on_click=PaymentTypeState.delete_one(ViewPaymentTypeState.item.id)
                            ),                            
                        ),
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.PAYMENT_TYPE_EDIT),
                            rx.button(
                                "Редагувати",
                                variant="ghost",
                                size="3",
                                on_click=rx.redirect(f"{routes.CATALOG_PAYMENT_TYPES_EDIT_ID}{ViewPaymentTypeState.item.id}")
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

        value=PaymentTypeState.Pages.VIEW
    )

def table_row(item: PaymentType) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(
            item.title,
            align="left"
        ),
        on_click=rx.redirect(f"{routes.CATALOG_PAYMENT_TYPES_VIEW_ID}{item.id}"),
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
            rx.foreach(ListPaymentTypeState.items, table_row),

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
                    rx.heading("Типи оплат", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.PAYMENT_TYPE_CREATE),
                            rx.button(
                                "Додати",
                                variant="ghost",
                                size="3",
                                on_click=rx.redirect(routes.CATALOG_PAYMENT_TYPES_ADD)
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
            rx.cond(ListPaymentTypeState.has_items,
                table(),
                rx.text("Записів немає")
            ),

            width="100%",
            height="100%",
        ),

        value=PaymentTypeState.Pages.LIST,
    )

def add_form() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text("*Назва:"),
            rx.input(id="title", required=True, size="3", value=AddPaymentTypeState.title, on_change=AddPaymentTypeState.on_change_title),
            rx.text("Опис:"),
            rx.text_area(id="description", size="3", value=AddPaymentTypeState.description, on_change=AddPaymentTypeState.on_change_description),
            rx.hstack(
                rx.switch(checked=AddPaymentTypeState.is_default, on_change=AddPaymentTypeState.on_change_is_default),
                rx.text("За замовчуванням для рухів"),
                align="center", spacing="2",
            ),

            align="stretch"
        ),

        height="100%",
        width="100%"
    )

def edit_form() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text("*Назва:"),
            rx.input(id="title", value=EditPaymentTypeState.title, required=True, size="3", on_change=EditPaymentTypeState.on_change_title),
            rx.text("Опис:"),
            rx.text_area(id="description", value=EditPaymentTypeState.description, size="3", is_optional=True, on_change=EditPaymentTypeState.on_change_description),
            rx.hstack(
                rx.switch(checked=EditPaymentTypeState.is_default, on_change=EditPaymentTypeState.on_change_is_default),
                rx.text("За замовчуванням для рухів"),
                align="center", spacing="2",
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
                        on_click=rx.redirect(routes.CATALOG_PAYMENT_TYPES)
                    ),
                    rx.heading("Типи оплат/Додавання", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.PAYMENT_TYPE_CREATE),
                            rx.button(
                                "Зберегти",
                                variant="ghost",
                                size="3",
                                on_click=AddPaymentTypeState.add_one
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

        value=PaymentTypeState.Pages.ADD
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
                        on_click=rx.redirect(routes.CATALOG_PAYMENT_TYPES)
                    ),
                    rx.heading("Типи оплат/Редагування", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.PAYMENT_TYPE_EDIT),
                            rx.button(
                                "Зберегти",
                                variant="ghost",
                                size="3",
                                on_click=EditPaymentTypeState.edit_one
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

        value=PaymentTypeState.Pages.EDIT
    )

def index() -> rx.Component:
    return rx.tabs.root(
        rx.cond(AppState.get_user_actions.contains(ActionEnum.PAYMENT_TYPE_LIST),
            list_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.PAYMENT_TYPE_CREATE),
            add_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.PAYMENT_TYPE_EDIT),
            edit_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.PAYMENT_TYPE_VIEW),
            item_preview_tab_content()),

        value=PaymentTypeState.current_page,

        height="100%",
        width="100%"
    )
