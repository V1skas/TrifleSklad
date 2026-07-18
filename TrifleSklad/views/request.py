from typing import Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.models import Request
from TrifleSklad.movement.products.frontend import index as products
from TrifleSklad.states.request import (
    AddRequestsState,
    EditRequestsState,
    ListRequestsState,
    ProcessRequestsState,
    ViewRequestsState,
)
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.templates import controls
from TrifleSklad.views.templates.layouts import header_subpage, page_wrapper


# ----- LIST -----
def _filter_card() -> rx.Component:
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


def _pagination() -> rx.Component:
    return rx.hstack(
        rx.button("Назад", variant="soft", on_click=ListRequestsState.current_page_decrement),
        controls.input_field(
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


def _list_row(item: Tuple[int, Request]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(item[1].id),
        rx.table.row_header_cell(item[1].date, align="left"),
        rx.table.cell(ListRequestsState.type_titles[item[1].type]),
        rx.table.cell(rx.cond(item[1].author.worker, item[1].author.worker.fio, item[1].author.login)),
        rx.table.cell(ListRequestsState.status_titles[item[1].status]),
        on_click=rx.redirect(routes.CATALOG_REQUESTS_VIEW_ID + item[1].id.to_string()),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def _list_table() -> rx.Component:
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
        rx.table.body(rx.foreach(ListRequestsState.get_items, _list_row)),
        variant="surface",
        width="100%",
    )


def list_page_content() -> rx.Component:
    return rx.vstack(
        _filter_card(),
        rx.cond(ListRequestsState.has_items, _list_table(), controls.empty_placeholder()),
        _pagination(),
        spacing="3",
        width="100%",
    )


@require_login
def list_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Заявки",
            rx.button(rx.icon("filter", size=16), "Фільтр", variant="ghost", size="3", on_click=ListRequestsState.toggle_filter),
            rx.cond(
                ListRequestsState.get_user_actions.contains(ActionEnum.REQUESTS_CREATE),
                rx.button("Додати", variant="ghost", size="3", on_click=ListRequestsState.on_click_add),
            ),
            width="100%",
        ),
        list_page_content(),
        on_mount=ListRequestsState.on_load,
    )


# ----- ADD / EDIT (спільна форма) -----
def _position_dialog(state) -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Додавання позиції"),
            rx.vstack(
                rx.text("*Найменування з каталогу:", size="2"),
                rx.select.root(
                    rx.select.trigger(placeholder="Оберіть позицію", width="100%"),
                    rx.select.content(
                        rx.foreach(state.list_catalog, lambda c: rx.select.item(c[0], value=c[1])),
                        width="100%",
                    ),
                    value=state.new_position_catalog,
                    on_change=state.set_new_position_catalog,
                    width="100%",
                ),
                rx.text("Кількість цілих одиниць:", size="2"),
                controls.input_field(
                    type="number", min="0", placeholder="Цілих", width="100%",
                    value=state.new_position_count,
                    on_change=state.set_new_position_count,
                ),
                rx.cond(
                    state.new_position_is_divisible,
                    rx.vstack(
                        rx.text(f"Частина (1..{state.new_position_capacity - 1} {state.new_position_unit}):", size="2"),
                        controls.input_field(
                            type="number", min="1", placeholder="Частина", width="100%",
                            value=state.new_position_part,
                            on_change=state.set_new_position_part,
                        ),
                        rx.text(f"Ємність однієї одиниці: {state.new_position_capacity} {state.new_position_unit}.", size="1", color="gray"),
                        spacing="1", width="100%", align="stretch",
                    ),
                ),
                rx.hstack(
                    rx.button("Скасувати", variant="outline", type="button", on_click=state.set_position_dialog_open(False)),
                    rx.spacer(),
                    rx.button("Додати", type="button", on_click=state.add_position),
                    width="100%",
                    padding_top="0.5em",
                ),
                spacing="2",
                width="100%",
            ),
            width="28em",
        ),
        open=state.is_position_dialog_open,
        on_open_change=state.set_position_dialog_open,
    )


def _positions_editor(state) -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text("Позиції ТМЦ:", weight="bold"),
            rx.spacer(),
            rx.button(rx.icon("plus", size=16), "Додати позицію", type="button", variant="soft", size="2", on_click=state.open_position_dialog),
            width="100%", align="center",
        ),
        _position_dialog(state),
        rx.cond(
            state.has_positions,
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
                        state.positions_rows,
                        lambda p: rx.table.row(
                            rx.table.cell(p[1]),
                            rx.table.cell(p[2]),
                            rx.table.cell(
                                rx.button("Видалити", color_scheme="red", size="1", on_click=state.remove_position(p[0])),
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


def _request_form(state) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text("*Тип заявки:"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть тип", width="100%"),
                rx.select.content(rx.foreach(state.type_options, lambda t: rx.select.item(t[1], value=t[0])), width="100%"),
                value=state.request_type,
                on_change=state.set_request_type,
                width="100%",
            ),
            rx.cond(
                state.is_issue_type,
                rx.vstack(
                    rx.text("*Отримувач:"),
                    rx.select.root(
                        rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                        rx.select.content(rx.foreach(state.list_workers, lambda w: rx.select.item(w[0], value=w[1])), width="100%"),
                        value=state.id_responsible,
                        on_change=state.set_id_responsible,
                        width="100%",
                    ),
                    rx.text("*Призначення (площадка/відділ):"),
                    rx.select.root(
                        rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                        rx.select.content(rx.foreach(state.list_destinations, lambda d: rx.select.item(d[0], value=d[1])), width="100%"),
                        value=state.id_destination_storage,
                        on_change=state.set_id_destination_storage,
                        width="100%",
                    ),
                    spacing="2", width="100%", align="stretch",
                ),
            ),
            _positions_editor(state),
            rx.text("Коментар:"),
            controls.text_area_field(value=state.comment, on_change=state.set_comment, width="100%"),
            spacing="3", align="stretch", width="100%",
        ),
        width="100%",
    )


@require_login
def add_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Заявки/Додавання",
            rx.cond(
                AddRequestsState.get_user_actions.contains(ActionEnum.REQUESTS_CREATE),
                rx.button("Зберегти", variant="ghost", size="3", on_click=AddRequestsState.on_save),
            ),
            left=controls.button_back(routes.CATALOG_REQUESTS, label="Скасувати"),
            width="100%",
        ),
        _request_form(AddRequestsState),
        on_mount=AddRequestsState.on_load,
    )


