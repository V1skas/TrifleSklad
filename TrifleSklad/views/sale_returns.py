import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.models import SaleReturn
from TrifleSklad.movement.list_components import filter_button, filter_card, filter_select, pagination
from TrifleSklad.states.sale_returns import (
    AddSaleReturnsState,
    EditSaleReturnsState,
    ListSaleReturnsState,
    ViewSaleReturnsState,
)
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.templates import controls, full_edit
from TrifleSklad.views.templates.history import history_block
from TrifleSklad.views.templates.layouts import (
    NESTED_DETAIL_TABLE,
    NESTED_DETAIL_TD,
    NESTED_DETAIL_TH,
    NESTED_DETAIL_THEAD,
    header_subpage,
    page_wrapper,
)


def _cancel_conflict_dialog() -> rx.Component:
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
                        ViewSaleReturnsState.cancel_conflict_rows,
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
                    rx.button(
                        "Закрити",
                        on_click=ViewSaleReturnsState.set_cancel_conflict_dialog_open(False),
                    ),
                ),
                justify="end",
                margin_top="1em",
            ),
            max_width="42em",
        ),
        open=ViewSaleReturnsState.is_cancel_conflict_dialog_open,
        on_open_change=ViewSaleReturnsState.set_cancel_conflict_dialog_open,
    )


def _view_unit_row(unit) -> rx.Component:
    return rx.el.tr(
        rx.el.td(unit[0], style={**NESTED_DETAIL_TD, "width": "1%", "white_space": "nowrap"}),
        rx.el.td(rx.cond(unit[1] != "—", rx.text(unit[1]), rx.text("—", color="gray")), style=NESTED_DETAIL_TD),
        rx.el.td(
            rx.cond(unit[2] != "—", rx.text(unit[2]), rx.text("—", color="gray")),
            style={**NESTED_DETAIL_TD, "width": "1%", "white_space": "nowrap"},
        ),
        on_click=rx.redirect(f"{routes.REPORTS_UNITS_VIEW_ID}{unit[0]}"),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 4)},
    )


def _view_units_subtable(group) -> rx.Component:
    # Сирий rx.el.table — уникаємо Radix ScrollArea, що схлопується в <td> у
    # Safari. Див. NESTED_DETAIL_* у layouts.py.
    return rx.el.table(
        rx.el.thead(
            rx.el.tr(
                rx.el.th("ID ТМЦ", style={**NESTED_DETAIL_TH, "width": "1%", "white_space": "nowrap"}),
                rx.el.th("Серійний номер", style=NESTED_DETAIL_TH),
                rx.el.th("Залишок", style={**NESTED_DETAIL_TH, "width": "1%", "white_space": "nowrap"}),
            ),
            style=NESTED_DETAIL_THEAD,
        ),
        rx.el.tbody(rx.foreach(group[4], _view_unit_row)),
        style=NESTED_DETAIL_TABLE,
    )


def _view_group_fragment(group) -> rx.Component:
    clickable = dict(
        on_click=ViewSaleReturnsState.toggle_position(group[0]),
        cursor="pointer",
    )
    return rx.fragment(
        rx.table.row(
            rx.table.cell(
                rx.icon(
                    "chevron-down",
                    size=16,
                    color=rx.color("accent", 9),
                    style={
                        "transform": rx.cond(
                            ViewSaleReturnsState.expanded_positions[group[0]],
                            "rotate(0deg)",
                            "rotate(-90deg)",
                        ),
                        "transition": "transform 0.15s",
                    },
                ),
                width="1%", white_space="nowrap", **clickable,
            ),
            rx.table.cell(group[1], **clickable),
            rx.table.cell(group[2], width="1%", white_space="nowrap", **clickable),
            rx.table.cell(group[3], width="1%", white_space="nowrap", **clickable),
            _hover={"background_color": rx.color("accent", 3)},
        ),
        rx.cond(
            ViewSaleReturnsState.expanded_positions[group[0]],
            rx.table.row(
                rx.table.cell(
                    _view_units_subtable(group),
                    custom_attrs={"colSpan": "4"},
                    padding="0.5em",
                ),
            ),
        ),
    )


