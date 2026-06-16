from typing import Tuple

import reflex as rx

from components.elements import subpage_header

from TrifleSklad import routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.models import Request
from TrifleSklad.state import AppState
from TrifleSklad.catalog.requests.backend import (
    AddRequestsState,
    EditRequestsState,
    ListRequestsState,
    ProcessRequestsState,
    RequestsState,
    ViewRequestsState,
)
from TrifleSklad.movement.products.frontend import index as products


# ----- LIST -----
def filter_card() -> rx.Component:
    return rx.cond(
        ListRequestsState.is_filter_open,
        rx.card(
            rx.vstack(
                rx.text("Статус:", size="2"),
                rx.hstack(
                    rx.foreach(
                        ListRequestsState.statuses_for_filter,
                        lambda s: rx.checkbox(
                            s[1],
                            checked=s[2],
                            on_change=lambda checked: ListRequestsState.set_status(s[0], checked),
                        ),
                    ),
                    spacing="4",
                    wrap="wrap",
                ),
                rx.hstack(
                    rx.button("Скинути", variant="soft", color_scheme="gray", on_click=ListRequestsState.reset_filters),
                    rx.button("Застосувати", on_click=ListRequestsState.apply_filters),
                    spacing="3",
                    justify="end",
                    width="100%",
                ),
                spacing="3",
                width="100%",
            ),
            width="100%",
        ),
    )


def pagination() -> rx.Component:
    return rx.hstack(
        rx.button("Назад", variant="soft", on_click=ListRequestsState.current_page_decrement),
        rx.input(
            value=ListRequestsState.get_current_page,
            on_change=ListRequestsState.on_change_current_page,
            type="number", min="1", max=ListRequestsState.get_all_pages,
            width="5em", text_align="center",
        ),
        rx.text("/"),
        rx.text(ListRequestsState.get_all_pages),
        rx.button("Вперед", variant="soft", on_click=ListRequestsState.current_page_increment),
        spacing="2", align="center", justify="center", width="100%",
    )


def list_row(item: Tuple[int, Request]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(item[1].id),
        rx.table.row_header_cell(
            item[1].date,
            align="left",
        ),
        rx.table.cell(ListRequestsState.type_titles[item[1].type]),
        rx.table.cell(
            rx.cond(
                item[1].author.worker,
                item[1].author.worker.fio,
                item[1].author.login,
            )
        ),
        rx.table.cell(ListRequestsState.status_titles[item[1].status]),
        on_click=rx.redirect(f"{routes.CATALOG_REQUESTS_VIEW_ID}{item[1].id}"),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def list_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("№", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Дата", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Тип", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Складач", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Статус", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(rx.foreach(ListRequestsState.get_items, list_row)),
        variant="surface",
        width="100%",
    )


def list_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            subpage_header(
                "Заявки",
                actions=[
                    rx.button(
                        rx.icon("filter", size=16), "Фільтр",
                        variant="ghost", size="3",
                        on_click=ListRequestsState.toggle_filter,
                    ),
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.REQUESTS_CREATE),
                        rx.button("Додати", variant="ghost", size="3",
                                  on_click=rx.redirect(routes.CATALOG_REQUESTS_ADD)),
                    ),
                ],
            ),
            filter_card(),
            rx.cond(ListRequestsState.has_items, list_table(), rx.text("Записів немає.")),
            pagination(),
            width="100%", height="100%",
        ),
        value=RequestsState.Pages.LIST,
    )


# ----- ADD / EDIT (спільна форма) -----
def position_dialog(State) -> rx.Component:
    # Модальне вікно додавання позиції ТМЦ до заявки.
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Додавання позиції"),
            rx.vstack(
                rx.text("*Найменування з каталогу:", size="2"),
                rx.select.root(
                    rx.select.trigger(placeholder="Оберіть позицію", width="100%"),
                    rx.select.content(
                        rx.foreach(State.list_catalog, lambda c: rx.select.item(c[0], value=c[1])),
                        width="100%",
                    ),
                    value=State.new_position_catalog,
                    on_change=State.on_change_new_position_catalog,
                    width="100%",
                ),
                rx.text("Кількість цілих одиниць:", size="2"),
                rx.input(
                    type="number", min="0", placeholder="Цілих", width="100%",
                    value=State.new_position_count,
                    on_change=State.on_change_new_position_count,
                ),
                # Для подільного ТМЦ — додаткове поле частини від однієї одиниці.
                rx.cond(
                    State.new_position_is_divisible,
                    rx.vstack(
                        rx.text(
                            f"Частина (1..{State.new_position_capacity - 1} {State.new_position_unit}):",
                            size="2",
                        ),
                        rx.input(
                            type="number", min="1", placeholder="Частина", width="100%",
                            value=State.new_position_part,
                            on_change=State.on_change_new_position_part,
                        ),
                        rx.text(
                            f"Ємність однієї одиниці: {State.new_position_capacity} {State.new_position_unit}.",
                            size="1", color="gray",
                        ),
                        spacing="1", width="100%", align="stretch",
                    ),
                ),
                rx.hstack(
                    rx.button("Скасувати", variant="outline", type="button",
                              on_click=State.set_position_dialog_open(False)),
                    rx.spacer(),
                    rx.button("Додати", type="button", on_click=State.add_position),
                    width="100%",
                    padding_top="0.5em",
                ),
                spacing="2",
                width="100%",
            ),
            width="28em",
        ),
        open=State.is_position_dialog_open,
        on_open_change=State.set_position_dialog_open,
    )