@require_login
def edit_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Заявки/Редагування",
            rx.cond(
                EditRequestsState.get_user_actions.contains(ActionEnum.REQUESTS_EDIT),
                rx.button("Зберегти", variant="ghost", size="3", on_click=EditRequestsState.on_save),
            ),
            left=controls.button_back(routes.CATALOG_REQUESTS, label="Скасувати"),
            width="100%",
        ),
        _request_form(EditRequestsState),
    )


# ----- VIEW -----
def _view_positions_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Позиція", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Кількість", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(rx.foreach(ViewRequestsState.positions_rows, lambda r: rx.table.row(rx.table.cell(r[0]), rx.table.cell(r[1])))),
        variant="surface", width="100%",
    )


def view_page_content() -> rx.Component:
    return rx.vstack(
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
        _view_positions_table(),
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
    )


@require_login
def view_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Заявки/Перегляд",
            rx.cond(
                ViewRequestsState.can_process,
                rx.button("Обробити", variant="ghost", size="3", color_scheme="green", on_click=ViewRequestsState.on_click_process),
            ),
            rx.cond(
                ViewRequestsState.get_user_actions.contains(ActionEnum.REQUESTS_EDIT) & (ViewRequestsState.is_completed == False),
                rx.button("Редагувати", variant="ghost", size="3", on_click=ViewRequestsState.on_click_edit),
            ),
            rx.cond(
                ViewRequestsState.get_user_actions.contains(ActionEnum.REQUESTS_DELETE) & (ViewRequestsState.is_completed == False),
                controls.delete_with_confirm(
                    on_confirm=ViewRequestsState.on_click_delete,
                    trigger=rx.button("Видалити", variant="ghost", size="3", color_scheme="red"),
                ),
            ),
            left=controls.button_back(routes.CATALOG_REQUESTS, label="Повернутись"),
            width="100%",
        ),
        rx.skeleton(view_page_content(), loading=ViewRequestsState.in_process, height="100%"),
    )


# ----- PROCESS -----
def _process_required_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Позиція", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Потрібно", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(rx.foreach(ProcessRequestsState.required_rows, lambda r: rx.table.row(rx.table.cell(r[0]), rx.table.cell(r[1])))),
        variant="surface", width="100%",
    )


def process_page_content() -> rx.Component:
    return rx.box(
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
            _process_required_table(),
            rx.divider(),
            rx.text("*Склад:"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(rx.foreach(ProcessRequestsState.list_storages, lambda s: rx.select.item(s[0], value=s[1])), width="100%"),
                value=ProcessRequestsState.id_incoming_storage,
                on_change=ProcessRequestsState.set_id_incoming_storage,
                width="100%",
            ),
            rx.text("*Власник:"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(rx.foreach(ProcessRequestsState.list_owners, lambda o: rx.select.item(o[0], value=o[1])), width="100%"),
                value=ProcessRequestsState.id_incoming_owner,
                on_change=ProcessRequestsState.set_id_incoming_owner,
                width="100%",
            ),
            rx.cond(
                ProcessRequestsState.is_issue == False,
                rx.vstack(
                    rx.text("*Відповідальний за продаж:"),
                    rx.select.root(
                        rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                        rx.select.content(rx.foreach(ProcessRequestsState.list_workers, lambda w: rx.select.item(w[0], value=w[1])), width="100%"),
                        value=ProcessRequestsState.id_responsible,
                        on_change=ProcessRequestsState.set_id_responsible,
                        width="100%",
                    ),
                    spacing="1", align="stretch", width="100%",
                ),
            ),
            products(width="100%"),
            spacing="3", align="stretch", width="100%",
        ),
        width="100%",
    )


@require_login
def process_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Заявки/Обробка",
            rx.cond(
                ProcessRequestsState.get_user_actions.contains(ActionEnum.REQUESTS_PROCESS),
                rx.button("Сформувати рух", variant="ghost", size="3", color_scheme="green", on_click=ProcessRequestsState.process),
            ),
            left=controls.button_back(routes.CATALOG_REQUESTS, label="Повернутись"),
            width="100%",
        ),
        rx.skeleton(process_page_content(), loading=ProcessRequestsState.in_process, height="100%"),
    )