def _view_positions_table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                rx.table.column_header_cell("Назва", color=rx.color("accent", 2)),
                rx.table.column_header_cell("К-сть одиниць", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                rx.table.column_header_cell("Компенсована вартість", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(rx.foreach(ViewSaleReturnsState.positions_grouped, _view_group_fragment)),
        variant="surface",
        width="100%",
    )


def view_page_content() -> rx.Component:
    return rx.vstack(
        _cancel_conflict_dialog(),
        rx.hstack(rx.text("Дата:", weight="medium"), rx.text(ViewSaleReturnsState.item.movement.date)),
        rx.hstack(
            rx.text("Вихідний продаж:", weight="medium"),
            rx.link(f"№{ViewSaleReturnsState.item.id_sale}", href=ViewSaleReturnsState.source_sale_url),
        ),
        rx.hstack(
            rx.text("Склад призначення:", weight="medium"),
            rx.text(ViewSaleReturnsState.item.movement.destination_storage.title),
        ),
        _view_positions_table(),
        rx.hstack(
            rx.spacer(),
            rx.heading(f"Загальна компенсована вартість: {ViewSaleReturnsState.total_cost}", size="4"),
            width="100%",
        ),
        rx.hstack(rx.text("Статус:", weight="medium"), rx.text(ViewSaleReturnsState.item_status)),
        rx.hstack(rx.text("Коментар:", weight="medium"), rx.text(ViewSaleReturnsState.item.movement.comment)),
        history_block(ViewSaleReturnsState),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def view_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Повернення продажу/Перегляд",
            rx.cond(
                ViewSaleReturnsState.get_user_actions.contains(Action.SALE_RETURNS_DELETE)
                & (ViewSaleReturnsState.current_is_canceled == False),
                controls.delete_with_confirm(
                    title="Підтвердження скасування",
                    trigger_label="Скасувати",
                    description="Скасувати це повернення продажу?",
                    on_confirm=ViewSaleReturnsState.on_click_cancel,
                ),
            ),
            rx.cond(
                ViewSaleReturnsState.get_user_actions.contains(Action.SALE_RETURNS_EDIT)
                & (ViewSaleReturnsState.current_is_canceled == False),
                controls.button_primary("Редагувати", on_click=ViewSaleReturnsState.on_click_edit),
            ),
            left=controls.button_back(routes.MOVEMENT_SALE_RETURNS, label="Повернутись"),
            width="100%",
        ),
        rx.skeleton(view_page_content(), loading=ViewSaleReturnsState.in_process, height="100%"),
    )


def _table_row(item: SaleReturn) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item.id)),
        rx.table.row_header_cell(item.movement.date, align="left"),
        rx.table.cell(rx.text(item.id_sale)),
        rx.table.cell(rx.text(item.movement.destination_storage.title)),
        rx.table.cell(rx.text(item.movement.total_cost)),
        rx.table.cell(rx.text(ListSaleReturnsState.get_movement_statuses[item.movement.status])),
        on_click=rx.redirect(f"{routes.MOVEMENT_SALE_RETURNS_VIEW_ID}{item.id}"),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def _table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("№", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Дата", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Продаж №", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Склад призначення", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Компенсація", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Статус", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(rx.foreach(ListSaleReturnsState.items, _table_row)),
        variant="surface",
        width="100%",
    )


def list_page_content() -> rx.Component:
    return rx.vstack(
        rx.cond(ListSaleReturnsState.has_items, _table(), controls.empty_placeholder()),
        pagination(ListSaleReturnsState),
        spacing="3",
        width="100%",
    )


@require_login
def list_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Повернення продажу",
            filter_button(ListSaleReturnsState),
            rx.cond(
                ListSaleReturnsState.get_user_actions.contains(Action.SALE_RETURNS_CREATE),
                controls.button_primary("Створити", on_click=ListSaleReturnsState.on_click_add),
            ),
            width="100%",
        ),
        rx.skeleton(list_page_content(), loading=ListSaleReturnsState.in_progress, height="100%"),
        filter_panel=filter_card(
            ListSaleReturnsState,
            filter_select(
                "Склад призначення",
                ListSaleReturnsState.filter_destination_storage,
                ListSaleReturnsState.list_warehouses,
                ListSaleReturnsState.on_change_filter_destination_storage,
            ),
        ),
        on_mount=ListSaleReturnsState.on_load,
    )


