import reflex as rx
from typing import Tuple

from TrifleSklad import routes
from TrifleSklad.movement.movements.backend import MovementsState
from TrifleSklad.movement.products.frontend import index as products

from TrifleSklad.models import Movement


def item_preview(item: Tuple[int, Movement]) -> rx.Component:
    return rx.vstack(
        rx.heading(f"Перемещение №{item[1].id}", size="7", width="100%"),
        rx.hstack(
            rx.text("Дата:"),
            rx.text(item[1].date)
        ),
        rx.hstack(
            rx.text("Склад отправки:"),
            rx.text(item[1].incoming_storage.title)
        ),
        rx.hstack(
            rx.text("Владелец отправки:"),
            rx.text(item[1].incoming_owner.title)
        ),
        rx.hstack(
            rx.text("Склад назначения:"),
            rx.text(item[1].destination_storage.title)
        ),
        rx.hstack(
            rx.text("Владелец назначения:"),
            rx.text(item[1].destination_owner.title)
        ),
        products(width="100%"),
        rx.hstack(
            rx.text("Статус:"),
            rx.text(MovementsState.get_selected_movement_status)
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
            rx.cond(MovementsState.current_is_canceled == False,
                    rx.button(
                        "Удалить",
                        color_scheme="red",

                        on_click=MovementsState.delete_one
                    )),

            width="100%",
        ),

        spacing="3",

        height="100%",
        width="100%"
    )

def item_preview_tab_content() -> rx.Component:
    return rx.tabs.content(
        item_preview(MovementsState.get_selected_item),

        value=MovementsState.Pages.VIEW
    )

def table_row(item: Tuple[int, Movement]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item[1].id)),
        rx.table.row_header_cell(
            rx.link(
                item[1].date,
                href=f"{routes.MOVEMENT_MOVEMENTS_VIEW_ID}{item[1].id}"
            ),

            align="left"
        ),
        rx.table.cell(rx.text(item[1].incoming_storage.title)),
        rx.table.cell(rx.text(item[1].incoming_owner.title)),
        rx.table.cell(rx.text(item[1].destination_storage.title)),
        rx.table.cell(rx.text(item[1].destination_owner.title)),
        rx.table.cell(rx.text(MovementsState.get_movement_statuses[item[1].status]))
    )

def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("№", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Дата", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Склад отправления", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Владелец отправления", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Склад назначения", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Владелец назначения", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Статус", color=rx.color("accent", 2)),
            ),

            background_color=rx.color("accent", 9)
        ),
        rx.table.body(
            rx.foreach(MovementsState.get_items, table_row),

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
                rx.heading("Перемещения", size="6"),
                rx.spacer(),
                rx.button(
                    "Добавить",
                    on_click=rx.redirect(routes.MOVEMENT_MOVEMENTS_ADD)
                ),

                width="100%"
            ),
            rx.cond(MovementsState.has_items,
                table(),
                rx.text("Записей нет.")
            ),

            width="100%",
            height="100%",
        ),

        value=MovementsState.Pages.LIST,
    )

def add_form() -> rx.Component:
    return rx.card(
        rx.form(
            rx.vstack(
                rx.text("Дата:"),
                rx.input(name="date", type="date", required=True, size="3", default_value=MovementsState.current_date),
                rx.text("Склад отправитель:"),
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
                                    on_click=MovementsState.on_click_search_name_incoming_storage
                                ),
                                rx.input(
                                    value=MovementsState.search_name_incoming_storage,
                                    on_change=MovementsState.on_change_search_name_incoming_storage,
                                    placeholder="Введите название для поиска",
                                    width="100%"
                                ),

                                width="100%"
                            ),

                            rx.foreach(
                                MovementsState.filtered_incoming_storages,
                                lambda storage: rx.select.item(storage[0], value=storage[1], width="100%")
                            ),

                            width="100%",
                        ),

                        width="100%",
                    ),

                    name="id_incoming_storage",
                    required=True,
                    value=MovementsState.id_incoming_storage,
                    on_change=MovementsState.on_change_id_incoming_storage
                ),
                rx.text("Владелец отправитель:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Выберите из списка",
                        width="100%",
                    ),
                    rx.select.content(
                        rx.foreach(
                            MovementsState.list_owners,
                            lambda owner: rx.select.item(owner[0], value=owner[1])
                        ),
                        width="100%",
                    ),

                    name="id_incoming_owner",
                    required=True,
                    value=MovementsState.id_incoming_owner,
                    on_change=MovementsState.on_change_id_incoming_owner
                ),
                rx.text("Склад получатель:"),
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
                                    on_click=MovementsState.on_click_search_name_destination_storage
                                ),
                                rx.input(
                                    value=MovementsState.search_name_destination_storage,
                                    on_change=MovementsState.on_change_search_name_destination_storage,
                                    placeholder="Введите название для поиска",
                                    width="100%"
                                ),

                                width="100%"
                            ),

                            rx.foreach(
                                MovementsState.filtered_destination_storages,
                                lambda storage: rx.select.item(storage[0], value=storage[1], width="100%")
                            ),

                            width="100%",
                        ),

                        width="100%",
                    ),

                    name="id_destination_storage",
                    required=True,
                    value=MovementsState.id_destination_storage,
                    on_change=MovementsState.on_change_id_destination_storage
                ),
                rx.text("Владелец получатель:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Выберите из списка",
                        width="100%",
                    ),
                    rx.select.content(
                        rx.foreach(
                            MovementsState.list_owners,
                            lambda owner: rx.select.item(owner[0], value=owner[1])
                        ),
                        width="100%",
                    ),

                    name="id_destination_owner",
                    required=True,
                    value=MovementsState.id_destination_owner,
                    on_change=MovementsState.on_change_id_destination_owner
                ),
                products(width="100%"),
                rx.hstack(
                    rx.text("Статус:"),
                    rx.select(
                        MovementsState.get_movement_statuses,

                        name="status",
                        placeholder="Выберите из списка",
                        required=True,
                        value=MovementsState.status,
                        on_change=MovementsState.on_change_status
                    ),
                ),
                rx.text("Комментарий:"),
                rx.text_area(name="comment"),

                rx.hstack(
                    rx.button("Отмена", type="reset", color_scheme="red", on_click=rx.redirect(routes.MOVEMENT_MOVEMENTS)),
                    rx.button("Сохранить", color_scheme="green", type="submit"),

                    justify="end"
                ),

                align="stretch"
            ),

            on_submit=MovementsState.add_one,
        ),

        height="100%",
        width="100%"
    )

def add_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading("Добавление перемещения", size="7", width="100%", margin_bottom="0.5em"),
        add_form(),

        value=MovementsState.Pages.ADD
    )

def index() -> rx.Component:
    return rx.tabs.root(
        list_tab_content(),
        item_preview_tab_content(),
        add_tab_content(),

        value=MovementsState.current_page,

        height="100%",
        width="100%"
    )