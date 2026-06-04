import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.movement.movements.backend import (
    AddMovementsState,
    EditMovementsState,
    ListMovementsState,
    MovementsState,
    ViewMovementsState,
)
from TrifleSklad.movement.products.frontend import index as products

from TrifleSklad.models import Movement
from TrifleSklad.state import AppState


def cancel_conflict_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Скасування неможливе"),
            rx.dialog.description(
                "Товар із цього переміщення бере участь у наведених нижче рухах. "
                "Спочатку скасуйте пізніші рухи."
            ),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("№"),
                        rx.table.column_header_cell("Тип"),
                        rx.table.column_header_cell("Дата"),
                        rx.table.column_header_cell("Статус"),
                    ),
                ),
                rx.table.body(
                    rx.foreach(
                        ViewMovementsState.cancel_conflict_rows,
                        lambda row: rx.table.row(
                            rx.table.cell(row[0]),
                            rx.table.cell(row[1]),
                            rx.table.cell(row[2]),
                            rx.table.cell(row[3]),
                        ),
                    ),
                ),
                variant="surface",
                width="100%",
                margin_top="1em",
            ),
            rx.flex(
                rx.dialog.close(
                    rx.button(
                        "Закрити",
                        on_click=ViewMovementsState.set_cancel_conflict_dialog_open(False),
                    ),
                ),
                justify="end",
                margin_top="1em",
            ),
            max_width="42em",
        ),
        open=ViewMovementsState.is_cancel_conflict_dialog_open,
        on_open_change=ViewMovementsState.set_cancel_conflict_dialog_open,
    )


def item_preview() -> rx.Component:
    return rx.vstack(
        cancel_conflict_dialog(),
        rx.heading(f"Переміщення №{ViewMovementsState.item.id}", size="7", width="100%"),
        rx.hstack(
            rx.text("Дата:"),
            rx.text(ViewMovementsState.item.date)
        ),
        rx.hstack(
            rx.text("Склад відправлення:"),
            rx.text(ViewMovementsState.item.incoming_storage.title)
        ),
        rx.hstack(
            rx.text("Власник відправлення:"),
            rx.text(ViewMovementsState.item.incoming_owner.title)
        ),
        rx.hstack(
            rx.text("Склад призначення:"),
            rx.text(ViewMovementsState.item.destination_storage.title)
        ),
        rx.hstack(
            rx.text("Власник призначення:"),
            rx.text(ViewMovementsState.item.destination_owner.title)
        ),
        products(width="100%"),
        rx.hstack(
            rx.text("Статус:"),
            rx.text(ViewMovementsState.item_status)
        ),
        rx.hstack(
            rx.text("Коментар:"),
            rx.text(ViewMovementsState.item.comment)
        ),
        rx.spacer(),
        rx.hstack(
            rx.spacer(),
            rx.cond(
                AppState.get_user_actions.contains(ActionEnum.MOVEMENTS_DELETE) & (ViewMovementsState.current_is_canceled == False),
                rx.button(
                    "Скасувати",
                    color_scheme="red",
                    on_click=MovementsState.delete_one,
                ),
            ),

            width="100%",
        ),

        spacing="3",

        height="100%",
        width="100%"
    )


def item_preview_tab_content() -> rx.Component:
    return rx.tabs.content(
        item_preview(),

        value=MovementsState.Pages.VIEW,
    )


def table_row(item: Movement) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item.id)),
        rx.table.row_header_cell(
            rx.link(
                item.date,
                href=f"{routes.MOVEMENT_MOVEMENTS_VIEW_ID}{item.id}"
            ),

            align="left"
        ),
        rx.table.cell(rx.text(item.incoming_storage.title)),
        rx.table.cell(rx.text(item.incoming_owner.title)),
        rx.table.cell(rx.text(item.destination_storage.title)),
        rx.table.cell(rx.text(item.destination_owner.title)),
        rx.table.cell(rx.text(ListMovementsState.get_movement_statuses[item.status])),
    )


def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("№", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Дата", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Склад відправлення", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Власник відправлення", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Склад призначення", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Власник призначення", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Статус", color=rx.color("accent", 2)),
            ),

            background_color=rx.color("accent", 9)
        ),
        rx.table.body(
            rx.foreach(ListMovementsState.items, table_row),

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
                rx.heading("Переміщення", size="6"),
                rx.spacer(),
                rx.cond(
                    AppState.get_user_actions.contains(ActionEnum.MOVEMENTS_CREATE),
                    rx.button(
                        "Додати",
                        on_click=rx.redirect(routes.MOVEMENT_MOVEMENTS_ADD)
                    ),
                ),

                width="100%"
            ),
            rx.cond(
                ListMovementsState.has_items,
                table(),
                rx.text("Записів немає.")
            ),

            width="100%",
            height="100%",
        ),

        value=MovementsState.Pages.LIST,
    )


