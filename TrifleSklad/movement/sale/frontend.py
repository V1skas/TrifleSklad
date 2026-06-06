from typing import Tuple

import reflex as rx

from components.elements import subpage_header

from TrifleSklad import routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.models import Sale
from TrifleSklad.state import AppState
from TrifleSklad.movement.sale.backend import (
    AddSaleState,
    EditSaleState,
    ListSaleState,
    SaleState,
    ViewSaleState,
)
from TrifleSklad.movement.products.frontend import index as products


def cancel_conflict_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Скасування неможливе"),
            rx.dialog.description(
                "Товар із цього продажу бере участь у наведених нижче рухах. "
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
                        ViewSaleState.cancel_conflict_rows,
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
                        on_click=ViewSaleState.set_cancel_conflict_dialog_open(False),
                    ),
                ),
                justify="end",
                margin_top="1em",
            ),
            max_width="42em",
        ),
        open=ViewSaleState.is_cancel_conflict_dialog_open,
        on_open_change=ViewSaleState.set_cancel_conflict_dialog_open,
    )


def table_row(item: Tuple[int, Sale]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item[1].id)),
        rx.table.row_header_cell(
            rx.link(
                item[1].movement.date,
                href=f"{routes.MOVEMENT_SALES_VIEW_ID}{item[1].id}",
            ),
            align="left",
        ),
        rx.table.cell(rx.text(item[1].movement.incoming_storage.title)),
        rx.table.cell(rx.text(item[1].responsible.fio)),
        rx.table.cell(rx.text(item[1].movement.total_cost)),
        rx.table.cell(
            rx.text(ListSaleState.get_movement_statuses[item[1].movement.status])
        ),
    )


def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("№", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Дата", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Склад", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Відповідальний", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Вартість", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Статус", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(ListSaleState.get_items, table_row),
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
                "Продажі",
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.SALES_CREATE),
                        rx.button(
                            "Додати",
                            variant="ghost",
                            size="3",
                            on_click=rx.redirect(routes.MOVEMENT_SALES_ADD),
                        ),
                    ),
                ],
            ),
            rx.cond(ListSaleState.has_items, table(), rx.text("Записів немає.")),
            width="100%",
            height="100%",
        ),
        value=SaleState.Pages.LIST,
    )


def add_form() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text("Дата:"),
            rx.input(
                value=AddSaleState.current_date,
                on_change=AddSaleState.on_change_date,
                type="date",
                required=True,
                size="3",
                width="100%",
            ),
            rx.text("Склад:"),
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
                                on_click=AddSaleState.on_click_search_name_incoming_storage,
                            ),
                            rx.input(
                                value=AddSaleState.search_name_incoming_storage,
                                on_change=AddSaleState.on_change_search_name_incoming_storage,
                                placeholder="Введіть назву для пошуку",
                                width="100%",
                            ),
                            width="100%",
                        ),
                        rx.foreach(
                            AddSaleState.list_storages,
                            lambda storage: rx.select.item(
                                storage[0], value=storage[1], width="100%"
                            ),
                        ),
                        width="100%",
                    ),
                    width="100%",
                ),
                required=True,
                value=AddSaleState.id_incoming_storage,
                on_change=AddSaleState.on_change_id_incoming_storage,
            ),
            rx.text("Власник:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%",
                ),
                rx.select.content(
                    rx.foreach(
                        AddSaleState.list_owners,
                        lambda owner: rx.select.item(owner[0], value=owner[1]),
                    ),
                    width="100%",
                ),
                required=True,
                value=AddSaleState.id_incoming_owner,
                on_change=AddSaleState.on_change_id_incoming_owner,
            ),
            rx.text("Відповідальний:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%",
                ),
                rx.select.content(
                    rx.foreach(
                        AddSaleState.list_workers,
                        lambda worker: rx.select.item(worker[0], value=worker[1]),
                    ),
                    width="100%",
                ),
                required=True,
                value=AddSaleState.id_responsible,
                on_change=AddSaleState.on_change_id_responsible,
            ),
            products(width="100%"),
            rx.hstack(
                rx.text("Статус:"),
                rx.select(
                    AddSaleState.editable_statuses,
                    placeholder="Оберіть зі списку",
                    required=True,
                    value=AddSaleState.status,
                    on_change=AddSaleState.on_change_status,
                ),
            ),
            rx.text("Коментар:"),
            rx.text_area(
                value=AddSaleState.comment,
                on_change=AddSaleState.on_change_comment,
                width="100%",
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
                "Продажі/Додавання",
                left=rx.button(
                    "Скасувати",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(routes.MOVEMENT_SALES),
                ),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.SALES_CREATE),
                        rx.button(
                            "Зберегти",
                            variant="ghost",
                            size="3",
                            on_click=AddSaleState.add_one,
                        ),
                    ),
                ],
            ),
            add_form(),
            width="100%",
        ),
        value=SaleState.Pages.ADD,
    )