def positions_editor(State) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text("Позиції ТМЦ:", weight="bold"),
            rx.spacer(),
            rx.button(
                rx.icon("plus", size=16), "Додати позицію",
                type="button", variant="soft", size="2",
                on_click=State.open_position_dialog,
            ),
            width="100%", align="center",
        ),
        position_dialog(State),
        rx.cond(
            State.has_positions,
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("Позиція", color=rx.color("accent", 2)),
                        rx.table.column_header_cell("Кількість", color=rx.color("accent", 2)),
                        rx.table.column_header_cell("", color=rx.color("accent", 2), width="1%"),
                    ),
                    background_color=rx.color("accent", 9),
                ),
                rx.table.body(
                    rx.foreach(
                        State.positions_rows,
                        lambda p: rx.table.row(
                            rx.table.cell(p[1]),
                            rx.table.cell(p[2]),
                            rx.table.cell(
                                rx.button("Видалити", color_scheme="red", size="1",
                                          on_click=State.remove_position(p[0])),
                                width="1%", white_space="nowrap",
                            ),
                        ),
                    ),
                ),
                variant="surface", width="100%",
            ),
            rx.text("Позицій не додано", color="gray"),
        ),
        spacing="2", width="100%",
    )


def request_form(State) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text("*Тип заявки:"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть тип", width="100%"),
                rx.select.content(
                    rx.foreach(State.type_options, lambda t: rx.select.item(t[1], value=t[0])),
                    width="100%",
                ),
                value=State.request_type,
                on_change=State.on_change_type,
                width="100%",
            ),
            rx.cond(
                State.is_issue_type,
                rx.vstack(
                    rx.text("*Отримувач:"),
                    rx.select.root(
                        rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                        rx.select.content(
                            rx.foreach(State.list_workers, lambda w: rx.select.item(w[0], value=w[1])),
                            width="100%",
                        ),
                        value=State.id_responsible,
                        on_change=State.on_change_responsible,
                        width="100%",
                    ),
                    rx.text("*Призначення (площадка/відділ):"),
                    rx.select.root(
                        rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                        rx.select.content(
                            rx.foreach(State.list_destinations, lambda d: rx.select.item(d[0], value=d[1])),
                            width="100%",
                        ),
                        value=State.id_destination_storage,
                        on_change=State.on_change_destination,
                        width="100%",
                    ),
                    spacing="2", width="100%", align="stretch",
                ),
            ),
            positions_editor(State),
            rx.text("Коментар:"),
            rx.text_area(value=State.comment, on_change=State.on_change_comment, width="100%"),
            spacing="3", align="stretch", width="100%",
        ),
        width="100%",
    )


def add_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            subpage_header(
                "Заявки/Додавання",
                left=rx.button("Скасувати", variant="ghost", size="3",
                               on_click=rx.redirect(routes.CATALOG_REQUESTS)),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.REQUESTS_CREATE),
                        rx.button("Зберегти", variant="ghost", size="3", on_click=AddRequestsState.add_one),
                    ),
                ],
            ),
            request_form(AddRequestsState),
            width="100%",
        ),
        value=RequestsState.Pages.ADD,
    )


def edit_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            subpage_header(
                "Заявки/Редагування",
                left=rx.button("Скасувати", variant="ghost", size="3",
                               on_click=rx.redirect(f"{routes.CATALOG_REQUESTS_VIEW_ID}{EditRequestsState.item.id}")),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.REQUESTS_EDIT),
                        rx.button("Зберегти", variant="ghost", size="3", on_click=EditRequestsState.edit_one),
                    ),
                ],
            ),
            request_form(EditRequestsState),
            width="100%",
        ),
        value=RequestsState.Pages.EDIT,
    )


# ----- VIEW -----
def view_positions_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Позиція", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Кількість", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(
                ViewRequestsState.positions_rows,
                lambda r: rx.table.row(rx.table.cell(r[0]), rx.table.cell(r[1])),
            ),
        ),
        variant="surface", width="100%",
    )


