from typing import List, Optional, Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.declared import MovementsStatus, movements_status_list
from TrifleSklad.models import Issue
from TrifleSklad.movement.issues.backend import (
    AddIssueState,
    EditIssueState,
    IssueState,
    ListIssueState,
    ViewIssueState,
)
from TrifleSklad.movement.products.frontend import index as products


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
                    "Место назначения", color=rx.color("accent", 2)
                ),
                rx.table.column_header_cell("Получатель", color=rx.color("accent", 2)),
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
            rx.hstack(
                rx.heading("Выдачи", size="6"),
                rx.spacer(),
                rx.button("Добавить", on_click=rx.redirect(routes.MOVEMENT_ISSUES_ADD)),
                width="100%",
            ),
            rx.cond(ListIssueState.has_items, issues_table(), rx.text("Записей нет.")),
            width="100%",
            height="100%",
        ),
        value=IssueState.Pages.LIST,
    )


def add_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading("Добавление выдачи", size="7", width="100%", margin_bottom="0.5em"),
        rx.card(
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
                        placeholder="Выберите из списка",
                        width="100%",
                    ),
                    rx.select.content(
                        rx.foreach(
                            AddIssueState.list_incoming_storages,
                            lambda storage: rx.select.item(
                                storage[0], value=storage[1]
                            ),
                        ),
                        width="100%",
                    ),
                    name="id_incoming_storage",
                    required=True,
                    value=AddIssueState.id_incoming_storage,
                    on_change=AddIssueState.on_change_id_incoming_storage,
                ),
                rx.text("Владелец:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Выберите из списка",
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
                rx.text("Место назначения:"),
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
                                    on_click=AddIssueState.on_click_search_name_destination_storage,
                                ),
                                rx.input(
                                    placeholder="Введите название для поиска",
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
                rx.text("Получатель:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Выберите из списка",
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
                        AddIssueState.get_movement_statuses,
                        name="status",
                        placeholder="Выберите из списка",
                        required=True,
                        width="100%",
                        value=AddIssueState.status,
                        on_change=AddIssueState.on_change_status,
                    ),
                ),
                rx.text("Комментарий:"),
                rx.text_area(
                    name="comment",
                    width="100%",
                    value=AddIssueState.item.movement.comment,
                    on_change=AddIssueState.on_change_comment,
                ),
                rx.hstack(
                    rx.button(
                        "Отмена",
                        color_scheme="red",
                        on_click=rx.redirect(routes.MOVEMENT_ISSUES),
                    ),
                    rx.button(
                        "Сохранить",
                        color_scheme="green",
                        type="submit",
                        on_click=AddIssueState.add_one,
                    ),
                    justify="end",
                ),
            )
        ),
        value=IssueState.Pages.ADD,
    )


def edit_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading(
            "Редактирование выдачи", size="7", width="100%", margin_bottom="0.5em"
        ),
        rx.card(
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
                        placeholder="Выберите из списка",
                        width="100%",
                    ),
                    rx.select.content(
                        rx.foreach(
                            EditIssueState.list_incoming_storages,
                            lambda storage: rx.select.item(
                                storage[0], value=storage[1]
                            ),
                        ),
                        width="100%",
                    ),
                    disabled=True,
                    name="id_incoming_storage",
                    required=True,
                    value=EditIssueState.id_incoming_storage,
                    on_change=EditIssueState.on_change_id_incoming_storage,
                ),
                rx.text("Владелец:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Выберите из списка",
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
                rx.text("Место назначения:"),
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
                                    on_click=EditIssueState.on_click_search_name_destination_storage,
                                ),
                                rx.input(
                                    placeholder="Введите название для поиска",
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
                rx.text("Получатель:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Выберите из списка",
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
                        EditIssueState.get_movement_statuses,
                        name="status",
                        placeholder="Выберите из списка",
                        required=True,
                        width="100%",
                        value=EditIssueState.status,
                        on_change=EditIssueState.on_change_status,
                    ),
                ),
                rx.text("Комментарий:"),
                rx.text_area(
                    name="comment",
                    width="100%",
                    value=EditIssueState.item.movement.comment,
                    on_change=EditIssueState.on_change_comment,
                ),
                rx.hstack(
                    rx.button(
                        "Отмена",
                        color_scheme="red",
                        on_click=rx.redirect(routes.MOVEMENT_ISSUES),
                    ),
                    rx.button(
                        "Сохранить",
                        color_scheme="green",
                        type="submit",
                        on_click=EditIssueState.edit_one,
                    ),
                    justify="end",
                ),
            )
        ),
        value=IssueState.Pages.EDIT,
    )


def view_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading(
            f"Выдача №{ViewIssueState.item.id}",
            size="7",
            width="100%",
            margin_bottom="0.5em",
        ),
        rx.card(
            rx.vstack(
                rx.text(f"Дата: {ViewIssueState.item.movement.date}"),
                rx.text(
                    f"Склад: {ViewIssueState.item.movement.incoming_storage.title}"
                ),
                rx.text(
                    f"Владелец: {ViewIssueState.item.movement.incoming_owner.title}"
                ),
                rx.text(
                    f"Место назначения: {ViewIssueState.item.movement.destination_storage.title}"
                ),
                rx.text(f"Получатель: {ViewIssueState.item.recipient.fio}"),
                rx.text(
                    f"Статус: {ListIssueState.get_movement_statuses[ViewIssueState.item.movement.status]}"
                ),
                rx.text(f"Комментарий: {ViewIssueState.item.movement.comment}"),
                products(width="100%"),
                rx.hstack(
                    rx.button(
                        "Редактировать",
                        on_click=rx.redirect(
                            f"{routes.MOVEMENT_ISSUES_EDIT_ID}{ViewIssueState.item.id}"
                        ),
                    ),
                    rx.spacer(),
                    # rx.button(
                    #     "Удалить",
                    #     color_scheme="red",
                    #     on_click=IssueState.delete_one(ViewIssueState.item.id),
                    # ),
                    width="100%",
                ),
            ),
        ),
        value=IssueState.Pages.VIEW,
    )


def index() -> rx.Component:
    return rx.tabs.root(
        list_tab_content(),
        add_tab_content(),
        view_tab_content(),
        edit_tab_content(),
        value=IssueState.current_page,
        height="100%",
        width="100%",
    )