def edit_form() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text("Дата:"),
            rx.input(
                value=EditSaleState.item.movement.date,
                type="date",
                required=True,
                size="3",
                disabled=True,
                width="100%",
            ),
            rx.text("Склад:"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(
                        EditSaleState.list_storages,
                        lambda storage: rx.select.item(
                            storage[0], value=storage[1], width="100%"
                        ),
                    ),
                    width="100%",
                ),
                required=True,
                disabled=True,
                value=EditSaleState.id_incoming_storage,
            ),
            rx.text("Власник:"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(
                        EditSaleState.list_owners,
                        lambda owner: rx.select.item(owner[0], value=owner[1]),
                    ),
                    width="100%",
                ),
                required=True,
                disabled=True,
                value=EditSaleState.id_incoming_owner,
            ),
            rx.text("Відповідальний:"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(
                        EditSaleState.list_workers,
                        lambda worker: rx.select.item(worker[0], value=worker[1]),
                    ),
                    width="100%",
                ),
                required=True,
                disabled=True,
                value=EditSaleState.id_responsible,
            ),
            products(width="100%"),
            rx.hstack(
                rx.text("Статус:"),
                rx.select(
                    EditSaleState.editable_statuses,
                    placeholder="Оберіть зі списку",
                    required=True,
                    value=EditSaleState.status,
                    on_change=EditSaleState.on_change_status,
                ),
            ),
            rx.text("Коментар:"),
            rx.text_area(
                value=EditSaleState.item.movement.comment,
                on_change=EditSaleState.on_change_comment,
                width="100%",
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
                "Продажі/Редагування",
                left=rx.button(
                    "Скасувати",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(
                        f"{routes.MOVEMENT_SALES_VIEW_ID}{EditSaleState.item.id}"
                    ),
                ),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.SALES_EDIT),
                        rx.button(
                            "Зберегти",
                            variant="ghost",
                            size="3",
                            on_click=EditSaleState.edit_one,
                        ),
                    ),
                ],
            ),
            edit_form(),
            width="100%",
        ),
        value=SaleState.Pages.EDIT,
    )


def position_detail_dialog() -> rx.Component:
    # Деталізація обраної позиції: перелік одиниць ТМЦ (id, серійний номер, залишок).
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(f"Позиція: {ViewSaleState.selected_position_title}"),
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("ID ТМЦ", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                        rx.table.column_header_cell("Серійний номер", color=rx.color("accent", 2)),
                        rx.table.column_header_cell("Залишок", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                    ),
                    background_color=rx.color("accent", 9),
                ),
                rx.table.body(
                    rx.foreach(
                        ViewSaleState.selected_position_units,
                        lambda unit: rx.table.row(
                            rx.table.cell(unit[0], width="1%", white_space="nowrap"),
                            rx.table.cell(unit[1]),
                            rx.table.cell(unit[2], width="1%", white_space="nowrap"),
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
                        on_click=ViewSaleState.set_position_dialog_open(False),
                    ),
                ),
                justify="end",
                margin_top="1em",
            ),
            max_width="40em",
        ),
        open=ViewSaleState.is_position_dialog_open,
        on_open_change=ViewSaleState.set_position_dialog_open,
    )


def positions_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Позиція", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Кількість", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Ціна за одиницю", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Сума", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(
                ViewSaleState.positions,
                lambda row: rx.table.row(
                    rx.table.cell(row[1]),
                    rx.table.cell(row[2]),
                    rx.table.cell(row[3]),
                    rx.table.cell(row[4]),
                    on_click=ViewSaleState.open_position_dialog(row[0]),
                    cursor="pointer",
                    _hover={"background_color": rx.color("accent", 3)},
                ),
            ),
        ),
        variant="surface",
        width="100%",
    )


def view_body() -> rx.Component:
    return rx.vstack(
        rx.text(f"Дата: {ViewSaleState.item.movement.date}"),
        rx.text(f"Склад: {ViewSaleState.item.movement.incoming_storage.title}"),
        rx.text(f"Власник: {ViewSaleState.item.movement.incoming_owner.title}"),
        rx.text(f"Відповідальний: {ViewSaleState.item.responsible.fio}"),
        rx.text(f"Статус: {ViewSaleState.item_status}"),
        rx.text(f"Коментар: {ViewSaleState.item.movement.comment}"),
        rx.text("Продані позиції (натисніть для деталізації):", width="100%"),
        positions_table(),
        position_detail_dialog(),
        rx.hstack(
            rx.spacer(),
            rx.heading(f"Загальна вартість: {ViewSaleState.total_cost}", size="4"),
            width="100%",
        ),
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
                "Продажі/Перегляд",
                left=rx.button(
                    "Повернутись",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(routes.MOVEMENT_SALES),
                ),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.SALES_EDIT)
                        & (ViewSaleState.current_is_canceled == False),
                        rx.button(
                            "Редагувати",
                            variant="ghost",
                            size="3",
                            on_click=rx.redirect(
                                f"{routes.MOVEMENT_SALES_EDIT_ID}{ViewSaleState.item.id}"
                            ),
                        ),
                    ),
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.SALES_DELETE)
                        & (ViewSaleState.current_is_canceled == False),
                        rx.button(
                            "Скасувати",
                            color_scheme="red",
                            variant="ghost",
                            size="3",
                            on_click=SaleState.delete_one(ViewSaleState.item.id),
                        ),
                    ),
                ],
            ),
            view_body(),
            width="100%",
        ),
        value=SaleState.Pages.VIEW,
    )


def index() -> rx.Component:
    return rx.tabs.root(
        rx.cond(AppState.get_user_actions.contains(ActionEnum.SALES_LIST),
            list_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.SALES_CREATE),
            add_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.SALES_VIEW),
            view_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.SALES_EDIT),
            edit_tab_content()),
        value=SaleState.current_page,
        height="100%",
        width="100%",
    )