def _unit_row(state, unit, read_only) -> rx.Component:
    return rx.el.tr(
        rx.el.td(
            rx.checkbox(
                checked=state.selected_units[unit[0]],
                on_change=lambda checked: state.toggle_unit(unit[0], checked),
                disabled=read_only,
            ),
            style={**NESTED_DETAIL_TD, "width": "1%", "white_space": "nowrap"},
        ),
        rx.el.td(unit[0], style={**NESTED_DETAIL_TD, "width": "1%", "white_space": "nowrap"}),
        rx.el.td(rx.cond(unit[1] != "—", rx.text(unit[1]), rx.text("—", color="gray")), style=NESTED_DETAIL_TD),
        rx.el.td(
            rx.cond(unit[2] != "—", rx.text(unit[2]), rx.text("—", color="gray")),
            style={**NESTED_DETAIL_TD, "width": "1%", "white_space": "nowrap"},
        ),
        rx.el.td(
            controls.input_field(
                type="number",
                min=0,
                step="0.01",
                value=state.compensations[unit[0]],
                on_change=lambda v: state.set_compensation(unit[0], v),
                placeholder="Компенсація",
                disabled=read_only,
                width="11em",
            ),
            style={**NESTED_DETAIL_TD, "width": "1%", "white_space": "nowrap"},
        ),
    )


def _units_subtable(state, group, read_only) -> rx.Component:
    # Сирий rx.el.table — уникаємо Radix ScrollArea, що схлопується в <td> у
    # Safari. Див. NESTED_DETAIL_* у layouts.py.
    return rx.el.table(
        rx.el.thead(
            rx.el.tr(
                rx.el.th("", style={**NESTED_DETAIL_TH, "width": "1%", "white_space": "nowrap"}),
                rx.el.th("ID ТМЦ", style={**NESTED_DETAIL_TH, "width": "1%", "white_space": "nowrap"}),
                rx.el.th("Серійний номер", style=NESTED_DETAIL_TH),
                rx.el.th("Залишок", style={**NESTED_DETAIL_TH, "width": "1%", "white_space": "nowrap"}),
                rx.el.th("Компенсована вартість", style={**NESTED_DETAIL_TH, "width": "1%", "white_space": "nowrap"}),
            ),
            style=NESTED_DETAIL_THEAD,
        ),
        rx.el.tbody(rx.foreach(group[4], lambda unit: _unit_row(state, unit, read_only))),
        style=NESTED_DETAIL_TABLE,
    )


def _group_fragment(state, group, read_only) -> rx.Component:
    clickable = dict(
        on_click=state.toggle_catalog(group[0]),
        cursor="pointer",
    )
    return rx.fragment(
        rx.table.row(
            rx.table.cell(
                rx.icon(
                    "chevron-down",
                    size=16,
                    color=rx.color("accent", 9),
                    style={
                        "transform": rx.cond(
                            state.expanded_catalogs[group[0]],
                            "rotate(0deg)",
                            "rotate(-90deg)",
                        ),
                        "transition": "transform 0.15s",
                    },
                ),
                width="1%", white_space="nowrap", **clickable,
            ),
            rx.table.cell(group[1], **clickable),
            rx.table.cell(group[2], width="1%", white_space="nowrap", **clickable),
            rx.table.cell(group[3], width="1%", white_space="nowrap", **clickable),
            rx.table.cell(state.position_sums[group[0]], width="1%", white_space="nowrap", **clickable),
            _hover={"background_color": rx.color("accent", 3)},
        ),
        rx.cond(
            state.expanded_catalogs[group[0]],
            rx.table.row(
                rx.table.cell(
                    _units_subtable(state, group, read_only),
                    custom_attrs={"colSpan": "5"},
                    padding="0.5em",
                ),
            ),
        ),
    )


