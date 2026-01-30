import reflex as rx
from typing import Tuple

from TrifleSklad import routes
from TrifleSklad.movement.write_off.backend import WriteOffState
from TrifleSklad.movement.products.frontend import index as products

from TrifleSklad.models import Movement


def item_preview(item: Tuple[int, Movement]) -> rx.Component:
    return rx.vstack(
        rx.heading(f"Списание №{item[1].id}", size="7", width="100%"),
        rx.hstack(
            rx.text("Дата:"),
            rx.text(item[1].date)
        ),
        rx.hstack(
            rx.text("Склад:"),
            rx.text(item[1].incoming_storage.title)
        ),
        rx.hstack(
            rx.text("Владелец:"),
            rx.text(item[1].incoming_owner.title)
        ),
        products(width="100%"),
        rx.hstack(
            rx.text("Статус:"),
            rx.text(WriteOffState.get_selected_movement_status)
        ),
        rx.hstack(
            rx.text("Комментарий:"),
            rx.text(item[1].comment)
        ),
        rx.spacer(),
        rx.hstack(
            #rx.button(
            #    "Редактировать",

            #    on_click=rx.redirect(f"{routes.MOVEMENT_ADMISSIONS_EDIT_ID}{item[1].id}")
            #),
            rx.spacer(),
            rx.cond(WriteOffState.current_is_canceled == False,
                    rx.button(
                        "Удалить",
                        color_scheme="red",

                        on_click=WriteOffState.delete_one
                    )),

            width="100%",
        ),

        spacing="3",

        height="100%",
        width="100%"
    )

def item_preview_tab_content() -> rx.Component:
    return rx.tabs.content(
        item_preview(WriteOffState.get_selected_item),

        value=WriteOffState.Pages.VIEW
    )

def table_row(item: Tuple[int, Movement]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item[1].id)),
        rx.table.row_header_cell(
            rx.link(
                item[1].date,
                href=f"{routes.MOVEMENT_WRITE_OFFS_VIEW_ID}{item[1].id}"
            ),

            align="left"
        ),
        rx.table.cell(rx.text(item[1].incoming_storage.title)),
        rx.table.cell(rx.text(item[1].incoming_owner.title)),
        rx.table.cell(rx.text(WriteOffState.get_movement_statuses[item[1].status]))
    )

def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("№", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Дата", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Склад", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Владелец", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Статус", color=rx.color("accent", 2)),
            ),

            background_color=rx.color("accent", 9)
        ),
        rx.table.body(
            rx.foreach(WriteOffState.get_items, table_row),

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
                rx.heading("Списания", size="6"),
                rx.spacer(),
                rx.button(
                    "Добавить",
                    on_click=rx.redirect(routes.MOVEMENT_WRITE_OFFS_ADD)
                ),

                width="100%"
            ),
            rx.cond(WriteOffState.has_items,
                table(),
                rx.text("Записей нет.")
            ),

            width="100%",
            height="100%",
        ),

        value=WriteOffState.Pages.LIST,
    )

def add_form() -> rx.Component:
    return rx.card(
        rx.form(
            rx.vstack(
                rx.text("Дата:"),
                rx.input(name="date", type="date", required=True, size="3", default_value=WriteOffState.current_date),
                rx.text("Склад:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Выберите из списка",
                        width="100%",
                    ),
                    rx.select.content(
                        rx.vstack(
                            rx.hstack(
                                rx.button(
                                    "Поиск",
                                    type="button",
                                    on_click=WriteOffState.on_click_search_name_incoming_storage
                                ),
                                rx.input(
                                    value=WriteOffState.search_name_incoming_storage,
                                    on_change=WriteOffState.on_change_search_name_incoming_storage,
                                    placeholder="Введите название для поиска",
                                    width="100%"
                                ),

                                width="100%"
                            ),

                            rx.foreach(
                                WriteOffState.list_storages,
                                lambda storage: rx.select.item(storage[0], value=storage[1], width="100%")
                            ),

                            width="100%",
                        ),

                        width="100%",
                    ),

                    name="id_incoming_storage",
                    required=True,
                    value=WriteOffState.id_incoming_storage,
                    on_change=WriteOffState.on_change_id_incoming_storage
                ),
                rx.text("Владелец:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Выберите из списка",
                        width="100%",
                    ),
                    rx.select.content(
                        rx.foreach(
                            WriteOffState.list_owners,
                            lambda owner: rx.select.item(owner[0], value=owner[1])
                        ),
                        width="100%",
                    ),

                    name="id_incoming_owner",
                    required=True,
                    value=WriteOffState.id_incoming_owner,
                    on_change=WriteOffState.on_change_id_incoming_owner
                ),
                products(width="100%"),
                rx.hstack(
                    rx.text("Статус:"),
                    rx.select(
                        WriteOffState.get_movement_statuses,

                        name="status",
                        placeholder="Выберите из списка",
                        required=True,
                        value=WriteOffState.status,
                        on_change=WriteOffState.on_change_status
                    ),
                ),
                rx.text("Комментарий:"),
                rx.text_area(name="comment"),

                rx.hstack(
                    rx.button("Отмена", type="reset", color_scheme="red", on_click=rx.redirect(routes.MOVEMENT_WRITE_OFFS)),
                    rx.button("Сохранить", color_scheme="green", type="submit"),

                    justify="end"
                ),

                align="stretch"
            ),

            on_submit=WriteOffState.add_one,
        ),

        height="100%",
        width="100%"
    )

