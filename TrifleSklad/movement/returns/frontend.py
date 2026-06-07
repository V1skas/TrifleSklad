import reflex as rx

from components.elements import subpage_header

from TrifleSklad import routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.movement.returns.backend import (
    AddReturnsState,
    EditReturnsState,
    ListReturnsState,
    ReturnsState,
    ViewReturnsState,
)
from TrifleSklad.movement.products.frontend import index as products
from TrifleSklad.movement.list_components import filter_button, filter_card, pagination

from TrifleSklad.models import Movement
from TrifleSklad.state import AppState


def cancel_conflict_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Скасування неможливе"),
            rx.dialog.description(
                "Товар із цього повернення бере участь у наведених нижче рухах. "
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
                        ViewReturnsState.cancel_conflict_rows,
                        lambda row: rx.table.row(
                            rx.table.cell(row[0]),
                            rx.table.cell(row[1]),
                            rx.table.cell(
                                rx.link(
                                    row[2],
                                    on_click=rx.redirect(row[4]),
                                    cursor="pointer",
                                ),
                            ),
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
                        on_click=ViewReturnsState.set_cancel_conflict_dialog_open(False),
                    ),
                ),
                justify="end",
                margin_top="1em",
            ),
            max_width="42em",
        ),
        open=ViewReturnsState.is_cancel_conflict_dialog_open,
        on_open_change=ViewReturnsState.set_cancel_conflict_dialog_open,
    )


def item_preview() -> rx.Component:
    return rx.vstack(
        rx.hstack(rx.text("Дата:"), rx.text(ViewReturnsState.item.date)),
        rx.hstack(
            rx.text("Звідки (площадка/відділ):"),
            rx.text(ViewReturnsState.item.incoming_storage.title),
        ),
        rx.hstack(
            rx.text("Склад призначення:"),
            rx.text(ViewReturnsState.item.destination_storage.title),
        ),
        products(width="100%"),
        rx.hstack(rx.text("Статус:"), rx.text(ViewReturnsState.item_status)),
        rx.hstack(rx.text("Коментар:"), rx.text(ViewReturnsState.item.comment)),
        spacing="3",
        align="stretch",
        height="100%",
        width="100%",
    )


def item_preview_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            cancel_conflict_dialog(),
            subpage_header(
                "Повернення/Перегляд",
                left=rx.button(
                    "Повернутись",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(routes.MOVEMENT_RETURNS),
                ),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.RETURNS_EDIT)
                        & (ViewReturnsState.current_is_canceled == False),
                        rx.button(
                            "Редагувати",
                            variant="ghost",
                            size="3",
                            on_click=rx.redirect(
                                f"{routes.MOVEMENT_RETURNS_EDIT_ID}{ViewReturnsState.item.id}"
                            ),
                        ),
                    ),
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.RETURNS_DELETE)
                        & (ViewReturnsState.current_is_canceled == False),
                        rx.button(
                            "Скасувати",
                            color_scheme="red",
                            variant="ghost",
                            size="3",
                            on_click=ReturnsState.delete_one,
                        ),
                    ),
                ],
            ),
            item_preview(),
            width="100%",
        ),
        value=ReturnsState.Pages.VIEW,
    )


def table_row(item: Movement) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item.id)),
        rx.table.row_header_cell(
            rx.link(item.date, href=f"{routes.MOVEMENT_RETURNS_VIEW_ID}{item.id}"),
            align="left",
        ),
        rx.table.cell(rx.text(item.incoming_storage.title)),
        rx.table.cell(rx.text(item.destination_storage.title)),
        rx.table.cell(rx.text(ListReturnsState.get_movement_statuses[item.status])),
    )


def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("№", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Дата", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Звідки", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Склад призначення", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Статус", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(ListReturnsState.items, table_row),
            height="100%",
            width="100%",
        ),
        variant="surface",
        height="100%",
        width="100%",
    )


def list_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            subpage_header(
                "Повернення",
                actions=[
                    filter_button(ListReturnsState),
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.RETURNS_CREATE),
                        rx.button(
                            "Додати",
                            variant="ghost",
                            size="3",
                            on_click=rx.redirect(routes.MOVEMENT_RETURNS_ADD),
                        ),
                    ),
                ],
            ),
            filter_card(ListReturnsState),
            rx.cond(ListReturnsState.has_items, table(), rx.text("Записів немає.")),
            pagination(ListReturnsState),
            width="100%",
            height="100%",
        ),
        value=ReturnsState.Pages.LIST,
    )


