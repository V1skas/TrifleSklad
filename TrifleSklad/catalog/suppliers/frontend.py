import reflex as rx

from TrifleSklad import routes
from TrifleSklad.catalog.suppliers.backend import *
from TrifleSklad.models import Supplier

def item_preview(item: Tuple[int, Supplier]) -> rx.Component:
    return rx.vstack(
        rx.heading(item[1].title, size="7", width="100%"),
        rx.text(item[1].okpo, width="100%"),
        rx.text(item[1].description, is_optional=True, width="100%"),
        rx.text(item[1].address, is_optional=True, width="100%"),
        rx.text(item[1].email, is_optional=True, width="100%"),
        rx.text(item[1].contact_person, width="100%"),
        rx.text(item[1].contact_phone, width="100%"),
        rx.spacer(),
        rx.hstack(
            rx.button(
                "Редактировать",

                on_click=rx.redirect(f"{routes.CATALOG_SUPPLIERS_EDIT_ID}{item[1].id}")
            ),
            rx.spacer(),
            rx.button(
                "Удалить",

                color_scheme="red",
                on_click=SupplierState.delete_one
            ),

            width="100%",
        ),

        spacing="3",
        height="100%",
        width="100%"
    )

def item_preview_tab_content() -> rx.Component:
    return rx.tabs.content(
        item_preview(SupplierState.get_selected_item),

        value=SupplierState.Pages.VIEW
    )

def table_row(item: Tuple[int, Supplier]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            item[1].okpo,
            align="left"
        ),
        rx.table.row_header_cell(
            rx.link(
                item[1].title,
                href=f"{routes.CATALOG_SUPPLIERS_VIEW_ID}{item[1].id}"
            ),
            align="left"
        ),
        rx.table.cell(
            item[1].address,
            align="left"
        ),
        rx.table.cell(
            item[1].email,
            align="left"
        ),
        rx.table.cell(
            item[1].contact_person,
            align="left"
        ),
        rx.table.cell(
            item[1].contact_phone,
            align="left"
        )
    )

def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("ОКПО", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Название", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Адрес", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Email", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Контактное лицо", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Телефон", color=rx.color("accent", 2))
            ),

            background_color=rx.color("accent", 9)
        ),
        rx.table.body(
            rx.foreach(SupplierState.get_items, table_row),

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
            rx.hstack(
                rx.heading("Поставщики", size="6"),
                rx.spacer(),
                rx.button(
                    "Добавить",
                    on_click=rx.redirect(routes.CATALOG_SUPPLIERS_ADD)
                ),

                width="100%"
            ),
            rx.cond(SupplierState.has_items,
                table(),
                rx.text("Записей нет.")
            ),

            width="100%",
            height="100%",
        ),

        value=SupplierState.Pages.LIST,
    )

def add_form() -> rx.Component:
    return rx.card(
        rx.form(
            rx.vstack(
                rx.text("Название:", size="3", width="100%"),
                rx.input(
                    name="title",
                    #placeholder="Введите название поставщика",
                    required=True,
                    width="100%"
                ),
                rx.text("ОКПО:", size="3", width="100%"),
                rx.input(
                    name="okpo",
                    #placeholder="Введите ОКПО поставщика",
                    required=True,
                    width="100%"
                ),
                rx.text("Описание:", size="3", width="100%"),
                rx.text_area(
                    name="description",
                    #placeholder="Введите описание поставщика",
                    is_optional=True,
                    width="100%"
                ),
                rx.text("Адрес", size="3", width="100%"),
                rx.input(
                    name="address",
                    #placeholder="Введите адрес поставщика",
                    is_optional=True,
                    width="100%"
                ),
                rx.text("Email:", size="3", width="100%"),
                rx.input(
                    name="email",
                    #placeholder="Введите email поставщика",
                    is_optional=True,
                    width="100%"
                ),
                rx.text("Контактное лицо:", size="3", width="100%"),
                rx.input(
                    name="contact_person",
                    #placeholder="Введите контактное лицо поставщика",
                    width="100%"
                ),
                rx.text("Телефон:", size="3", width="100%"),
                rx.input(
                    name="contact_phone",
                    #placeholder="Введите телефон поставщика",
                    width="100%"
                ),

                rx.hstack(
                    rx.button(
                        "Отмена",
                        color_scheme="red",
                        type="reset",
                        on_click=rx.redirect(f"{routes.CATALOG_SUPPLIERS}")
                    ),
                    rx.button(
                        "Добавить",
                        type="submit",
                        color_scheme="green"
                    ),

                    justify="end",

                    width="100%"
                ),

                width="100%",
            ),

            on_submit=SupplierState.add_one,
            width="100%",
            height="100%"
        ),

        variant="surface"
    )

def edit_form(item: Tuple[int, Supplier]) -> rx.Component:
    return rx.card(
        rx.form(
            rx.vstack(
                rx.text("Название:", size="3", width="100%"),
                rx.input(
                    name="title",
                    default_value=item[1].title,
                    required=True,
                    width="100%"
                ),
                rx.text("ОКПО:", size="3", width="100%"),
                rx.input(
                    name="okpo",
                    default_value=item[1].okpo,
                    required=True,
                    width="100%"
                ),
                rx.text("Описание:", size="3", width="100%"),
                rx.text_area(
                    name="description",
                    default_value=item[1].description,
                    is_optional=True,
                    width="100%"
                ),
                rx.text("Адрес:", size="3", width="100%"),
                rx.input(
                    name="address",
                    default_value=item[1].address,
                    is_optional=True,
                    width="100%"
                ),
                rx.text("Email:", size="3", width="100%"),
                rx.input(
                    name="email",
                    default_value=item[1].email,
                    is_optional=True,
                    width="100%"
                ),
                rx.text("Контактное лицо:", size="3", width="100%"),
                rx.input(
                    name="contact_person",
                    default_value=item[1].contact_person,
                    width="100%"
                ),
                rx.text("Телефон:", size="3", width="100%"),
                rx.input(
                    name="contact_phone",
                    default_value=item[1].contact_phone,
                    width="100%"
                ),

                rx.hstack(
                    rx.button(
                        "Отмена",
                        color_scheme="red",
                        type="reset",
                        on_click=rx.redirect(f"{routes.CATALOG_SUPPLIERS_VIEW_ID}{item[1].id}")
                    ),
                    rx.button(
                        "Сохранить",
                        type="submit",
                        color_scheme="green"
                    ),

                    justify="end",

                    width="100%"
                ),

                width="100%",
            ),

            on_submit=SupplierState.edit_one,
            width="100%",
            height="100%"
        ),

        variant="surface"
    )

def add_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading("Добавление поставщика", size="7", width="100%", margin_bottom="0.5em"),
        add_form(),

        value=SupplierState.Pages.ADD
    )

def edit_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading("Редактирование поставщика", size="7", width="100%", margin_bottom="0.5em"),
        edit_form(SupplierState.get_selected_item),

        value=SupplierState.Pages.EDIT
    )

def index() -> rx.Component:
    return rx.tabs.root(
        list_tab_content(),
        add_tab_content(),
        edit_tab_content(),
        item_preview_tab_content(),

        value=SupplierState.current_page,

        height="100%",
        width="100%"
    )