def edit_form(item: Tuple[int, Movement]) -> rx.Component:
    return rx.card(
        rx.form(
            rx.vstack(
                rx.text("Дата:"),
                rx.input(id="date", required=True, type="date", size="3", default_value=item[1].date),
                rx.text("Склад:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Выберите из списка",
                        width="100%",
                    ),
                    rx.select.content(
                        rx.vstack(
                            rx.hstack(
                                rx.button(
                                    "Поиск",
                                    type="button",
                                    on_click=WriteOffState.on_click_search_name_incoming_storage
                                ),
                                rx.input(
                                    value=WriteOffState.search_name_incoming_storage,
                                    on_change=WriteOffState.on_change_search_name_incoming_storage,
                                    placeholder="Введите название для поиска",
                                    width="100%"
                                ),

                                width="100%"
                            ),

                            rx.foreach(
                                WriteOffState.list_storages,
                                lambda storage: rx.select.item(storage[0], value=storage[1], width="100%")
                            ),

                            width="100%",
                        ),

                        width="100%",
                    ),

                    id="id_incoming_storage",
                    required=True,
                    value=WriteOffState.id_incoming_storage,
                    on_change=WriteOffState.on_change_id_incoming_storage
                ),
                rx.text("Владелец:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Выберите из списка",
                        width="100%",
                    ),
                    rx.select.content(
                        rx.foreach(
                            WriteOffState.list_owners,
                            lambda owner: rx.select.item(owner[0], value=owner[1])
                        ),
                        width="100%",
                    ),

                    id="id_incoming_owner",
                    required=True,
                    value=WriteOffState.id_incoming_owner,
                    on_change=WriteOffState.on_change_id_incoming_owner
                ),
                products(width="100%"),
                rx.hstack(
                    rx.text("Статус:"),
                    rx.select(
                        WriteOffState.get_movement_statuses,

                        name="status",
                        placeholder="Выберите из списка",
                        required=True,
                        value=WriteOffState.status,
                        on_change=WriteOffState.on_change_status
                    ),
                ),
                rx.text("Комментарий:"),
                rx.text_area(id="comment", default_value=item[1].comment),

                rx.hstack(
                    rx.button("Отмена", type="reset", color_scheme="red", on_click=rx.redirect(f"{routes.MOVEMENT_WRITE_OFFS_VIEW_ID}{item[1].id}")),
                    rx.button("Сохранить", color_scheme="green", type="submit"),

                    justify="end"
                ),

                align="stretch"
            ),

            on_submit=WriteOffState.edit_one,
        ),

        height="100%",
        width="100%"
    )

def add_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading("Добавление списания", size="7", width="100%", margin_bottom="0.5em"),
        add_form(),

        value=WriteOffState.Pages.ADD
    )

def edit_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading("Редактирование списания", size="7", width="100%", margin_bottom="0.5em"),
        edit_form(WriteOffState.get_selected_item),

        value=WriteOffState.Pages.EDIT
    )

def index() -> rx.Component:
    return rx.tabs.root(
        list_tab_content(),
        add_tab_content(),
        edit_tab_content(),
        item_preview_tab_content(),

        value=WriteOffState.current_page,

        height="100%",
        width="100%"
    )