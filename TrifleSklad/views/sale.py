from typing import Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.declared import StorageType
from TrifleSklad.models import Sale
from TrifleSklad.movement.inline_creator_components import (
    create_lookup_button,
    owner_create_dialog,
    storage_create_dialog,
    worker_create_dialog,
)
from TrifleSklad.movement.list_components import filter_button, filter_card, filter_select, pagination
from TrifleSklad.movement.products.frontend import index as products_widget
from TrifleSklad.states.sale import (
    AddSaleState,
    EditSaleState,
    ListSaleState,
    ViewSaleState,
)
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.templates import controls, full_edit
from TrifleSklad.views.templates.history import history_block
from TrifleSklad.views.templates.layouts import (
    NESTED_DETAIL_TABLE,
    NESTED_DETAIL_TD,
    NESTED_DETAIL_TH,
    NESTED_DETAIL_THEAD,
    field_row,
    header_subpage,
    page_wrapper,
    titled_section,
)


def _table_row(item: Tuple[int, Sale]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item[1].id)),
        rx.table.row_header_cell(item[1].movement.date, align="left"),
        rx.table.cell(rx.text(item[1].movement.incoming_storage.title)),
        rx.table.cell(rx.text(item[1].responsible.fio)),
        rx.table.cell(rx.text(item[1].movement.total_cost)),
        rx.table.cell(rx.text(ListSaleState.get_movement_statuses[item[1].movement.status])),
        on_click=rx.redirect(f"{routes.MOVEMENT_SALES_VIEW_ID}{item[1].id}"),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def _table() -> rx.Component:
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
        rx.table.body(rx.foreach(ListSaleState.get_items, _table_row)),
        variant="surface",
        width="100%",
    )


def list_page_content() -> rx.Component:
    return rx.vstack(
        rx.cond(ListSaleState.has_items, _table(), controls.empty_placeholder()),
        pagination(ListSaleState),
        spacing="3",
        width="100%",
    )


@require_login
def list_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Продажі",
            filter_button(ListSaleState),
            rx.cond(
                ListSaleState.get_user_actions.contains(Action.SALES_CREATE),
                controls.button_primary("Створити", on_click=ListSaleState.on_click_add),
            ),
            width="100%",
        ),
        rx.skeleton(list_page_content(), loading=ListSaleState.in_progress, height="100%"),
        filter_panel=filter_card(
            ListSaleState,
            filter_select(
                "Склад",
                ListSaleState.filter_incoming_storage,
                ListSaleState.list_warehouses,
                ListSaleState.on_change_filter_incoming_storage,
            ),
            filter_select(
                "Власник",
                ListSaleState.filter_incoming_owner,
                ListSaleState.list_owners,
                ListSaleState.on_change_filter_incoming_owner,
            ),
            filter_select(
                "Відповідальний",
                ListSaleState.filter_responsible,
                ListSaleState.list_responsibles,
                ListSaleState.on_change_filter_responsible,
            ),
        ),
        on_mount=ListSaleState.on_load,
    )


def _request_picker() -> rx.Component:
    return rx.cond(
        AddSaleState.get_user_actions.contains(Action.REQUESTS_PROCESS)
        & AddSaleState.has_requests,
        rx.vstack(
            rx.text("Заявка (необов'язково):", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Без заявки", width="100%"),
                rx.select.content(
                    rx.foreach(
                        AddSaleState.list_requests,
                        lambda r: rx.select.item(r[0], value=r[1]),
                    ),
                    width="100%",
                ),
                value=AddSaleState.selected_request_id,
                on_change=AddSaleState.on_change_request,
                width="100%",
            ),
            rx.cond(
                AddSaleState.has_request_positions,
                rx.vstack(
                    rx.text("Потрібно за заявкою:", weight="bold", size="2"),
                    rx.foreach(
                        AddSaleState.request_positions,
                        lambda p: rx.text(f"• {p[0]} — {p[1]}", size="2"),
                    ),
                    spacing="1",
                    align="stretch",
                    width="100%",
                ),
            ),
            rx.divider(),
            spacing="2",
            align="stretch",
            width="100%",
        ),
    )


