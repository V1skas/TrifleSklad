from typing import Tuple

import reflex as rx

from components.elements import subpage_header

from TrifleSklad import routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.models import Issue
from TrifleSklad.state import AppState
from TrifleSklad.movement.issues.backend import (
    AddIssueState,
    EditIssueState,
    IssueState,
    ListIssueState,
    ViewIssueState,
)
from TrifleSklad.movement.products.frontend import index as products
from TrifleSklad.movement.list_components import filter_button, filter_card, pagination


def issues_table_row(item: Tuple[int, Issue]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item[1].id)),
        rx.table.row_header_cell(
            rx.link(
                item[1].movement.date,
                href=f"{routes.MOVEMENT_ISSUES_VIEW_ID}{item[1].id}",
            ),
            align="left",
        ),
        rx.table.cell(rx.text(item[1].movement.destination_storage.title)),
        rx.table.cell(rx.text(item[1].recipient.fio)),
        rx.table.cell(
            rx.text(ListIssueState.get_movement_statuses[item[1].movement.status])
        ),
    )


def issues_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("№", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Дата", color=rx.color("accent", 2)),
                rx.table.column_header_cell(
                    "Місце призначення", color=rx.color("accent", 2)
                ),
                rx.table.column_header_cell("Одержувач", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Статус", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(ListIssueState.get_items, issues_table_row),
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
                "Видачі",
                actions=[
                    filter_button(ListIssueState),
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.ISSUES_CREATE),
                        rx.button(
                            "Додати",
                            variant="ghost",
                            size="3",
                            on_click=rx.redirect(routes.MOVEMENT_ISSUES_ADD),
                        ),
                    ),
                ],
            ),
            filter_card(ListIssueState),
            rx.cond(ListIssueState.has_items, issues_table(), rx.text("Записів немає.")),
            pagination(ListIssueState),
            width="100%",
            height="100%",
        ),
        value=IssueState.Pages.LIST,
    )


def add_form() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text("Дата:"),
            rx.input(
                name="date",
                type="date",
                required=True,
                size="3",
                default_value=AddIssueState.item.movement.date,
                width="100%",
                on_change=AddIssueState.on_change_date,
            ),
            rx.text("Склад:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%",
                ),
                rx.select.content(
                    rx.foreach(
                        AddIssueState.list_incoming_storages,
                        lambda storage: rx.select.item(storage[0], value=storage[1]),
                    ),
                    width="100%",
                ),
                name="id_incoming_storage",
                required=True,
                value=AddIssueState.id_incoming_storage,
                on_change=AddIssueState.on_change_id_incoming_storage,
            ),
            rx.text("Власник:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%",
                ),
                rx.select.content(
                    rx.foreach(
                        AddIssueState.list_owners,
                        lambda owner: rx.select.item(owner[0], value=owner[1]),
                    ),
                    width="100%",
                ),
                name="id_incoming_owner",
                required=True,
                value=AddIssueState.id_incoming_owner,
                on_change=AddIssueState.on_change_id_incoming_owner,
            ),
            rx.text("Місце призначення:"),
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
                                on_click=AddIssueState.on_click_search_name_destination_storage,
                            ),
                            rx.input(
                                placeholder="Введіть назву для пошуку",
                                width="100%",
                                value=AddIssueState.search_name_destination_storage,
                                on_change=AddIssueState.on_change_search_name_destination_storage,
                            ),
                            width="100%",
                        ),
                        rx.foreach(
                            AddIssueState.list_destination_storages,
                            lambda storage: rx.select.item(
                                storage[0], value=storage[1], width="100%"
                            ),
                        ),
                        width="100%",
                    ),
                    width="100%",
                ),
                name="id_destination_storage",
                required=True,
                value=AddIssueState.id_destination_storage,
                on_change=AddIssueState.on_change_id_destination_storage,
            ),
            rx.text("Одержувач:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%",
                ),
                rx.select.content(
                    rx.foreach(
                        AddIssueState.list_workers,
                        lambda worker: rx.select.item(worker[0], value=worker[1]),
                    ),
                    width="100%",
                ),
                name="id_recipient",
                required=True,
                value=AddIssueState.id_recipient,
                on_change=AddIssueState.on_change_id_recipient,
            ),
            products(width="100%"),
            rx.hstack(
                rx.text("Статус:"),
                rx.select(
                    AddIssueState.editable_statuses,
                    name="status",
                    placeholder="Оберіть зі списку",
                    required=True,
                    width="100%",
                    value=AddIssueState.status,
                    on_change=AddIssueState.on_change_status,
                ),
            ),
            rx.text("Коментар:"),
            rx.text_area(
                name="comment",
                width="100%",
                value=AddIssueState.item.movement.comment,
                on_change=AddIssueState.on_change_comment,
            ),
            spacing="3",
            align="stretch",
            width="100%",
        ),
        width="100%",
        height="100%",
    )


