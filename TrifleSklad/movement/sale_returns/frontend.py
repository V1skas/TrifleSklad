import reflex as rx

from components.elements import subpage_header

from TrifleSklad import routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.movement.sale_returns.backend import (
    AddSaleReturnsState,
    EditSaleReturnsState,
    ListSaleReturnsState,
    SaleReturnsState,
    ViewSaleReturnsState,
)
from TrifleSklad.movement.list_components import (
    filter_button,
    filter_card,
    filter_select,
    pagination,
)

from TrifleSklad.models import SaleReturn
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
                        on_click=ViewSaleReturnsState.set_cancel_conflict_dialog_open(
                            False
                        ),
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


# View
# ======================
def view_unit_row(unit) -> rx.Component:
    # unit = (id одиниці, серійний номер|'—', залишок|'—').
    # Клік по рядку → детальна сторінка одиниці ТМЦ.
    return rx.table.row(
        rx.table.cell(unit[0], width="1%", white_space="nowrap"),
        rx.table.cell(
            rx.cond(unit[1] != "—", rx.text(unit[1]), rx.text("—", color="gray")),
        ),
        rx.table.cell(
            rx.cond(unit[2] != "—", rx.text(unit[2]), rx.text("—", color="gray")),
            width="1%", white_space="nowrap",
        ),
        on_click=rx.redirect(f"{routes.REPORTS_UNITS_VIEW_ID}{unit[0]}"),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 4)},
    )


def view_units_subtable(group) -> rx.Component:
    # group[4] — перелік одиниць позиції каталогу.
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("ID ТМЦ", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                rx.table.column_header_cell("Серійний номер", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Залишок", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
            ),
            background_color=rx.color("accent", 6),
        ),
        rx.table.body(rx.foreach(group[4], view_unit_row)),
        variant="surface",
        width="100%",
    )


def view_group_fragment(group) -> rx.Component:
    # group = (індекс, назва, к-сть, компенсація, одиниці).
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
                    view_units_subtable(group),
                    custom_attrs={"colSpan": "4"},
                    padding="0.5em",
                ),
            ),
        ),
    )


def view_positions_table() -> rx.Component:
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
        rx.table.body(
            rx.foreach(ViewSaleReturnsState.positions_grouped, view_group_fragment),
        ),
        variant="surface",
        width="100%",
    )


def item_preview() -> rx.Component:
    return rx.vstack(
        rx.hstack(rx.text("Дата:"), rx.text(ViewSaleReturnsState.item.movement.date)),
        rx.hstack(
            rx.text("Вихідний продаж:"),
            rx.link(
                f"№{ViewSaleReturnsState.item.id_sale}",
                href=ViewSaleReturnsState.source_sale_url,
            ),
        ),
        rx.hstack(
            rx.text("Склад призначення:"),
            rx.text(ViewSaleReturnsState.item.movement.destination_storage.title),
        ),
        view_positions_table(),
        rx.hstack(
            rx.spacer(),
            rx.heading(
                f"Загальна компенсована вартість: {ViewSaleReturnsState.total_cost}",
                size="4",
            ),
            width="100%",
        ),
        rx.hstack(rx.text("Статус:"), rx.text(ViewSaleReturnsState.item_status)),
        rx.hstack(rx.text("Коментар:"), rx.text(ViewSaleReturnsState.item.movement.comment)),
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
                "Повернення продажу/Перегляд",
                left=rx.button(
                    "Повернутись",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(routes.MOVEMENT_SALE_RETURNS),
                ),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.SALE_RETURNS_EDIT)
                        & (ViewSaleReturnsState.current_is_canceled == False),
                        rx.button(
                            "Редагувати",
                            variant="ghost",
                            size="3",
                            on_click=rx.redirect(
                                f"{routes.MOVEMENT_SALE_RETURNS_EDIT_ID}{ViewSaleReturnsState.item.id}"
                            ),
                        ),
                    ),
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.SALE_RETURNS_DELETE)
                        & (ViewSaleReturnsState.current_is_canceled == False),
                        rx.button(
                            "Скасувати",
                            color_scheme="red",
                            variant="ghost",
                            size="3",
                            on_click=SaleReturnsState.delete_one,
                        ),
                    ),
                ],
            ),
            item_preview(),
            width="100%",
        ),
        value=SaleReturnsState.Pages.VIEW,
    )
# ======================