def _units_table(state, read_only) -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("", width="1%", white_space="nowrap"),
                rx.table.column_header_cell("Назва", color=rx.color("accent", 2)),
                rx.table.column_header_cell("К-сть одиниць", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                rx.table.column_header_cell("Залишок", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                rx.table.column_header_cell("Компенсація", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(rx.foreach(state.grouped_units, lambda group: _group_fragment(state, group, read_only))),
        variant="surface",
        width="100%",
    )


def _units_section(state, read_only=False) -> rx.Component:
    return rx.vstack(
        rx.heading("Одиниці до повернення:", size="3"),
        _units_table(state, read_only),
        rx.hstack(
            rx.spacer(),
            rx.heading(f"Загальна компенсована вартість: {state.total_compensation}", size="4"),
            width="100%",
        ),
        spacing="3",
        align="stretch",
        width="100%",
    )


def _sale_selector() -> rx.Component:
    return rx.cond(
        AddSaleReturnsState.sale_locked,
        rx.fragment(
            rx.text("Вихідний продаж:", weight="medium"),
            controls.input_field(value=AddSaleReturnsState.sale_label, disabled=True, width="100%"),
        ),
        rx.fragment(
            rx.text("*Продаж для повернення:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть продаж", width="100%"),
                rx.select.content(
                    rx.foreach(
                        AddSaleReturnsState.list_sales,
                        lambda s: rx.select.item(s[0], value=s[1]),
                    ),
                    width="100%",
                ),
                value=AddSaleReturnsState.selected_sale_id,
                on_change=AddSaleReturnsState.on_change_sale,
            ),
        ),
    )


def _add_form() -> rx.Component:
    return rx.vstack(
        rx.text("*Дата:", weight="medium"),
        controls.input_field(
            value=AddSaleReturnsState.current_date,
            on_change=AddSaleReturnsState.on_change_date,
            type="date",
            required=True,
            width="100%",
        ),
        _sale_selector(),
        rx.text("*Склад призначення:", weight="medium"),
        rx.select.root(
            rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
            rx.select.content(
                rx.foreach(
                    AddSaleReturnsState.list_warehouses,
                    lambda storage: rx.select.item(storage[0], value=storage[1]),
                ),
                width="100%",
            ),
            required=True,
            value=AddSaleReturnsState.id_destination_storage,
            on_change=AddSaleReturnsState.on_change_id_destination_storage,
        ),
        rx.cond(AddSaleReturnsState.has_sale, _units_section(AddSaleReturnsState)),
        rx.text("*Статус:", weight="medium"),
        rx.select(
            AddSaleReturnsState.editable_statuses,
            placeholder="Оберіть зі списку",
            required=True,
            value=AddSaleReturnsState.status,
            on_change=AddSaleReturnsState.on_change_status,
        ),
        rx.text("Коментар:", weight="medium"),
        controls.text_area_field(value=AddSaleReturnsState.comment, on_change=AddSaleReturnsState.on_change_comment, width="100%"),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def add_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Повернення продажу/Додавання",
            controls.button_primary("Зберегти", on_click=AddSaleReturnsState.add_one),
            left=controls.button_back(routes.MOVEMENT_SALE_RETURNS, label="Скасувати"),
            width="100%",
        ),
        _add_form(),
        on_mount=AddSaleReturnsState.on_load,
    )


def _edit_form() -> rx.Component:
    return rx.vstack(
        full_edit.full_edit_notice(EditSaleReturnsState),
        rx.text("*Дата:", weight="medium"),
        controls.input_field(value=EditSaleReturnsState.item.movement.date, type="date", required=True, disabled=True, width="100%"),
        rx.text("*Вихідний продаж:", weight="medium"),
        rx.select.root(
            rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
            rx.select.content(
                rx.foreach(
                    EditSaleReturnsState.list_sales,
                    lambda sale: rx.select.item(sale[0], value=sale[1], width="100%"),
                ),
                width="100%",
            ),
            required=True,
            disabled=EditSaleReturnsState.is_view_only_edit,
            value=EditSaleReturnsState.selected_sale_id,
            on_change=EditSaleReturnsState.on_change_sale,
        ),
        rx.text("*Склад призначення:", weight="medium"),
        rx.select.root(
            rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
            rx.select.content(
                rx.foreach(
                    EditSaleReturnsState.list_warehouses,
                    lambda storage: rx.select.item(storage[0], value=storage[1], width="100%"),
                ),
                width="100%",
            ),
            required=True,
            disabled=EditSaleReturnsState.is_view_only_edit,
            value=EditSaleReturnsState.id_destination_storage,
            on_change=EditSaleReturnsState.on_change_id_destination_storage,
        ),
        _units_section(EditSaleReturnsState, read_only=EditSaleReturnsState.is_view_only_edit),
        full_edit.reason_field(EditSaleReturnsState),
        rx.text("*Статус:", weight="medium"),
        rx.select(
            EditSaleReturnsState.editable_statuses,
            placeholder="Оберіть зі списку",
            required=True,
            value=EditSaleReturnsState.status,
            on_change=EditSaleReturnsState.on_change_status,
        ),
        rx.text("Коментар:", weight="medium"),
        controls.text_area_field(value=EditSaleReturnsState.item.movement.comment, on_change=EditSaleReturnsState.on_change_comment, width="100%"),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def edit_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Повернення продажу/Редагування",
            controls.button_primary("Зберегти", on_click=EditSaleReturnsState.edit_one),
            left=controls.button_back(routes.MOVEMENT_SALE_RETURNS, label="Скасувати"),
            width="100%",
        ),
        rx.skeleton(_edit_form(), loading=EditSaleReturnsState.in_process, height="100%"),
    )