def add_form() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text("Дата:"),
            rx.input(
                value=AddReturnsState.current_date,
                on_change=AddReturnsState.on_change_date,
                type="date",
                required=True,
                size="3",
                width="100%",
            ),
            rx.text("Звідки (площадка/відділ):"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(
                        AddReturnsState.list_source_storages,
                        lambda storage: rx.select.item(storage[0], value=storage[1]),
                    ),
                    width="100%",
                ),
                required=True,
                value=AddReturnsState.id_incoming_storage,
                on_change=AddReturnsState.on_change_id_incoming_storage,
            ),
            rx.text("Склад призначення:"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(
                        AddReturnsState.list_destination_storages,
                        lambda storage: rx.select.item(storage[0], value=storage[1]),
                    ),
                    width="100%",
                ),
                required=True,
                value=AddReturnsState.id_destination_storage,
                on_change=AddReturnsState.on_change_id_destination_storage,
            ),
            products(width="100%"),
            rx.hstack(
                rx.text("Статус:"),
                rx.select(
                    AddReturnsState.editable_statuses,
                    placeholder="Оберіть зі списку",
                    required=True,
                    value=AddReturnsState.status,
                    on_change=AddReturnsState.on_change_status,
                ),
            ),
            rx.text("Коментар:"),
            rx.text_area(
                value=AddReturnsState.comment,
                on_change=AddReturnsState.on_change_comment,
                width="100%",
            ),
            spacing="3",
            align="stretch",
            width="100%",
        ),
        height="100%",
        width="100%",
    )


def add_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            subpage_header(
                "Повернення/Додавання",
                left=rx.button(
                    "Скасувати",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(routes.MOVEMENT_RETURNS),
                ),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.RETURNS_CREATE),
                        rx.button(
                            "Зберегти",
                            variant="ghost",
                            size="3",
                            on_click=AddReturnsState.add_one,
                        ),
                    ),
                ],
            ),
            add_form(),
            width="100%",
        ),
        value=ReturnsState.Pages.ADD,
    )


def edit_form() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text("Дата:"),
            rx.input(
                value=EditReturnsState.item.date,
                type="date",
                required=True,
                size="3",
                disabled=True,
            ),
            rx.text("Звідки (площадка/відділ):"),
            rx.input(
                value=EditReturnsState.item.incoming_storage.title,
                disabled=True,
                width="100%",
            ),
            rx.text("Склад призначення:"),
            rx.input(
                value=EditReturnsState.item.destination_storage.title,
                disabled=True,
                width="100%",
            ),
            products(width="100%"),
            rx.hstack(
                rx.text("Статус:"),
                rx.select(
                    EditReturnsState.editable_statuses,
                    placeholder="Оберіть зі списку",
                    required=True,
                    value=EditReturnsState.status,
                    on_change=EditReturnsState.on_change_status,
                ),
            ),
            rx.text("Коментар:"),
            rx.text_area(
                value=EditReturnsState.item.comment,
                on_change=EditReturnsState.on_change_comment,
                width="100%",
            ),
            spacing="3",
            align="stretch",
            width="100%",
        ),
        height="100%",
        width="100%",
    )


def edit_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            subpage_header(
                "Повернення/Редагування",
                left=rx.button(
                    "Скасувати",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(
                        f"{routes.MOVEMENT_RETURNS_VIEW_ID}{EditReturnsState.item.id}"
                    ),
                ),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.RETURNS_EDIT),
                        rx.button(
                            "Зберегти",
                            variant="ghost",
                            size="3",
                            on_click=EditReturnsState.edit_one,
                        ),
                    ),
                ],
            ),
            edit_form(),
            width="100%",
        ),
        value=ReturnsState.Pages.EDIT,
    )


def index() -> rx.Component:
    return rx.tabs.root(
        rx.cond(AppState.get_user_actions.contains(ActionEnum.RETURNS_LIST),
            list_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.RETURNS_VIEW),
            item_preview_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.RETURNS_CREATE),
            add_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.RETURNS_EDIT),
            edit_tab_content()),
        value=ReturnsState.current_page,
        height="100%",
        width="100%",
    )
