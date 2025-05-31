import reflex as rx

from TrifleSklad import routes
from TrifleSklad.catalog.storages.backend import *

def item_preview(item: Tuple[int, Storage]) -> rx.Component:
    return rx.vstack(
        rx.heading(item[1].title, size="7", width="100%"),
        rx.text(item[1].type, width="100%"),
        rx.text(item[1].description, is_optional=True, width="100%"),
        rx.text(item[1].address, width="100%"),
        rx.text(item[1].responsible.fio, width="100%"),
        rx.spacer(),
        rx.hstack(
            rx.button(
                "Редактировать",

                on_click=rx.redirect(f"{routes.CATALOG_STORAGES_EDIT_ID}{item[1].id}")
            ),
            rx.spacer(),
            rx.button(
                "Удалить",

                color_scheme="red",
                on_click=StorageState.delete_one
            ),
            width="100%",
        ),

        spasing="3",
        height="100%",
        width="100%",
    )

def item_preview_tab_content() -> rx.Component:
    return rx.tabs.content(
        item_preview(StorageState.get_selected_item),
        value=StorageState.Pages.VIEW
    )

def table_row(item: Tuple[int, Storage]) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(
            rx.link(
                item[1].title,
                href=f"{routes.CATALOG_STORAGES_VIEW_ID}{item[1].id}"
            ),

            align="left"
        ),
        rx.table.cell(item[1].type),
        rx.table.cell(item[1].address),
        rx.table.cell(item[1].responsible.fio),
    )

def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Название", align="left", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Тип", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Адрес", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Ответственный", color=rx.color("accent", 2)),
            ),

            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(
                StorageState.get_items,
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
                rx.heading("Хранилища", size="6"),
                rx.spacer(),
                rx.button(
                    "Добавить",

                    on_click=rx.redirect(routes.CATALOG_STORAGES_ADD)
                ),

                width="100%"
            ),
            rx.cond(
                StorageState.has_items,
                table(),
                rx.text("Записей нет.")
            ),

            spacing="3",
            width="100%"
        ),

        value=StorageState.Pages.LIST
    )

def add_form() -> rx.Component:
    return rx.card(
        rx.form(
            rx.vstack(
                rx.text("Название", size="4", width="100%"),
                rx.input(
                    name="title",
                    required=True,
                    width="100%"
                ),
                rx.text("Тип", size="4", width="100%"),
                rx.input(
                    name="type",
                    required=True,
                    width="100%"
                ),
                rx.text("Описание", size="4", width="100%"),
                rx.text_area(
                    name="description",
                    is_optional=True,
                    width="100%"
                ),
                rx.text("Адрес", size="4", width="100%"),
                rx.input(
                    name="address",
                    required=True,
                    width="100%"
                ),
                rx.text("Ответственный", size="4", width="100%"),
                rx.select(
                    [worker.fio for worker in WorkerDAO.get_all()],

                    name="id_responsible",
                    required=True,
                    placeholder="Выберите ответственного",
                    size="3",
                    width="100%"
                ),

                rx.hstack(
                    rx.button(
                        "Отмена",
                        color_scheme="red",
                        on_click=rx.redirect(routes.CATALOG_STORAGES)
                    ),
                    rx.button(
                        "Добавить",
                        color_scheme="green",
                        type="submit"
                    ),

                    justify="end",

                    width="100%"
                ),

                spacing="3",
                width="100%"
            ),

            on_submit=StorageState.add_one,
            width="100%"
        ),
        
        width="100%",
        height="100%",
    )

def edit_form(item: Tuple[int, Storage]) -> rx.Component:
    return rx.card(
        rx.form(
            rx.vstack(
                rx.text("Название", size="4", width="100%"),
                rx.input(
                    name="title",
                    required=True,
                    default_value=item[1].title,
                    width="100%"
                ),
                rx.text("Тип", size="4", width="100%"),
                rx.input(
                    name="type",
                    required=True,
                    default_value=item[1].type,
                    width="100%"
                ),
                rx.text("Описание", size="4", width="100%"),
                rx.text_area(
                    name="description",
                    is_optional=True,
                    default_value=item[1].description,
                    width="100%"
                ),
                rx.text("Адрес", size="4", width="100%"),
                rx.input(
                    name="address",
                    required=True,
                    default_value=item[1].address,
                    width="100%"
                ),
                rx.text("Ответственный", size="4", width="100%"),
                rx.select(
                    [worker.fio for worker in WorkerDAO.get_all()],
                    
                    name="id_responsible",
                    required=True,
                    placeholder="Выберите ответственного",
                    default_value=item[1].responsible.fio,
                    size="3",
                    width="100%"
                ),

                rx.hstack(
                    rx.button(
                        "Отмена",
                        color_scheme="red",
                        on_click=rx.redirect(routes.CATALOG_STORAGES)
                    ),
                    rx.button(
                        "Сохранить",
                        color_scheme="green",
                        type="submit"
                    ),

                    justify="end",

                    width="100%"
                ),

                spacing="3",
                width="100%"
            ),

            on_submit=StorageState.edit_one,
            width="100%"
        ),

        width="100%",
        height="100%",
    )

def add_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading("Добавление хранилища", size="7", width="100%", margin_bottom="0.5em"),
        add_form(),
        value=StorageState.Pages.ADD
    )

def edit_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading("Редактирование хранилища", size="7", width="100%", margin_bottom="0.5em"),
        edit_form(StorageState.get_selected_item),
        value=StorageState.Pages.EDIT
    )

def index() -> rx.Component:
    return rx.tabs.root(
        table_tab_content(),
        item_preview_tab_content(),
        add_tab_content(),
        edit_tab_content(),

        value=StorageState.current_page,

        orientation="horizontal",
        width="100%"
    )