def add_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            subpage_header(
                "Видачі/Додавання",
                left=rx.button(
                    "Скасувати",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(routes.MOVEMENT_ISSUES),
                ),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.ISSUES_CREATE),
                        rx.button(
                            "Зберегти",
                            variant="ghost",
                            size="3",
                            on_click=AddIssueState.add_one,
                        ),
                    ),
                ],
            ),
            add_form(),
            width="100%",
        ),
        value=IssueState.Pages.ADD,
    )


def edit_form() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text("Дата:"),
            rx.input(
                name="date",
                type="date",
                required=True,
                size="3",
                disabled=True,
                default_value=EditIssueState.item.movement.date,
                width="100%",
                on_change=EditIssueState.on_change_date,
            ),
            rx.text("Склад:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%",
                ),
                rx.select.content(
                    rx.foreach(
                        EditIssueState.list_incoming_storages,
                        lambda storage: rx.select.item(storage[0], value=storage[1]),
                    ),
                    width="100%",
                ),
                disabled=True,
                name="id_incoming_storage",
                required=True,
                value=EditIssueState.id_incoming_storage,
                on_change=EditIssueState.on_change_id_incoming_storage,
            ),
            rx.text("Власник:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%",
                ),
                rx.select.content(
                    rx.foreach(
                        EditIssueState.list_owners,
                        lambda owner: rx.select.item(owner[0], value=owner[1]),
                    ),
                    width="100%",
                ),
                name="id_incoming_owner",
                required=True,
                disabled=True,
                value=EditIssueState.id_incoming_owner,
                on_change=EditIssueState.on_change_id_incoming_owner,
            ),
            rx.text("Місце призначення:"),
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
                                on_click=EditIssueState.on_click_search_name_destination_storage,
                            ),
                            rx.input(
                                placeholder="Введіть назву для пошуку",
                                width="100%",
                                value=EditIssueState.search_name_destination_storage,
                                on_change=EditIssueState.on_change_search_name_destination_storage,
                            ),
                            width="100%",
                        ),
                        rx.foreach(
                            EditIssueState.list_destination_storages,
                            lambda storage: rx.select.item(
                                storage[0], value=storage[1], width="100%"
                            ),
                        ),
                        width="100%",
                    ),
                    width="100%",
                ),
                name="id_destination_storage",
                required=True,
                disabled=True,
                value=EditIssueState.id_destination_storage,
                on_change=EditIssueState.on_change_id_destination_storage,
            ),
            rx.text("Одержувач:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%",
                ),
                rx.select.content(
                    rx.foreach(
                        EditIssueState.list_workers,
                        lambda worker: rx.select.item(worker[0], value=worker[1]),
                    ),
                    width="100%",
                ),
                name="id_recipient",
                required=True,
                disabled=True,
                value=EditIssueState.id_recipient,
                on_change=EditIssueState.on_change_id_recipient,
            ),
            products(width="100%"),
            rx.hstack(
                rx.text("Статус:"),
                rx.select(
                    EditIssueState.editable_statuses,
                    name="status",
                    placeholder="Оберіть зі списку",
                    required=True,
                    width="100%",
                    value=EditIssueState.status,
                    on_change=EditIssueState.on_change_status,
                ),
            ),
            rx.text("Коментар:"),
            rx.text_area(
                name="comment",
                width="100%",
                value=EditIssueState.item.movement.comment,
                on_change=EditIssueState.on_change_comment,
            ),
            spacing="3",
            align="stretch",
            width="100%",
        ),
        width="100%",
        height="100%",
    )