def add_form() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text("Дата:"),
            rx.input(
                value=AddMovementsState.current_date,
                on_change=AddMovementsState.on_change_date,
                type="date",
                required=True,
                size="3",
            ),
            rx.text("Склад відправлення:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%",
                ),
                rx.select.content(
                    rx.vstack(
                        rx.hstack(
                            rx.button(
                                "Пошук",
                                type="button",
                                on_click=AddMovementsState.on_click_search_name_incoming_storage,
                            ),
                            rx.input(
                                value=AddMovementsState.search_name_incoming_storage,
                                on_change=AddMovementsState.on_change_search_name_incoming_storage,
                                placeholder="Введіть назву для пошуку",
                                width="100%",
                            ),
                            width="100%",
                        ),
                        rx.foreach(
                            AddMovementsState.filtered_incoming_storages,
                            lambda storage: rx.select.item(storage[0], value=storage[1], width="100%"),
                        ),
                        width="100%",
                    ),
                    width="100%",
                ),
                required=True,
                value=AddMovementsState.id_incoming_storage,
                on_change=AddMovementsState.on_change_id_incoming_storage,
            ),
            rx.text("Власник відправлення:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%",
                ),
                rx.select.content(
                    rx.foreach(
                        AddMovementsState.list_owners,
                        lambda owner: rx.select.item(owner[0], value=owner[1]),
                    ),
                    width="100%",
                ),
                required=True,
                value=AddMovementsState.id_incoming_owner,
                on_change=AddMovementsState.on_change_id_incoming_owner,
            ),
            rx.text("Склад призначення:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%",
                ),
                rx.select.content(
                    rx.vstack(
                        rx.hstack(
                            rx.button(
                                "Пошук",
                                type="button",
                                on_click=AddMovementsState.on_click_search_name_destination_storage,
                            ),
                            rx.input(
                                value=AddMovementsState.search_name_destination_storage,
                                on_change=AddMovementsState.on_change_search_name_destination_storage,
                                placeholder="Введіть назву для пошуку",
                                width="100%",
                            ),
                            width="100%",
                        ),
                        rx.foreach(
                            AddMovementsState.filtered_destination_storages,
                            lambda storage: rx.select.item(storage[0], value=storage[1], width="100%"),
                        ),
                        width="100%",
                    ),
                    width="100%",
                ),
                required=True,
                value=AddMovementsState.id_destination_storage,
                on_change=AddMovementsState.on_change_id_destination_storage,
            ),
            rx.text("Власник призначення:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%",
                ),
                rx.select.content(
                    rx.foreach(
                        AddMovementsState.list_owners,
                        lambda owner: rx.select.item(owner[0], value=owner[1]),
                    ),
                    width="100%",
                ),
                required=True,
                value=AddMovementsState.id_destination_owner,
                on_change=AddMovementsState.on_change_id_destination_owner,
            ),
            products(width="100%"),
            rx.hstack(
                rx.text("Статус:"),
                rx.select(
                    AddMovementsState.get_movement_statuses,
                    placeholder="Оберіть зі списку",
                    required=True,
                    value=AddMovementsState.status,
                    on_change=AddMovementsState.on_change_status,
                ),
            ),
            rx.text("Коментар:"),
            rx.text_area(value=AddMovementsState.comment, on_change=AddMovementsState.on_change_comment),
            rx.hstack(
                rx.button(
                    "Скасувати",
                    color_scheme="red",
                    on_click=rx.redirect(routes.MOVEMENT_MOVEMENTS),
                ),
                rx.button(
                    "Зберегти",
                    color_scheme="green",
                    on_click=AddMovementsState.add_one,
                ),

                justify="end",
            ),

            align="stretch",
        ),

        height="100%",
        width="100%",
    )


def add_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading("Додавання переміщення", size="7", width="100%", margin_bottom="0.5em"),
        add_form(),

        value=MovementsState.Pages.ADD,
    )


def edit_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading("Редагування переміщення", size="7", width="100%", margin_bottom="0.5em"),
        rx.text("Редагування переміщення поки що не реалізовано."),

        value=MovementsState.Pages.EDIT,
    )


def index() -> rx.Component:
    return rx.tabs.root(
        rx.cond(AppState.get_user_actions.contains(ActionEnum.MOVEMENTS_LIST),
            list_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.MOVEMENTS_VIEW),
            item_preview_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.MOVEMENTS_CREATE),
            add_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.MOVEMENTS_EDIT),
            edit_tab_content()),

        value=MovementsState.current_page,

        height="100%",
        width="100%",
    )
