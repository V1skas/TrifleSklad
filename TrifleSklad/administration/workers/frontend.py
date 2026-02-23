import reflex as rx

from TrifleSklad import routes
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action
from TrifleSklad.administration.workers.backend import *

def item_preview() -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.hstack(
                rx.button(
                    "Повернутись",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(routes.ADMIN_WORKERS)
                ),
                rx.heading("Співробітники/Перегляд", size="7", color=rx.color("accent", 9)),
                rx.hstack(
                    rx.cond(AppState.has_permission(Action.WORKERS_DELETE),
                        rx.button(
                            "Видалити",
                            color_scheme="red",
                            variant="ghost",
                            size="3",
                            on_click=WorkersState.delete_one(ViewWorkerState.item.id)
                        ),                            
                    ),
                    rx.cond(AppState.has_permission(Action.WORKERS_EDIT),
                        rx.button(
                            "Редагувати",
                            variant="ghost",
                            size="3",
                            on_click=rx.redirect(f"{routes.ADMIN_WORKERS_EDIT_ID}{ViewWorkerState.item.id}")
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
        
        rx.heading(ViewWorkerState.item.fio, size="7", width="100%"),
        rx.text(ViewWorkerState.item.position, width="100%"),
        rx.text(ViewWorkerState.item.phone_number, width="100%"),
        rx.text(ViewWorkerState.item.email, width="100%"),
        rx.spacer(),

        spacing="3",

        height="100%",
        width="100%"
    )

def item_preview_tab_content() -> rx.Component:
    return rx.tabs.content(
        item_preview(),

        value=WorkersState.Pages.VIEW
    )

def table_row(item: Tuple[int, Worker]) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(
            rx.link(
                item[1].fio,
                href=f"{routes.ADMIN_WORKERS_VIEW_ID}{item[1].id}",
            ),

            align="left"
        ),
        rx.table.cell(
            item[1].position,
            align="left"
        ),
        rx.table.cell(
            item[1].phone_number,
            align="left"
        ),
        rx.table.cell(
            item[1].email,
            align="left"
        ),
    )

def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Прізвище І.Б.", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Посада", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Телефон", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Email", color=rx.color("accent", 2)),
            ),

            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(ListWorkersState.get_items, table_row),

            width="100%"
        ),

        variant="surface",
        width="100%"
    )

def list_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            rx.box(
                rx.hstack(
                    rx.heading("Співробітники", size="7", color=rx.color("accent", 9)),
                    rx.cond(AppState.has_permission(Action.WORKERS_CREATE),
                        rx.button(
                                "Створити",
                                variant="ghost",
                                size="3",
                                on_click=rx.redirect(routes.ADMIN_WORKERS_ADD)
                            ),
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
            rx.cond(ListWorkersState.has_items,
                table(),
                rx.text("Записей нет.")
            ),

            width="100%",
            height="100%",
        ),

        value=WorkersState.Pages.LIST,
    )

def add_form() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text("*Прізвище І.Б.:"),
            rx.input(
                name="fio",
                width="100%",

                value=AddWorkerState.item.fio,
                on_change=AddWorkerState.change_fio
            ),
            rx.text("*Посада:"),
            rx.input(
                name="position",   
                width="100%",

                value=AddWorkerState.item.position,
                on_change=AddWorkerState.change_position
            ),
            rx.text("Телефон:"),
            rx.input(
                type="tel",
                name="phone_number",
                width="100%",

                value=AddWorkerState.item.phone_number,
                on_change=AddWorkerState.change_phone_number
            ),
            rx.text("Email:"),
            rx.input(
                type="email",
                name="email",
                width="100%",

                value=AddWorkerState.item.email,
                on_change=AddWorkerState.change_email
            ),

            align="stretch"
        ),

        height="100%",
        width="100%",
    )

def edit_form() -> rx.Component:
    return rx.card(
            rx.vstack(
                rx.text("*Прізвище І.Б.:"),
                rx.input(
                    name="fio",
                    width="100%",

                    value=EditWorkerState.item.fio,
                    on_change=EditWorkerState.change_fio
                ),
                rx.text("*Посада:"),
                rx.input(
                    name="position",
                    width="100%",

                    value=EditWorkerState.item.position,
                    on_change=EditWorkerState.change_position
                ),
                rx.text("Телефон:"),
                rx.input(
                    type="tel",
                    name="phone_number",
                    width="100%",

                    value=EditWorkerState.item.phone_number,
                    on_change=EditWorkerState.change_phone_number
                ),
                rx.text("Email:"),
                rx.input(
                    type="email",
                    name="email",
                    width="100%",

                    value=EditWorkerState.item.email,
                    on_change=EditWorkerState.change_email
                ),

                align="stretch"
            ),

        height="100%",
        width="100%",
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
                        on_click=rx.redirect(routes.ADMIN_WORKERS)
                    ),
                    rx.heading("Співробітники/Створення", size="7", color=rx.color("accent", 9)),
                    rx.button(
                        "Зберегти",
                        variant="ghost",
                        size="3",
                        on_click=AddWorkerState.add_one
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

            width="100%",
            height="100%",
        ),

        value=WorkersState.Pages.ADD
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
                        on_click=rx.redirect(f"{routes.ADMIN_WORKERS_VIEW_ID}/{EditWorkerState.item.id}")
                    ),
                    rx.heading("Співробітники/Редагування", size="7", color=rx.color("accent", 9)),
                    rx.button(
                        "Зберегти",
                        variant="ghost",
                        size="3",
                        on_click=EditWorkerState.edit_one
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

            width="100%",
            height="100%",
        ),

        value=WorkersState.Pages.EDIT
    )

def index() -> rx.Component:
    return rx.tabs.root(
        rx.cond(AppState.has_permission(Action.WORKERS_LIST), list_tab_content()),
        rx.cond(AppState.has_permission(Action.WORKERS_CREATE), add_tab_content()),
        rx.cond(AppState.has_permission(Action.WORKERS_EDIT), edit_tab_content()),
        rx.cond(AppState.has_permission(Action.WORKERS_LIST), item_preview_tab_content()),

        value=WorkersState.current_page,

        height="100%",
        width="100%"
    )