def _add_form() -> rx.Component:
    return rx.vstack(
        titled_section(
            "Загальна інформація",
            _request_picker(),
            rx.text("*Дата:", weight="medium"),
            controls.input_field(
                value=AddSaleState.current_date,
                on_change=AddSaleState.on_change_date,
                type="date",
                required=True,
                width="100%",
            ),
            rx.text("*Склад:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.vstack(
                        controls.search_field(
                            value=AddSaleState.search_name_incoming_storage,
                            on_change=AddSaleState.on_change_search_name_incoming_storage,
                            placeholder="Введіть назву для пошуку",
                            width="100%",
                        ),
                        rx.foreach(
                            AddSaleState.list_storages,
                            lambda storage: rx.select.item(storage[0], value=storage[1], width="100%"),
                        ),
                        width="100%",
                    ),
                    width="100%",
                ),
                required=True,
                value=AddSaleState.id_incoming_storage,
                on_change=AddSaleState.on_change_id_incoming_storage,
            ),
            create_lookup_button(
                Action.STORAGE_CREATE,
                "Створити склад",
                AddSaleState.open_storage_create(StorageType.WAREHOUSE, "incoming", False),
            ),
            storage_create_dialog(AddSaleState),
            rx.text("*Власник:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
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
            create_lookup_button(Action.OWNERS_CREATE, "Створити власника", AddSaleState.open_owner_create("")),
            owner_create_dialog(AddSaleState),
            rx.text("*Відповідальний:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    controls.input_field(
                        rx.input.slot(rx.icon("search")),
                        placeholder="Пошук за ПІБ",
                        value=AddSaleState.search_responsible,
                        on_change=AddSaleState.on_change_search_responsible,
                        width="100%",
                        margin_bottom="0.5em",
                    ),
                    rx.foreach(
                        AddSaleState.filtered_list_workers,
                        lambda worker: rx.select.item(worker[0], value=worker[1]),
                    ),
                    width="100%",
                ),
                required=True,
                value=AddSaleState.id_responsible,
                on_change=AddSaleState.on_change_id_responsible,
            ),
            create_lookup_button(Action.WORKERS_CREATE, "Створити співробітника", AddSaleState.open_worker_create),
            worker_create_dialog(AddSaleState),
            rx.text("*Статус:", weight="medium"),
            rx.select(
                AddSaleState.editable_statuses,
                placeholder="Оберіть зі списку",
                required=True,
                value=AddSaleState.status,
                on_change=AddSaleState.on_change_status,
            ),
            rx.text("Коментар:", weight="medium"),
            controls.text_area_field(value=AddSaleState.comment, on_change=AddSaleState.on_change_comment, width="100%"),
            rx.text("Інформація про клієнта:", weight="medium"),
            controls.text_area_field(value=AddSaleState.client_info, on_change=AddSaleState.on_change_client_info, width="100%"),
        ),
        titled_section("Товари", products_widget(width="100%")),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def add_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Продажі/Додавання",
            controls.button_secondary("Зберегти і продовжити", on_click=AddSaleState.add_one(True)),
            controls.button_primary("Зберегти", on_click=AddSaleState.add_one(False)),
            left=controls.button_back(routes.MOVEMENT_SALES, label="Скасувати"),
            width="100%",
        ),
        _add_form(),
        on_mount=AddSaleState.on_load,
    )