# List
# ======================
def table_row(item: SaleReturn) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item.id)),
        rx.table.row_header_cell(item.movement.date, align="left"),
        rx.table.cell(rx.text(item.id_sale)),
        rx.table.cell(rx.text(item.movement.destination_storage.title)),
        rx.table.cell(rx.text(item.movement.total_cost)),
        rx.table.cell(
            rx.text(ListSaleReturnsState.get_movement_statuses[item.movement.status])
        ),
        on_click=rx.redirect(f"{routes.MOVEMENT_SALE_RETURNS_VIEW_ID}{item.id}"),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def table() -> rx.Component:
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
        rx.table.body(
            rx.foreach(ListSaleReturnsState.items, table_row),
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
                "Повернення продажу",
                actions=[
                    filter_button(ListSaleReturnsState),
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.SALE_RETURNS_CREATE),
                        rx.button(
                            "Додати",
                            variant="ghost",
                            size="3",
                            on_click=rx.redirect(routes.MOVEMENT_SALE_RETURNS_ADD),
                        ),
                    ),
                ],
            ),
            filter_card(
                ListSaleReturnsState,
                filter_select(
                    "Склад призначення",
                    ListSaleReturnsState.filter_destination_storage,
                    ListSaleReturnsState.list_warehouses,
                    ListSaleReturnsState.on_change_filter_destination_storage,
                ),
            ),
            rx.cond(ListSaleReturnsState.has_items, table(), rx.text("Записів немає.")),
            pagination(ListSaleReturnsState),
            width="100%",
            height="100%",
        ),
        value=SaleReturnsState.Pages.LIST,
    )
# ======================


# Add
# ======================
def unit_row(unit) -> rx.Component:
    # unit = (id одиниці, серійний номер|'—', залишок|'—').
    return rx.table.row(
        rx.table.cell(
            rx.checkbox(
                checked=AddSaleReturnsState.selected_units[unit[0]],
                on_change=lambda checked: AddSaleReturnsState.toggle_unit(unit[0], checked),
            ),
            width="1%", white_space="nowrap",
        ),
        rx.table.cell(unit[0], width="1%", white_space="nowrap"),
        rx.table.cell(
            rx.cond(unit[1] != "—", rx.text(unit[1]), rx.text("—", color="gray")),
        ),
        rx.table.cell(
            rx.cond(unit[2] != "—", rx.text(unit[2]), rx.text("—", color="gray")),
            width="1%", white_space="nowrap",
        ),
        rx.table.cell(
            rx.input(
                type="number",
                min=0,
                step="0.01",
                value=AddSaleReturnsState.compensations[unit[0]],
                on_change=lambda v: AddSaleReturnsState.set_compensation(unit[0], v),
                placeholder="Компенсація",
                size="1",
                width="11em",
            ),
            width="1%", white_space="nowrap",
        ),
    )


def units_subtable(group) -> rx.Component:
    # group[4] — перелік одиниць позиції каталогу.
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                rx.table.column_header_cell("ID ТМЦ", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                rx.table.column_header_cell("Серійний номер", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Залишок", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                rx.table.column_header_cell("Компенсована вартість", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
            ),
            background_color=rx.color("accent", 6),
        ),
        rx.table.body(rx.foreach(group[4], unit_row)),
        variant="surface",
        width="100%",
    )


def group_fragment(group) -> rx.Component:
    # group = (id каталогу, назва, к-сть одиниць, залишок|'—', одиниці).
    clickable = dict(
        on_click=AddSaleReturnsState.toggle_catalog(group[0]),
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
                            AddSaleReturnsState.expanded_catalogs[group[0]],
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
            rx.table.cell(
                AddSaleReturnsState.position_sums[group[0]],
                width="1%", white_space="nowrap", **clickable,
            ),
            _hover={"background_color": rx.color("accent", 3)},
        ),
        rx.cond(
            AddSaleReturnsState.expanded_catalogs[group[0]],
            rx.table.row(
                rx.table.cell(
                    units_subtable(group),
                    custom_attrs={"colSpan": "5"},
                    padding="0.5em",
                ),
            ),
        ),
    )


def units_table() -> rx.Component:
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
        rx.table.body(rx.foreach(AddSaleReturnsState.grouped_units, group_fragment)),
        variant="surface",
        width="100%",
    )