def edit_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            subpage_header(
                "Видачі/Редагування",
                left=rx.button(
                    "Скасувати",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(routes.MOVEMENT_ISSUES),
                ),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.ISSUES_EDIT),
                        rx.button(
                            "Зберегти",
                            variant="ghost",
                            size="3",
                            on_click=EditIssueState.edit_one,
                        ),
                    ),
                ],
            ),
            edit_form(),
            width="100%",
        ),
        value=IssueState.Pages.EDIT,
    )


def cancel_conflict_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Скасування неможливе"),
            rx.dialog.description(
                "Товар із цієї видачі бере участь у наведених нижче рухах. "
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
                        ViewIssueState.cancel_conflict_rows,
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
                        on_click=ViewIssueState.set_cancel_conflict_dialog_open(False),
                    ),
                ),
                justify="end",
                margin_top="1em",
            ),
            max_width="42em",
        ),
        open=ViewIssueState.is_cancel_conflict_dialog_open,
        on_open_change=ViewIssueState.set_cancel_conflict_dialog_open,
    )


def view_body() -> rx.Component:
    return rx.vstack(
        rx.text(f"Дата: {ViewIssueState.item.movement.date}"),
        rx.text(f"Склад: {ViewIssueState.item.movement.incoming_storage.title}"),
        rx.text(f"Власник: {ViewIssueState.item.movement.incoming_owner.title}"),
        rx.text(
            f"Місце призначення: {ViewIssueState.item.movement.destination_storage.title}"
        ),
        rx.text(f"Одержувач: {ViewIssueState.item.recipient.fio}"),
        rx.text(
            f"Статус: {ListIssueState.get_movement_statuses[ViewIssueState.item.movement.status]}"
        ),
        rx.text(f"Коментар: {ViewIssueState.item.movement.comment}"),
        products(width="100%"),
        spacing="3",
        align="stretch",
        width="100%",
        height="100%",
    )


def view_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            cancel_conflict_dialog(),
            subpage_header(
                "Видачі/Перегляд",
                left=rx.button(
                    "Повернутись",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(routes.MOVEMENT_ISSUES),
                ),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.ISSUES_EDIT)
                        & (ViewIssueState.current_is_canceled == False),
                        rx.button(
                            "Редагувати",
                            variant="ghost",
                            size="3",
                            on_click=rx.redirect(
                                f"{routes.MOVEMENT_ISSUES_EDIT_ID}{ViewIssueState.item.id}"
                            ),
                        ),
                    ),
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.ISSUES_DELETE)
                        & (ViewIssueState.current_is_canceled == False),
                        rx.button(
                            "Скасувати",
                            color_scheme="red",
                            variant="ghost",
                            size="3",
                            on_click=IssueState.delete_one,
                        ),
                    ),
                ],
            ),
            view_body(),
            width="100%",
        ),
        value=IssueState.Pages.VIEW,
    )


def index() -> rx.Component:
    return rx.tabs.root(
        rx.cond(AppState.get_user_actions.contains(ActionEnum.ISSUES_LIST),
            list_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.ISSUES_CREATE),
            add_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.ISSUES_VIEW),
            view_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.ISSUES_EDIT),
            edit_tab_content()),
        value=IssueState.current_page,
        height="100%",
        width="100%",
    )