def view_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            subpage_header(
                "Заявки/Перегляд",
                left=rx.button("Повернутись", variant="ghost", size="3",
                               on_click=rx.redirect(routes.CATALOG_REQUESTS)),
                actions=[
                    rx.cond(
                        ViewRequestsState.can_process,
                        rx.button("Обробити", variant="ghost", size="3", color_scheme="green",
                                  on_click=rx.redirect(f"{routes.CATALOG_REQUESTS_PROCESS_ID}{ViewRequestsState.item.id}")),
                    ),
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.REQUESTS_EDIT)
                        & (ViewRequestsState.is_completed == False),
                        rx.button("Редагувати", variant="ghost", size="3",
                                  on_click=rx.redirect(f"{routes.CATALOG_REQUESTS_EDIT_ID}{ViewRequestsState.item.id}")),
                    ),
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.REQUESTS_DELETE)
                        & (ViewRequestsState.is_completed == False),
                        rx.button("Видалити", variant="ghost", size="3", color_scheme="red",
                                  on_click=RequestsState.delete_one(ViewRequestsState.item.id)),
                    ),
                ],
            ),
            rx.vstack(
                rx.text(f"Тип: {ViewRequestsState.type_title}"),
                rx.text(f"Складач: {ViewRequestsState.author_name}"),
                rx.cond(
                    ViewRequestsState.item.type == 4,
                    rx.vstack(
                        rx.text(f"Отримувач: {ViewRequestsState.responsible_name}"),
                        rx.text(f"Призначення: {ViewRequestsState.destination_name}"),
                        spacing="2", align="stretch", width="100%",
                    ),
                ),
                rx.text(f"Статус: {ViewRequestsState.status_title}"),
                rx.text(f"Коментар: {ViewRequestsState.comment_display}"),
                rx.text("Позиції:", weight="bold"),
                view_positions_table(),
                rx.cond(
                    ViewRequestsState.is_completed,
                    rx.hstack(
                        rx.text("Сформований рух:", weight="bold"),
                        rx.link(
                            f"{ViewRequestsState.type_title} №{ViewRequestsState.item.id_movement}",
                            on_click=rx.redirect(ViewRequestsState.movement_link),
                            cursor="pointer",
                            color=rx.color("accent", 11),
                        ),
                        spacing="2",
                    ),
                ),
                spacing="3", align="stretch", width="100%",
            ),
            width="100%",
        ),
        value=RequestsState.Pages.VIEW,
    )


# ----- PROCESS -----
def process_required_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Позиція", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Потрібно", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(
                ProcessRequestsState.required_rows,
                lambda r: rx.table.row(rx.table.cell(r[0]), rx.table.cell(r[1])),
            ),
        ),
        variant="surface", width="100%",
    )


def process_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            subpage_header(
                "Заявки/Обробка",
                left=rx.button("Скасувати", variant="ghost", size="3",
                               on_click=rx.redirect(f"{routes.CATALOG_REQUESTS_VIEW_ID}{ProcessRequestsState.item.id}")),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.REQUESTS_PROCESS),
                        rx.button("Сформувати рух", variant="ghost", size="3", color_scheme="green",
                                  on_click=ProcessRequestsState.process),
                    ),
                ],
            ),
            rx.box(
                rx.vstack(
                    rx.text(f"Тип: {ProcessRequestsState.type_title}"),
                    rx.cond(
                        ProcessRequestsState.is_issue,
                        rx.vstack(
                            rx.text(f"Отримувач: {ProcessRequestsState.responsible_name}"),
                            rx.text(f"Призначення: {ProcessRequestsState.destination_name}"),
                            spacing="1", align="stretch", width="100%",
                        ),
                    ),
                    rx.text("Потрібно за заявкою:", weight="bold"),
                    process_required_table(),
                    rx.divider(),
                    rx.text("*Склад:"),
                    rx.select.root(
                        rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                        rx.select.content(
                            rx.foreach(ProcessRequestsState.list_storages,
                                       lambda s: rx.select.item(s[0], value=s[1])),
                            width="100%",
                        ),
                        value=ProcessRequestsState.id_incoming_storage,
                        on_change=ProcessRequestsState.on_change_id_incoming_storage,
                        width="100%",
                    ),
                    rx.text("*Власник:"),
                    rx.select.root(
                        rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                        rx.select.content(
                            rx.foreach(ProcessRequestsState.list_owners,
                                       lambda o: rx.select.item(o[0], value=o[1])),
                            width="100%",
                        ),
                        value=ProcessRequestsState.id_incoming_owner,
                        on_change=ProcessRequestsState.on_change_id_incoming_owner,
                        width="100%",
                    ),
                    rx.cond(
                        ProcessRequestsState.is_issue == False,
                        rx.vstack(
                            rx.text("*Відповідальний за продаж:"),
                            rx.select.root(
                                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                                rx.select.content(
                                    rx.foreach(ProcessRequestsState.list_workers,
                                               lambda w: rx.select.item(w[0], value=w[1])),
                                    width="100%",
                                ),
                                value=ProcessRequestsState.id_responsible,
                                on_change=ProcessRequestsState.on_change_id_responsible,
                                width="100%",
                            ),
                            spacing="1", align="stretch", width="100%",
                        ),
                    ),
                    products(width="100%"),
                    spacing="3", align="stretch", width="100%",
                ),
                width="100%",
            ),
            width="100%",
        ),
        value=RequestsState.Pages.PROCESS,
    )


def index() -> rx.Component:
    return rx.tabs.root(
        list_tab_content(),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.REQUESTS_CREATE), add_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.REQUESTS_EDIT), edit_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.REQUESTS_VIEW), view_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.REQUESTS_PROCESS), process_tab_content()),
        value=RequestsState.current_page,
        height="100%", width="100%",
    )
