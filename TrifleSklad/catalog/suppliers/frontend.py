import reflex as rx

from TrifleSklad import routes
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum

from TrifleSklad.catalog.suppliers.backend import ViewSupplierState, AddSupplierState, EditSupplierState, ListSupplierState, SupplierState
from TrifleSklad.models import Supplier

def item_preview() -> rx.Component:
    return rx.vstack(
        rx.heading(ViewSupplierState.title, size="7", width="100%"),
        rx.hstack(rx.text("ЄДРПОУ:"), rx.text(ViewSupplierState.edrpou), width="100%"),
        rx.hstack(rx.text("Опис:"), rx.text(ViewSupplierState.description, is_optional=True), width="100%"),
        rx.hstack(rx.text("Адреса:"), rx.text(ViewSupplierState.address, is_optional=True), width="100%"),
        rx.hstack(rx.text("Ел. пошта:"), rx.text(ViewSupplierState.email, is_optional=True), width="100%"),
        rx.hstack(rx.text("Контактна особа:"), rx.text(ViewSupplierState.contact_person), width="100%"),
        rx.hstack(rx.text("Контактний телефон:"), rx.text(ViewSupplierState.contact_phone), width="100%"),

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
                        on_click=rx.redirect(routes.CATALOG_SUPPLIERS)
                    ),
                    rx.heading("Постачальники/Перегляд", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.SUPPLIERS_DELETE),
                            rx.button(
                                "Видалити",
                                color_scheme="red",
                                variant="ghost",
                                size="3",
                                on_click=SupplierState.delete_one(ViewSupplierState.item.id)
                            ),                            
                        ),
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.SUPPLIERS_EDIT),
                            rx.button(
                                "Редагувати",
                                variant="ghost",
                                size="3",
                                on_click=rx.redirect(f"{routes.CATALOG_SUPPLIERS_EDIT_ID}{ViewSupplierState.item.id}")
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

        value=SupplierState.Pages.VIEW
    )

def table_row(item: Supplier) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            item.edrpou,
            align="left"
        ),
        rx.table.row_header_cell(
            item.title,
            align="left"
        ),
        rx.table.cell(
            item.address,
            align="left"
        ),
        rx.table.cell(
            item.email,
            align="left"
        ),
        rx.table.cell(
            item.contact_person,
            align="left"
        ),
        rx.table.cell(
            item.contact_phone,
            align="left"
        ),
        on_click=rx.redirect(f"{routes.CATALOG_SUPPLIERS_VIEW_ID}{item.id}"),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )

def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("ЄДРПОУ", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Назва", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Адреса", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Email", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Контактне лице", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Телефон", color=rx.color("accent", 2))
            ),

            background_color=rx.color("accent", 9)
        ),
        rx.table.body(
            rx.foreach(ListSupplierState.filtered_items, table_row),

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
                    rx.heading("Постачальники", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.SUPPLIERS_CREATE),
                            rx.button(
                                "Додати",
                                variant="ghost",
                                size="3",
                                on_click=rx.redirect(routes.CATALOG_SUPPLIERS_ADD)
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
            rx.input(
                rx.input.slot(rx.icon("search")),
                placeholder="Пошук за назвою",
                value=ListSupplierState.filter_title,
                on_change=ListSupplierState.on_change_filter_title,
                width="100%",
            ),
            rx.cond(ListSupplierState.has_items,
                table(),
                rx.text("Записів немає")
            ),

            width="100%",
            height="100%",
        ),

        value=SupplierState.Pages.LIST,
    )