def _edit_form() -> rx.Component:
    return rx.vstack(
        full_edit.full_edit_notice(EditSaleState),
        full_edit.save_reason_dialog(EditSaleState),
        titled_section(
            "Загальна інформація",
            rx.cond(
                EditSaleState.has_source_request,
                rx.hstack(
                    rx.text("Рух сформовано за заявкою", size="2", color=rx.color("gray", 11)),
                    rx.link(
                        f"№{EditSaleState.source_request_id}",
                        href=f"{routes.CATALOG_REQUESTS_VIEW_ID}{EditSaleState.source_request_id}",
                        size="2",
                    ),
                    spacing="1",
                    align="center",
                ),
            ),
            rx.text("*Дата:", weight="medium"),
            controls.input_field(value=EditSaleState.item.movement.date, type="date", required=True, disabled=True, width="100%"),
            rx.text("*Склад:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(
                        EditSaleState.list_storages,
                        lambda storage: rx.select.item(storage[0], value=storage[1], width="100%"),
                    ),
                    width="100%",
                ),
                required=True,
                disabled=EditSaleState.is_view_only_edit,
                value=EditSaleState.id_incoming_storage,
                on_change=EditSaleState.on_change_id_incoming_storage,
            ),
            rx.text("*Власник:", weight="medium"),
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
                disabled=EditSaleState.is_view_only_edit,
                value=EditSaleState.id_incoming_owner,
                on_change=EditSaleState.on_change_id_incoming_owner,
            ),
            rx.text("*Відповідальний:", weight="medium"),
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
                disabled=EditSaleState.is_view_only_edit,
                value=EditSaleState.id_responsible,
                on_change=EditSaleState.on_change_id_responsible,
            ),
            rx.text("*Статус:", weight="medium"),
            rx.select(
                EditSaleState.editable_statuses,
                placeholder="Оберіть зі списку",
                required=True,
                value=EditSaleState.status,
                on_change=EditSaleState.on_change_status,
            ),
            rx.text("Коментар:", weight="medium"),
            controls.text_area_field(value=EditSaleState.item.movement.comment, on_change=EditSaleState.on_change_comment, width="100%"),
            rx.text("Інформація про клієнта:", weight="medium"),
            controls.text_area_field(value=EditSaleState.client_info, on_change=EditSaleState.on_change_client_info, width="100%"),
        ),
        titled_section("Товари", products_widget(width="100%")),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def edit_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Продажі/Редагування",
            controls.button_primary("Зберегти", on_click=EditSaleState.open_save_dialog),
            left=controls.button_back(routes.MOVEMENT_SALES, label="Скасувати"),
            width="100%",
        ),
        rx.skeleton(_edit_form(), loading=EditSaleState.in_process, height="100%"),
    )


def _cancel_conflict_dialog() -> rx.Component:
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
                            rx.table.cell(row[2]),
                            rx.table.cell(row[3]),
                            on_click=rx.redirect(row[4]),
                            cursor="pointer",
                            _hover={"background_color": rx.color("accent", 3)},
                        ),
                    ),
                ),
                variant="surface",
                width="100%",
                margin_top="1em",
            ),
            rx.flex(
                rx.dialog.close(
                    rx.button("Закрити", on_click=ViewSaleState.set_cancel_conflict_dialog_open(False)),
                ),
                justify="end",
                margin_top="1em",
            ),
            max_width="42em",
        ),
        open=ViewSaleState.is_cancel_conflict_dialog_open,
        on_open_change=ViewSaleState.set_cancel_conflict_dialog_open,
    )


def _position_units_subtable(group) -> rx.Component:
    # Сирий rx.el.table (не rx.table.root) — щоб уникнути Radix ScrollArea, що
    # схлопується всередині <td> у Safari. Див. NESTED_DETAIL_* у layouts.py.
    return rx.el.table(
        rx.el.thead(
            rx.el.tr(
                rx.el.th("ID ТМЦ", style={**NESTED_DETAIL_TH, "width": "1%", "white_space": "nowrap"}),
                rx.el.th("Серійний номер", style=NESTED_DETAIL_TH),
                rx.el.th("Залишок", style={**NESTED_DETAIL_TH, "width": "1%", "white_space": "nowrap"}),
                rx.el.th("Облік", style={**NESTED_DETAIL_TH, "width": "1%", "white_space": "nowrap"}),
            ),
            style=NESTED_DETAIL_THEAD,
        ),
        rx.el.tbody(
            rx.foreach(
                group[5],
                lambda unit: rx.el.tr(
                    rx.el.td(unit[0], style={**NESTED_DETAIL_TD, "width": "1%", "white_space": "nowrap"}),
                    rx.el.td(unit[1], style=NESTED_DETAIL_TD),
                    rx.el.td(unit[2], style={**NESTED_DETAIL_TD, "width": "1%", "white_space": "nowrap"}),
                    rx.el.td(
                        rx.cond(
                            unit[3],
                            rx.badge("Поза обліком", color_scheme="orange", size="1", variant="soft"),
                            rx.text("—", color="gray"),
                        ),
                        style={**NESTED_DETAIL_TD, "width": "1%", "white_space": "nowrap"},
                    ),
                    on_click=rx.redirect(f"{routes.REPORTS_UNITS_VIEW_ID}{unit[0]}"),
                    cursor="pointer",
                    _hover={"background_color": rx.color("accent", 4)},
                ),
            ),
        ),
        style=NESTED_DETAIL_TABLE,
    )