def units_section() -> rx.Component:
    return rx.cond(
        AddSaleReturnsState.has_sale,
        rx.vstack(
            rx.heading("Одиниці до повернення:", size="3"),
            units_table(),
            rx.hstack(
                rx.spacer(),
                rx.heading(
                    f"Загальна компенсована вартість: {AddSaleReturnsState.total_compensation}",
                    size="4",
                ),
                width="100%",
            ),
            spacing="3",
            align="stretch",
            width="100%",
        ),
    )


def sale_selector() -> rx.Component:
    return rx.cond(
        AddSaleReturnsState.sale_locked,
        rx.fragment(
            rx.text("Вихідний продаж:"),
            rx.input(value=AddSaleReturnsState.sale_label, disabled=True, width="100%"),
        ),
        rx.fragment(
            rx.text("*Продаж для повернення:"),
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


def add_form() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text("*Дата:"),
            rx.input(
                value=AddSaleReturnsState.current_date,
                on_change=AddSaleReturnsState.on_change_date,
                type="date",
                required=True,
                size="3",
                width="100%",
            ),
            sale_selector(),
            rx.text("*Склад призначення:"),
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
            units_section(),
            rx.hstack(
                rx.text("*Статус:"),
                rx.select(
                    AddSaleReturnsState.editable_statuses,
                    placeholder="Оберіть зі списку",
                    required=True,
                    value=AddSaleReturnsState.status,
                    on_change=AddSaleReturnsState.on_change_status,
                ),
            ),
            rx.text("Коментар:"),
            rx.text_area(
                value=AddSaleReturnsState.comment,
                on_change=AddSaleReturnsState.on_change_comment,
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
                "Повернення продажу/Додавання",
                left=rx.button(
                    "Скасувати",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(routes.MOVEMENT_SALE_RETURNS),
                ),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.SALE_RETURNS_CREATE),
                        rx.button(
                            "Зберегти",
                            variant="ghost",
                            size="3",
                            on_click=AddSaleReturnsState.add_one,
                        ),
                    ),
                ],
            ),
            add_form(),
            width="100%",
        ),
        value=SaleReturnsState.Pages.ADD,
    )
# ======================


# Edit
# ======================
def edit_form() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text("*Дата:"),
            rx.input(
                value=EditSaleReturnsState.item.movement.date,
                type="date",
                required=True,
                size="3",
                disabled=True,
            ),
            rx.text("Склад призначення:"),
            rx.input(
                value=EditSaleReturnsState.item.movement.destination_storage.title,
                disabled=True,
                width="100%",
            ),
            rx.hstack(
                rx.text("*Статус:"),
                rx.select(
                    EditSaleReturnsState.editable_statuses,
                    placeholder="Оберіть зі списку",
                    required=True,
                    value=EditSaleReturnsState.status,
                    on_change=EditSaleReturnsState.on_change_status,
                ),
            ),
            rx.text("Коментар:"),
            rx.text_area(
                value=EditSaleReturnsState.item.movement.comment,
                on_change=EditSaleReturnsState.on_change_comment,
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
                "Повернення продажу/Редагування",
                left=rx.button(
                    "Скасувати",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(
                        f"{routes.MOVEMENT_SALE_RETURNS_VIEW_ID}{EditSaleReturnsState.item.id}"
                    ),
                ),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.SALE_RETURNS_EDIT),
                        rx.button(
                            "Зберегти",
                            variant="ghost",
                            size="3",
                            on_click=EditSaleReturnsState.edit_one,
                        ),
                    ),
                ],
            ),
            edit_form(),
            width="100%",
        ),
        value=SaleReturnsState.Pages.EDIT,
    )
# ======================


def index() -> rx.Component:
    return rx.tabs.root(
        rx.cond(
            AppState.get_user_actions.contains(ActionEnum.SALE_RETURNS_LIST),
            list_tab_content(),
        ),
        rx.cond(
            AppState.get_user_actions.contains(ActionEnum.SALE_RETURNS_VIEW),
            item_preview_tab_content(),
        ),
        rx.cond(
            AppState.get_user_actions.contains(ActionEnum.SALE_RETURNS_CREATE),
            add_tab_content(),
        ),
        rx.cond(
            AppState.get_user_actions.contains(ActionEnum.SALE_RETURNS_EDIT),
            edit_tab_content(),
        ),
        value=SaleReturnsState.current_page,
        height="100%",
        width="100%",
    )