def add_form() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text("*Назва:", size="3", width="100%"),
            rx.input(
                name="title",
                value=AddSupplierState.title,
                on_change=AddSupplierState.on_change_title,
                required=True,
                width="100%"
            ),
            rx.text("ЄДРПОУ:", size="3", width="100%"),
            rx.input(
                name="edrpou",
                value=AddSupplierState.edrpou,
                on_change=AddSupplierState.on_change_edrpou,
                required=True,
                width="100%"
            ),
            rx.text("Опис:", size="3", width="100%"),
            rx.text_area(
                name="description",
                value=AddSupplierState.description,
                on_change=AddSupplierState.on_change_description,
                is_optional=True,
                width="100%"
            ),
            rx.text("Адреса", size="3", width="100%"),
            rx.input(
                name="address",
                value=AddSupplierState.address,
                on_change=AddSupplierState.on_change_address,
                is_optional=True,
                width="100%"
            ),
            rx.text("Email:", size="3", width="100%"),
            rx.input(
                name="email",
                value=AddSupplierState.email,
                on_change=AddSupplierState.on_change_email,
                is_optional=True,
                width="100%"
            ),
            rx.text("Контактне лице:", size="3", width="100%"),
            rx.input(
                name="contact_person",
                value=AddSupplierState.contact_person,
                on_change=AddSupplierState.on_change_contact_person,
                width="100%"
            ),
            rx.text("Телефон:", size="3", width="100%"),
            rx.input(
                name="contact_phone",
                value=AddSupplierState.contact_phone,
                on_change=AddSupplierState.on_change_contact_phone,
                width="100%"
            ),

            width="100%",
        ),

        variant="surface",
        width="100%"
    )

def edit_form() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text("*Назва:", size="3", width="100%"),
            rx.input(
                name="title",
                value=EditSupplierState.title,
                on_change=EditSupplierState.on_change_title,
                required=True,
                width="100%"
            ),
            rx.text("ЄДРПОУ:", size="3", width="100%"),
            rx.input(
                name="edrpou",
                value=EditSupplierState.edrpou,
                on_change=EditSupplierState.on_change_edrpou,
                required=True,
                width="100%"
            ),
            rx.text("Опис:", size="3", width="100%"),
            rx.text_area(
                name="description",
                value=EditSupplierState.description,
                on_change=EditSupplierState.on_change_description,
                is_optional=True,
                width="100%"
            ),
            rx.text("Адреса:", size="3", width="100%"),
            rx.input(
                name="address",
                value=EditSupplierState.address,
                on_change=EditSupplierState.on_change_address,
                is_optional=True,
                width="100%"
            ),
            rx.text("Email:", size="3", width="100%"),
            rx.input(
                name="email",
                value=EditSupplierState.email,
                on_change=EditSupplierState.on_change_email,
                is_optional=True,
                width="100%"
            ),
            rx.text("Контактне лице:", size="3", width="100%"),
            rx.input(
                name="contact_person",
                value=EditSupplierState.contact_person,
                on_change=EditSupplierState.on_change_contact_person,
                width="100%"
            ),
            rx.text("Телефон:", size="3", width="100%"),
            rx.input(
                name="contact_phone",
                value=EditSupplierState.contact_phone,
                on_change=EditSupplierState.on_change_contact_phone,
                width="100%"
            ),

            width="100%",
        ),

        variant="surface",
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
                        on_click=rx.redirect(routes.CATALOG_SUPPLIERS)
                    ),
                    rx.heading("Постачальники/Додавання", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.SUPPLIERS_CREATE),
                            rx.button(
                                "Зберегти",
                                variant="ghost",
                                size="3",
                                on_click=AddSupplierState.add_one
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

        value=SupplierState.Pages.ADD
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
                        on_click=rx.redirect(routes.CATALOG_SUPPLIERS)
                    ),
                    rx.heading("Постачальники/Редагування", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.SUPPLIERS_EDIT),
                            rx.button(
                                "Зберегти",
                                variant="ghost",
                                size="3",
                                on_click=EditSupplierState.edit_one
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

        value=SupplierState.Pages.EDIT
    )

def index() -> rx.Component:
    return rx.tabs.root(
        rx.cond(AppState.get_user_actions.contains(ActionEnum.SUPPLIERS_LIST),
            list_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.SUPPLIERS_CREATE),
            add_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.SUPPLIERS_EDIT),
            edit_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.SUPPLIERS_VIEW),
            item_preview_tab_content()),

        value=SupplierState.current_page,

        height="100%",
        width="100%"
    )