def _position_group(group) -> rx.Component:
    clickable = dict(
        on_click=ViewSaleState.toggle_position(group[0]),
        cursor="pointer",
    )
    expanded = ViewSaleState.expanded_positions[group[0]]
    return rx.fragment(
        rx.table.row(
            rx.table.cell(
                rx.icon(
                    "chevron-down",
                    size=16,
                    color=rx.color("accent", 9),
                    style={
                        "transform": rx.cond(expanded, "rotate(0deg)", "rotate(-90deg)"),
                        "transition": "transform 0.15s",
                    },
                ),
                width="1%", white_space="nowrap", **clickable,
            ),
            rx.table.cell(group[1], **clickable),
            rx.table.cell(group[2], width="1%", white_space="nowrap", **clickable),
            rx.table.cell(group[3], width="1%", white_space="nowrap", **clickable),
            rx.table.cell(group[4], width="1%", white_space="nowrap", **clickable),
            _hover={"background_color": rx.color("accent", 3)},
        ),
        rx.cond(
            expanded,
            rx.table.row(
                rx.table.cell(
                    _position_units_subtable(group),
                    custom_attrs={"colSpan": "5"},
                    padding="0.5em",
                ),
            ),
        ),
    )


def _positions_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                rx.table.column_header_cell("Позиція", color=rx.color("accent", 2)),
                rx.table.column_header_cell("К-сть одиниць", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                rx.table.column_header_cell("Ціна за од.", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                rx.table.column_header_cell("Сума", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(rx.foreach(ViewSaleState.positions_grouped, _position_group)),
        variant="surface",
        width="100%",
    )


def view_page_content() -> rx.Component:
    return rx.vstack(
        _cancel_conflict_dialog(),
        titled_section(
            "Загальна інформація",
            field_row("Дата", ViewSaleState.item.movement.date),
            field_row("Склад", ViewSaleState.item.movement.incoming_storage.title),
            field_row("Власник", ViewSaleState.item.movement.incoming_owner.title),
            field_row("Відповідальний", ViewSaleState.item.responsible.fio),
            field_row("Статус", ViewSaleState.item_status),
            field_row("Коментар", ViewSaleState.item.movement.comment),
            field_row("Інформація про клієнта", ViewSaleState.client_info),
        ),
        titled_section(
            "Товари",
            rx.text("Продані позиції (натисніть для деталізації):", width="100%"),
            _positions_table(),
            rx.hstack(
                rx.spacer(),
                rx.heading(f"Загальна вартість: {ViewSaleState.total_cost}", size="4"),
                width="100%",
            ),
        ),
        history_block(ViewSaleState),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def view_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Продажі/Перегляд",
            rx.cond(
                ViewSaleState.get_user_actions.contains(Action.SALE_RETURNS_CREATE)
                & (ViewSaleState.current_is_canceled == False),
                controls.button_secondary(
                    "Оформити повернення",
                    on_click=rx.redirect(f"{routes.MOVEMENT_SALE_RETURNS_ADD}{ViewSaleState.item.id}"),
                ),
            ),
            rx.cond(
                ViewSaleState.get_user_actions.contains(Action.SALES_DELETE)
                & (ViewSaleState.current_is_canceled == False),
                controls.cancel_with_reason(
                    open=ViewSaleState.is_cancel_reason_dialog_open,
                    on_open_change=ViewSaleState.set_cancel_reason_dialog_open,
                    value=ViewSaleState.cancel_reason,
                    on_change=ViewSaleState.on_change_cancel_reason,
                    on_open_trigger=ViewSaleState.open_cancel_reason_dialog,
                    on_confirm=ViewSaleState.confirm_cancel,
                    title="Підтвердження скасування",
                    trigger_label="Скасувати",
                    description="Скасувати цей продаж? Товар буде повернено у залишки.",
                ),
            ),
            rx.cond(
                ViewSaleState.get_user_actions.contains(Action.SALES_EDIT)
                & (ViewSaleState.current_is_canceled == False),
                controls.button_primary("Редагувати", on_click=ViewSaleState.on_click_edit),
            ),
            left=controls.button_back(routes.MOVEMENT_SALES, label="Повернутись"),
            width="100%",
        ),
        rx.skeleton(view_page_content(), loading=ViewSaleState.in_process, height="100%"),
    )
