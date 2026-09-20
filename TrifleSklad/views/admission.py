from typing import Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.declared import StorageType
from TrifleSklad.models import Admission, Product
from TrifleSklad.movement.inline_creator_components import (
    create_lookup_button,
    nds_rate_create_dialog,
    owner_create_dialog,
    payment_type_create_dialog,
    storage_create_dialog,
    supplier_create_dialog,
)
from TrifleSklad.movement.list_components import filter_button, filter_card, filter_select, pagination
from TrifleSklad.states.app import AppState
from TrifleSklad.states.admission import (
    AddAdmissionState,
    EditAdmissionState,
    ListAdmissionState,
    MovementProductCatalogAddEditFormState,
    MovementProductCatalogDetailedViewState,
    ViewAdmissionState,
)
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.templates import controls, full_edit
from TrifleSklad.views.templates.history import history_block
from TrifleSklad.views.templates.layouts import field_row, header_subpage, page_wrapper, titled_section


def _create_category_dialog() -> rx.Component:
    State = MovementProductCatalogAddEditFormState
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Створення категорії"),
            rx.vstack(
                rx.text("*Назва:", size="2"),
                controls.input_field(value=State.new_category_title, on_change=State.on_change_new_category_title, width="100%"),
                rx.text("Опис:", size="2"),
                controls.text_area_field(value=State.new_category_description, on_change=State.on_change_new_category_description, width="100%"),
                rx.hstack(
                    rx.button("Скасувати", variant="outline", type="button", on_click=State.set_create_category_open(False)),
                    rx.spacer(),
                    rx.button("Створити", type="button", on_click=State.create_category),
                    width="100%",
                    padding_top="0.5em",
                ),
                spacing="2",
                width="100%",
            ),
            width="28em",
        ),
        open=State.is_create_category_open,
        on_open_change=State.set_create_category_open,
    )


def _duplicate_product_confirm_dialog() -> rx.Component:
    State = MovementProductCatalogAddEditFormState
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Такий товар вже є в каталозі"),
            rx.text(f"ТМЦ «{State.duplicate_product_title}» вже є в каталозі. Додати наявний товар до поставки?"),
            rx.hstack(
                rx.button("Ні", variant="outline", type="button", on_click=State.cancel_duplicate_product),
                rx.spacer(),
                rx.button("Так, додати", type="button", on_click=State.confirm_use_duplicate_product),
                width="100%",
                padding_top="0.5em",
            ),
            width="28em",
        ),
        open=State.is_duplicate_confirm_open,
        on_open_change=State.set_duplicate_confirm_open,
    )


def _create_product_dialog() -> rx.Component:
    State = MovementProductCatalogAddEditFormState
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Створення товару каталогу"),
            rx.vstack(
                rx.text("*Назва:", size="2"),
                controls.input_field(value=State.new_title, on_change=State.on_change_new_title, width="100%"),
                rx.text("Опис:", size="2"),
                controls.text_area_field(value=State.new_description, on_change=State.on_change_new_description, width="100%"),
                rx.text("*Категорія:", size="2"),
                rx.select.root(
                    rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                    rx.select.content(
                        rx.foreach(State.list_categories, lambda c: rx.select.item(c[1], value=c[0])),
                        width="100%",
                    ),
                    value=State.new_id_category,
                    on_change=State.on_change_new_category,
                    width="100%",
                ),
                rx.hstack(
                    rx.spacer(),
                    rx.cond(
                        AppState.get_user_actions.contains(Action.CATEGORIES_CREATE),
                        rx.button(
                            rx.icon("plus", size=14),
                            "Створити категорію",
                            variant="ghost",
                            size="2",
                            type="button",
                            on_click=State.open_create_category,
                        ),
                    ),
                    width="100%",
                ),
                _create_category_dialog(),
                _duplicate_product_confirm_dialog(),
                rx.text("Одиниця виміру:", size="2"),
                controls.input_field(value=State.new_unit, on_change=State.on_change_new_unit, list="units-datalist-admission", width="100%"),
                rx.el.datalist(
                    rx.foreach(State.units_cache, lambda unit: rx.el.option(value=unit)),
                    id="units-datalist-admission",
                ),
                rx.text("Місткість:", size="2"),
                controls.input_field(
                    type="number",
                    min="0",
                    step="any",
                    value=State.new_capacity,
                    on_change=State.on_change_new_capacity,
                    disabled=State.new_uniq | State.new_no_fixed_capacity,
                    width="100%",
                ),
                rx.checkbox("Має серійний номер", checked=State.new_uniq, on_change=State.on_change_new_uniq),
                rx.checkbox("Подільний", checked=State.new_divisible, on_change=State.on_change_new_divisible, disabled=State.new_uniq),
                rx.checkbox(
                    "Без фіксованої ємності",
                    checked=State.new_no_fixed_capacity,
                    on_change=State.on_change_new_no_fixed_capacity,
                    disabled=State.new_uniq | ~State.new_divisible,
                ),
                rx.hstack(
                    rx.button("Скасувати", variant="outline", type="button", on_click=State.set_create_open(False)),
                    rx.spacer(),
                    rx.button("Створити", type="button", on_click=State.create_product),
                    width="100%",
                    padding_top="0.5em",
                ),
                spacing="2",
                width="100%",
            ),
            width="28em",
        ),
        open=State.is_create_open,
        on_open_change=State.set_create_open,
    )


def _movement_product_catalog_add_edit_form() -> rx.Component:
    return rx.vstack(
        rx.text("Категорія:", width="100%"),
        rx.select.root(
            rx.select.trigger(placeholder="Оберіть категорію", width="100%"),
            rx.select.content(
                rx.foreach(
                    MovementProductCatalogAddEditFormState.category_options,
                    lambda c: rx.select.item(c[0], value=c[1]),
                ),
                width="100%",
            ),
            value=MovementProductCatalogAddEditFormState.filter_category,
            on_change=MovementProductCatalogAddEditFormState.on_change_filter_category,
            width="100%",
        ),
        rx.text("Найменування з каталогу:", width="100%"),
        rx.select.root(
            rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
            rx.select.content(
                controls.search_field(
                    rx.input.slot(rx.icon("search")),
                    placeholder="Пошук за назвою",
                    value=MovementProductCatalogAddEditFormState.search_catalog,
                    on_change=MovementProductCatalogAddEditFormState.on_change_search_catalog,
                    width="100%",
                    margin_bottom="0.5em",
                ),
                rx.foreach(
                    MovementProductCatalogAddEditFormState.products_catalog_list,
                    lambda product_catalog: rx.select.item(product_catalog[0], value=product_catalog[1]),
                ),
                width="100%",
            ),
            required=True,
            disabled=~MovementProductCatalogAddEditFormState.category_chosen,
            value=MovementProductCatalogAddEditFormState.id_product_catalog,
            on_change=MovementProductCatalogAddEditFormState.on_change_id_product_catalog,
            width="100%",
        ),
        rx.hstack(
            rx.spacer(),
            rx.cond(
                AppState.get_user_actions.contains(Action.PRODUCTS_CREATE),
                rx.button(
                    rx.icon("plus", size=14),
                    "Створити товар",
                    variant="ghost",
                    size="2",
                    type="button",
                    on_click=MovementProductCatalogAddEditFormState.open_create_product,
                ),
            ),
            width="100%",
        ),
        _create_product_dialog(),
        rx.hstack(
            rx.text("Кількість:"),
            controls.input_field(
                type="number",
                min="0",
                step="1",
                required=True,
                is_invalid=MovementProductCatalogAddEditFormState.error_count,
                color_scheme=rx.cond(MovementProductCatalogAddEditFormState.error_count, "red", "None"),
                style=rx.cond(
                    MovementProductCatalogAddEditFormState.error_count,
                    {"border": "2px solid red", "box-shadow": "0 0 0 1px red"},
                    {},
                ),
                value=MovementProductCatalogAddEditFormState.count,
                on_change=MovementProductCatalogAddEditFormState.on_change_count,
            ),
            width="100%",
        ),
        rx.cond(
            MovementProductCatalogAddEditFormState.selected_divisible
            & MovementProductCatalogAddEditFormState.selected_no_fixed_capacity,
            rx.hstack(
                rx.text("Місткість одиниці:"),
                controls.input_field(
                    type="number",
                    min="0",
                    step="any",
                    required=True,
                    is_invalid=MovementProductCatalogAddEditFormState.error_capacity,
                    color_scheme=rx.cond(MovementProductCatalogAddEditFormState.error_capacity, "red", "None"),
                    style=rx.cond(
                        MovementProductCatalogAddEditFormState.error_capacity,
                        {"border": "2px solid red", "box-shadow": "0 0 0 1px red"},
                        {},
                    ),
                    value=MovementProductCatalogAddEditFormState.entered_capacity,
                    on_change=MovementProductCatalogAddEditFormState.on_change_entered_capacity,
                ),
                width="100%",
            ),
        ),
        rx.cond(
            MovementProductCatalogAddEditFormState.selected_divisible
            & ~MovementProductCatalogAddEditFormState.selected_no_fixed_capacity
            & (MovementProductCatalogAddEditFormState.selected_capacity > 0),
            rx.vstack(
                rx.hstack(
                    rx.text("Задати ємність усім:", size="2"),
                    controls.input_field(
                        type="number",
                        min="0",
                        step="any",
                        placeholder="Порожньо — повна ємність",
                        value=MovementProductCatalogAddEditFormState.bulk_capacity,
                        on_change=MovementProductCatalogAddEditFormState.on_change_bulk_capacity,
                    ),
                    width="100%",
                ),
                rx.hstack(
                    rx.text("Задати вартість усім:", size="2"),
                    controls.input_field(
                        type="number",
                        min="0",
                        step="0.01",
                        placeholder="Порожньо — пропорційно",
                        value=MovementProductCatalogAddEditFormState.bulk_price,
                        on_change=MovementProductCatalogAddEditFormState.on_change_bulk_price,
                    ),
                    width="100%",
                ),
                rx.accordion.root(
                    rx.accordion.item(
                        header=rx.text("Одиниці"),
                        content=rx.scroll_area(
                            rx.vstack(
                                rx.text(
                                    "Ємність — порожньо чи повне значення означає повну одиницю. "
                                    "Вартість — порожньо означає пропорційно заповненню від базової ціни; "
                                    "вказана вручну закріплюється за одиницею.",
                                    size="1", color="gray",
                                ),
                                rx.foreach(
                                    MovementProductCatalogAddEditFormState.unit_rows,
                                    lambda row: rx.hstack(
                                        rx.text(f"№{row[0] + 1}:", size="2", width="3em"),
                                        controls.input_field(
                                            type="number",
                                            min="0",
                                            step="any",
                                            max=MovementProductCatalogAddEditFormState.selected_capacity,
                                            is_invalid=row[2],
                                            color_scheme=rx.cond(row[2], "red", "None"),
                                            style=rx.cond(
                                                row[2],
                                                {"border": "2px solid red", "box-shadow": "0 0 0 1px red"},
                                                {},
                                            ),
                                            value=row[1],
                                            on_change=MovementProductCatalogAddEditFormState.on_change_unit_amount(row[0]),
                                            width="30%",
                                        ),
                                        rx.text(f"/ {MovementProductCatalogAddEditFormState.selected_capacity_label}", size="2", color="gray"),
                                        controls.input_field(
                                            type="number",
                                            min="0",
                                            step="0.01",
                                            placeholder="розрахунок",
                                            is_invalid=row[4],
                                            color_scheme=rx.cond(row[4], "red", "None"),
                                            style=rx.cond(
                                                row[4],
                                                {"border": "2px solid red", "box-shadow": "0 0 0 1px red"},
                                                {},
                                            ),
                                            value=row[3],
                                            on_change=MovementProductCatalogAddEditFormState.on_change_unit_price(row[0]),
                                            width="40%",
                                        ),
                                        width="100%",
                                        align="center",
                                    ),
                                ),
                                width="100%",
                            ),
                            padding="0.5em",
                            width="100%",
                            height="11em",
                        ),
                    ),
                    collapsible=True,
                    variant="outline",
                    width="100%",
                ),
                width="100%",
                spacing="2",
            ),
        ),
        rx.hstack(
            rx.text("Вартість за одиницю:"),
            controls.input_field(
                type="number",
                min="0",
                step="0.01",
                required=True,
                is_invalid=MovementProductCatalogAddEditFormState.error_price,
                color_scheme=rx.cond(MovementProductCatalogAddEditFormState.error_price, "red", "None"),
                style=rx.cond(
                    MovementProductCatalogAddEditFormState.error_price,
                    {"border": "1px solid red", "box-shadow": "0 0 0 1px red"},
                    {},
                ),
                value=MovementProductCatalogAddEditFormState.price,
                on_change=MovementProductCatalogAddEditFormState.on_change_price,
            ),
            width="100%",
        ),
        rx.cond(
            MovementProductCatalogAddEditFormState.product_is_uniq,
            rx.accordion.root(
                rx.accordion.item(
                    header=rx.text("Серійні номери"),
                    content=rx.scroll_area(
                        rx.vstack(
                            rx.hstack(
                                controls.input_field(
                                    placeholder="Маска, напр. СН-{n}",
                                    value=MovementProductCatalogAddEditFormState.serial_mask,
                                    on_change=MovementProductCatalogAddEditFormState.on_change_serial_mask,
                                    width="40%",
                                ),
                                controls.input_field(
                                    placeholder="Від",
                                    type="text",
                                    value=MovementProductCatalogAddEditFormState.serial_range_from,
                                    on_change=MovementProductCatalogAddEditFormState.on_change_serial_range_from,
                                    width="20%",
                                ),
                                controls.input_field(
                                    placeholder="До",
                                    type="text",
                                    value=MovementProductCatalogAddEditFormState.serial_range_to,
                                    on_change=MovementProductCatalogAddEditFormState.on_change_serial_range_to,
                                    width="20%",
                                ),
                                rx.button(
                                    "Заповнити",
                                    type="button",
                                    size="1",
                                    on_click=MovementProductCatalogAddEditFormState.fill_serial_range,
                                ),
                                width="100%",
                                spacing="1",
                            ),
                            rx.text(
                                rx.checkbox(
                                    checked=MovementProductCatalogAddEditFormState.serial_range_hex,
                                    on_change=MovementProductCatalogAddEditFormState.on_change_serial_range_hex,
                                ),
                                " 16-та система числення (0-9, A-F)",
                                as_="label",
                                size="1",
                            ),
                            rx.foreach(
                                MovementProductCatalogAddEditFormState.item_products_list,
                                lambda item: rx.hstack(
                                    controls.input_field(
                                        type="text",
                                        value=item[1].serial_number,
                                        on_change=MovementProductCatalogAddEditFormState.on_change_serial_numbers(item[0]),
                                        width="100%",
                                    ),
                                    width="100%",
                                ),
                            ),
                            width="100%",
                            height="100%",
                        ),
                        padding="0.5em",
                        width="100%",
                        height="11em",
                    ),
                ),
                collapsible=True,
                variant="outline",
                width="100%",
            ),
        ),
    )


def _detailed_unit_table_row(item: Tuple[int, Product]) -> rx.Component:
    State = MovementProductCatalogDetailedViewState
    return rx.table.row(
        rx.table.cell(
            rx.cond(
                item[1].id,
                rx.link(item[1].id, href=f"{routes.REPORTS_UNITS_VIEW_ID}{item[1].id}"),
                rx.text(item[1].id),
            ),
            width="1%", white_space="nowrap",
        ),
        rx.table.cell(
            rx.cond(
                State.item.product.uniq,
                rx.text(rx.cond(item[1].serial_number, item[1].serial_number, "—")),
                rx.text("—", color="gray"),
            ),
        ),
        rx.table.cell(
            rx.cond(
                State.item.product.divisible,
                rx.text(item[1].count),
                rx.text("—", color="gray"),
            ),
            width="1%", white_space="nowrap",
        ),
        rx.table.cell(
            rx.cond(
                item[1].excluded_from_accounting,
                rx.badge("Поза обліком", color_scheme="orange", size="1", variant="soft"),
                rx.text("—", color="gray"),
            ),
            width="1%", white_space="nowrap",
        ),
    )


def _movement_product_catalog_detailed_view_form() -> rx.Component:
    return rx.vstack(
        rx.text("Товари з каталогу:", width="100%"),
        rx.text(
            MovementProductCatalogDetailedViewState.item.product.title,
            weight="bold",
            decoration="underline",
            width="100%",
        ),
        rx.hstack(
            rx.text("Кількість:"),
            rx.text(MovementProductCatalogDetailedViewState.item.count, weight="bold", decoration="underline", width="100%"),
        ),
        rx.hstack(
            rx.text("Вартість за одиницю:"),
            rx.text(MovementProductCatalogDetailedViewState.price_display, weight="bold", decoration="underline", width="100%"),
        ),
        rx.text("Одиниці ТМЦ:", width="100%"),
        rx.scroll_area(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.table.column_header_cell("ID", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                        rx.table.column_header_cell("Серійний номер", color=rx.color("accent", 2)),
                        rx.table.column_header_cell("Залишок", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                        rx.table.column_header_cell("Облік", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                    ),
                    background_color=rx.color("accent", 9),
                ),
                rx.table.body(rx.foreach(MovementProductCatalogDetailedViewState.item_products_list, _detailed_unit_table_row)),
                variant="surface",
                width="100%",
            ),
            max_height="14em",
            width="100%",
        ),
    )


def _add_admission_products_catalog_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Інформація про товар"),
            rx.tabs.root(
                rx.tabs.content(
                    _movement_product_catalog_add_edit_form(),
                    value=AddAdmissionState.ProductCatalogDialogPages.EDIT,
                    width="100%", height="100%",
                ),
                rx.tabs.content(
                    _movement_product_catalog_detailed_view_form(),
                    value=AddAdmissionState.ProductCatalogDialogPages.VIEW,
                    width="100%", height="100%",
                ),
                default_value=AddAdmissionState.ProductCatalogDialogPages.EMPTY,
                value=AddAdmissionState.product_catalog_dialog_page,
            ),
            rx.cond(
                AddAdmissionState.is_product_dialog_view_mode,
                rx.hstack(
                    rx.button("Видалити", variant="outline", color_scheme="red", on_click=AddAdmissionState.on_close_product_catalog_dialog),
                    rx.spacer(),
                    rx.button("Редагувати", type="button", on_click=AddAdmissionState.edit_product_catalog_dialog),
                    padding_top="1em",
                    width="100%",
                ),
                rx.hstack(
                    rx.button("Скасувати", variant="outline", on_click=AddAdmissionState.on_close_product_catalog_dialog),
                    rx.spacer(),
                    rx.button("Зберегти", disabled=MovementProductCatalogAddEditFormState.has_errors, on_click=AddAdmissionState.on_save_product_catalog_dialog),
                    padding_top="1em",
                    width="100%",
                ),
            ),
            width="30em",
        ),
        open=AddAdmissionState.is_open_product_catalog_dialog,
        on_open_change=AddAdmissionState.on_close_product_catalog_dialog,
    )


def _edit_admission_products_catalog_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Інформація про товар"),
            rx.tabs.root(
                rx.tabs.content(
                    _movement_product_catalog_add_edit_form(),
                    value=EditAdmissionState.ProductCatalogDialogPages.EDIT,
                    width="100%", height="100%",
                ),
                rx.tabs.content(
                    _movement_product_catalog_detailed_view_form(),
                    value=EditAdmissionState.ProductCatalogDialogPages.VIEW,
                    width="100%", height="100%",
                ),
                default_value=EditAdmissionState.ProductCatalogDialogPages.EMPTY,
                value=EditAdmissionState.product_catalog_dialog_page,
            ),
            rx.cond(
                EditAdmissionState.is_product_dialog_view_mode,
                rx.hstack(
                    rx.button("Видалити", variant="outline", color_scheme="red", on_click=EditAdmissionState.on_close_product_catalog_dialog),
                    rx.spacer(),
                    rx.button("Редагувати", type="button", on_click=EditAdmissionState.edit_product_catalog_dialog),
                    padding_top="1em",
                    width="100%",
                ),
                rx.hstack(
                    rx.button("Скасувати", variant="outline", on_click=EditAdmissionState.on_close_product_catalog_dialog),
                    rx.spacer(),
                    rx.button("Зберегти", disabled=MovementProductCatalogAddEditFormState.has_errors, on_click=EditAdmissionState.on_save_product_catalog_dialog),
                    padding_top="1em",
                    width="100%",
                ),
            ),
            width="30em",
        ),
        open=EditAdmissionState.is_open_product_catalog_dialog,
        on_open_change=EditAdmissionState.on_close_product_catalog_dialog,
    )


def _edit_admission_add_product_button() -> rx.Component:
    return rx.cond(
        EditAdmissionState.can_edit_full,
        rx.hstack(
            rx.spacer(),
            rx.button("Додати позицію", type="button", variant="soft", size="2", on_click=EditAdmissionState.add_product_catalog_dialog_open),
            width="100%",
        ),
    )


def _edit_admission_products_catalog_table() -> rx.Component:
    return rx.vstack(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Товар", color=rx.color("accent", 2)),
                    rx.table.column_header_cell("К-сть одиниць", color=rx.color("accent", 2)),
                    rx.table.column_header_cell("Залишок", color=rx.color("accent", 2)),
                    rx.table.column_header_cell("Ціна за од.", color=rx.color("accent", 2)),
                    rx.table.column_header_cell("Сума", color=rx.color("accent", 2)),
                    rx.cond(
                        EditAdmissionState.can_edit_full,
                        rx.table.column_header_cell("Дії", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                    ),
                ),
                background_color=rx.color("accent", 9),
            ),
            rx.table.body(
                rx.foreach(
                    EditAdmissionState.item_movement_products_catalog_list,
                    lambda item: rx.table.row(
                        rx.table.cell(item[1].product.title),
                        rx.table.cell(item[1].count),
                        rx.table.cell(item[4]),
                        rx.table.cell(item[2]),
                        rx.table.cell(item[3]),
                        rx.cond(
                            EditAdmissionState.can_edit_full,
                            rx.table.cell(
                                rx.hstack(
                                    rx.icon_button(
                                        rx.icon("pencil", size=14),
                                        type="button",
                                        variant="soft",
                                        size="1",
                                        on_click=EditAdmissionState.edit_product_catalog_dialog_from_row(item[0]).stop_propagation,
                                    ),
                                    rx.icon_button(
                                        rx.icon("trash-2", size=14),
                                        type="button",
                                        variant="soft",
                                        color_scheme="red",
                                        size="1",
                                        on_click=EditAdmissionState.delete_product_catalog_row(item[0]).stop_propagation,
                                    ),
                                    spacing="1",
                                ),
                                width="1%", white_space="nowrap",
                            ),
                        ),
                        on_click=EditAdmissionState.view_product_catalog_dialog(item[0]),
                        cursor="pointer",
                        _hover={"background_color": rx.color("accent", 3)},
                    ),
                ),
                height="100%",
                width="100%",
            ),
            variant="surface",
            height="100%",
            width="100%",
        ),
        width="100%",
    )


def _add_admission_products_catalog_table() -> rx.Component:
    return rx.vstack(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Товар", color=rx.color("accent", 2)),
                    rx.table.column_header_cell("К-сть одиниць", color=rx.color("accent", 2)),
                    rx.table.column_header_cell("Залишок", color=rx.color("accent", 2)),
                    rx.table.column_header_cell("Ціна за од.", color=rx.color("accent", 2)),
                    rx.table.column_header_cell("Сума", color=rx.color("accent", 2)),
                ),
                background_color=rx.color("accent", 9),
            ),
            rx.table.body(
                rx.foreach(
                    AddAdmissionState.item_movement_products_catalog_list,
                    lambda item: rx.table.row(
                        rx.table.cell(item[1].product.title),
                        rx.table.cell(item[1].count),
                        rx.table.cell(item[4]),
                        rx.table.cell(item[2]),
                        rx.table.cell(item[3]),
                        on_click=AddAdmissionState.view_product_catalog_dialog(item[0]),
                        cursor="pointer",
                        _hover={"background_color": rx.color("accent", 3)},
                    ),
                ),
                height="100%",
                width="100%",
            ),
            variant="surface",
            height="100%",
            width="100%",
        ),
        width="100%",
    )


def _view_admission_products_catalog_table() -> rx.Component:
    return rx.vstack(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Товар", color=rx.color("accent", 2)),
                    rx.table.column_header_cell("К-сть одиниць", color=rx.color("accent", 2)),
                    rx.table.column_header_cell("Залишок", color=rx.color("accent", 2)),
                    rx.table.column_header_cell("Ціна за од.", color=rx.color("accent", 2)),
                    rx.table.column_header_cell("Сума", color=rx.color("accent", 2)),
                ),
                background_color=rx.color("accent", 9),
            ),
            rx.table.body(
                rx.foreach(
                    ViewAdmissionState.item_movement_products_catalog_list,
                    lambda item: rx.table.row(
                        rx.table.cell(item[1].product.title),
                        rx.table.cell(item[1].count),
                        rx.table.cell(item[4]),
                        rx.table.cell(item[2]),
                        rx.table.cell(item[3]),
                        on_click=ViewAdmissionState.on_change_dialog_open(item[0]),
                        cursor="pointer",
                        _hover={"background_color": rx.color("accent", 3)},
                    ),
                ),
                height="100%",
                width="100%",
            ),
            variant="surface",
            height="100%",
            width="100%",
        ),
        width="100%",
    )


def _cancel_conflict_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Видалення неможливе"),
            rx.dialog.description(
                "Товар із цього постачання бере участь у наведених нижче рухах. "
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
                        ViewAdmissionState.cancel_conflict_rows,
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
                    rx.button("Закрити", on_click=ViewAdmissionState.set_cancel_conflict_dialog_open(False)),
                ),
                justify="end",
                margin_top="1em",
            ),
            max_width="42em",
        ),
        open=ViewAdmissionState.is_cancel_conflict_dialog_open,
        on_open_change=ViewAdmissionState.set_cancel_conflict_dialog_open,
    )


def view_page_content() -> rx.Component:
    return rx.vstack(
        _cancel_conflict_dialog(),
        titled_section(
            "Загальна інформація",
            field_row("Дата", ViewAdmissionState.item.movement.date),
            field_row("Постачальник", ViewAdmissionState.item.supplier.title),
            field_row("Одержувач", ViewAdmissionState.item.movement.destination_owner.title),
            field_row("Склад", ViewAdmissionState.item.movement.destination_storage.title),
            field_row("Статус", ViewAdmissionState.item_status),
            field_row("Коментар", ViewAdmissionState.item.movement.comment),
        ),
        titled_section(
            "Товари",
            _view_admission_products_catalog_table(),
            rx.dialog.root(
                rx.dialog.content(
                    rx.dialog.title("Інформація про товар"),
                    _movement_product_catalog_detailed_view_form(),
                    width="30em",
                ),
                open=ViewAdmissionState.dialog_open,
                on_open_change=ViewAdmissionState.close_dialog,
            ),
        ),
        titled_section(
            "Фінанси",
            field_row("Сума без ПДВ", ViewAdmissionState.subtotal_display),
            field_row("Ставка ПДВ", ViewAdmissionState.nds_rate_title),
            field_row("Сума ПДВ", ViewAdmissionState.nds_amount_display),
            field_row("Разом з ПДВ", ViewAdmissionState.total_display),
            field_row("ПДВ включений у ціну", rx.cond(ViewAdmissionState.item.flag_nds, "Так", "Ні")),
            field_row("Спосіб оплати", ViewAdmissionState.item.payment_type.title),
            field_row("Номер накладної оплати", ViewAdmissionState.invoice_number),
            field_row("Курс долара", ViewAdmissionState.item.dollar_rate),
        ),
        history_block(ViewAdmissionState),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def view_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Постачання/Перегляд",
            rx.cond(
                ViewAdmissionState.get_user_actions.contains(Action.ADMISSIONS_DELETE),
                controls.cancel_with_reason(
                    open=ViewAdmissionState.is_cancel_reason_dialog_open,
                    on_open_change=ViewAdmissionState.set_cancel_reason_dialog_open,
                    value=ViewAdmissionState.cancel_reason,
                    on_change=ViewAdmissionState.on_change_cancel_reason,
                    on_open_trigger=ViewAdmissionState.open_cancel_reason_dialog,
                    on_confirm=ViewAdmissionState.confirm_cancel,
                    title="Підтвердження видалення",
                    trigger_label="Видалити",
                    description="Ви впевнені, що бажаєте видалити цей запис? Цю дію не можна буде скасувати.",
                ),
            ),
            rx.cond(
                ViewAdmissionState.get_user_actions.contains(Action.ADMISSIONS_EDIT),
                controls.button_primary("Редагувати", on_click=ViewAdmissionState.on_click_edit),
            ),
            left=controls.button_back(routes.MOVEMENT_ADMISSIONS, label="Повернутись"),
            width="100%",
        ),
        rx.skeleton(view_page_content(), loading=ViewAdmissionState.in_process, height="100%"),
    )


def _table_row(item: Tuple[int, Admission, str]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item[1].id)),
        rx.table.row_header_cell(item[1].movement.date, align="left"),
        rx.table.cell(rx.text(item[1].supplier.title)),
        rx.table.cell(rx.text(item[1].movement.destination_storage.title)),
        rx.table.cell(rx.text(item[1].movement.destination_owner.title)),
        rx.table.cell(rx.text(item[1].payment_type.title)),
        rx.table.cell(rx.text(item[2])),
        rx.table.cell(rx.text(rx.cond(item[1].flag_nds, "Так", "Ні"))),
        rx.table.cell(rx.text(ListAdmissionState.get_movement_statuses[item[1].movement.status])),
        on_click=rx.redirect(f"{routes.MOVEMENT_ADMISSIONS_VIEW_ID}{item[1].id}"),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def _table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("№", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Дата", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Постачальник", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Склад", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Одержувач", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Тип платежу", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Сума", color=rx.color("accent", 2)),
                rx.table.column_header_cell("ПДВ", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Статус", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(rx.foreach(ListAdmissionState.get_items, _table_row)),
        variant="surface",
        width="100%",
    )


def list_page_content() -> rx.Component:
    return rx.vstack(
        rx.cond(ListAdmissionState.has_items, _table(), controls.empty_placeholder()),
        pagination(ListAdmissionState),
        spacing="3",
        width="100%",
    )


@require_login
def list_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Постачання",
            filter_button(ListAdmissionState),
            rx.cond(
                ListAdmissionState.get_user_actions.contains(Action.ADMISSIONS_CREATE),
                controls.button_primary("Створити", on_click=ListAdmissionState.on_click_add),
            ),
            width="100%",
        ),
        rx.skeleton(list_page_content(), loading=ListAdmissionState.in_progress, height="100%"),
        filter_panel=filter_card(
            ListAdmissionState,
            filter_select(
                "Постачальник",
                ListAdmissionState.filter_supplier,
                ListAdmissionState.list_suppliers,
                ListAdmissionState.on_change_filter_supplier,
            ),
            filter_select(
                "Склад призначення",
                ListAdmissionState.filter_destination_storage,
                ListAdmissionState.list_warehouses,
                ListAdmissionState.on_change_filter_destination_storage,
            ),
            filter_select(
                "Власник призначення",
                ListAdmissionState.filter_destination_owner,
                ListAdmissionState.list_owners,
                ListAdmissionState.on_change_filter_destination_owner,
            ),
        ),
        on_mount=ListAdmissionState.on_load,
    )


def _add_form() -> rx.Component:
    return rx.vstack(
        titled_section(
            "Загальна інформація",
            rx.text("*Дата:", weight="medium"),
            controls.input_field(type="date", required=True, default_value=AddAdmissionState.item.movement.date, width="100%", on_change=AddAdmissionState.on_change_date),
            rx.text("*Постачальник:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(AddAdmissionState.list_suppliers, lambda supplier: rx.select.item(supplier[0], value=supplier[1])),
                    width="100%",
                ),
                required=True,
                value=AddAdmissionState.id_supplier,
                on_change=AddAdmissionState.on_change_id_supplier,
            ),
            create_lookup_button(Action.SUPPLIERS_CREATE, "Створити постачальника", AddAdmissionState.open_supplier_create),
            supplier_create_dialog(AddAdmissionState),
            rx.text("*Склад:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.vstack(
                        controls.search_field(
                            placeholder="Введіть назву для пошуку",
                            width="100%",
                            value=AddAdmissionState.search_name_destination_storage,
                            on_change=AddAdmissionState.on_change_search_name_destination_storage,
                        ),
                        rx.foreach(AddAdmissionState.list_storages, lambda storage: rx.select.item(storage[0], value=storage[1], width="100%")),
                        width="100%",
                    ),
                    width="100%",
                ),
                required=True,
                value=AddAdmissionState.id_destination_storage,
                on_change=AddAdmissionState.on_change_id_destination_storage,
            ),
            create_lookup_button(
                Action.STORAGE_CREATE,
                "Створити склад",
                AddAdmissionState.open_storage_create(StorageType.WAREHOUSE, "destination", False),
            ),
            storage_create_dialog(AddAdmissionState),
            rx.text("*Одержувач:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(AddAdmissionState.list_owners, lambda owner: rx.select.item(owner[0], value=owner[1])),
                    width="100%",
                ),
                required=True,
                value=AddAdmissionState.id_destination_owner,
                on_change=AddAdmissionState.on_change_id_destination_owner,
            ),
            create_lookup_button(Action.OWNERS_CREATE, "Створити власника", AddAdmissionState.open_owner_create("")),
            owner_create_dialog(AddAdmissionState),
            rx.text("*Статус:", weight="medium"),
            rx.select(
                AddAdmissionState.editable_statuses,
                placeholder="Оберіть зі списку",
                required=True,
                value=AddAdmissionState.status,
                on_change=AddAdmissionState.on_change_status,
            ),
            rx.text("Коментар:", weight="medium"),
            controls.text_area_field(value=AddAdmissionState.item.movement.comment, on_change=AddAdmissionState.on_change_comment, width="100%"),
        ),
        titled_section(
            "Товари",
            rx.text("*Товари з каталогу:", weight="medium"),
            _add_admission_products_catalog_dialog(),
            rx.cond(
                AddAdmissionState.has_item_movement_products_catalog,
                _add_admission_products_catalog_table(),
                rx.center(rx.text("Нічого не обрано", color="gray"), width="100%", size="3"),
            ),
            rx.button("Додати", on_click=AddAdmissionState.add_product_catalog_dialog_open),
        ),
        titled_section(
            "Фінанси",
            rx.text("*Спосіб оплати:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(AddAdmissionState.list_payment_types, lambda payment_type: rx.select.item(payment_type[0], value=payment_type[1])),
                    width="100%",
                ),
                required=True,
                value=AddAdmissionState.id_payment_type,
                on_change=AddAdmissionState.on_change_id_payment_type,
            ),
            create_lookup_button(Action.PAYMENT_TYPE_CREATE, "Створити тип оплати", AddAdmissionState.open_payment_type_create),
            payment_type_create_dialog(AddAdmissionState),
            rx.text("Номер накладної оплати:", weight="medium"),
            controls.input_field(value=AddAdmissionState.invoice_number, on_change=AddAdmissionState.on_change_invoice_number),
            rx.text("Ставка ПДВ:", weight="medium"),
            rx.hstack(
                rx.select.root(
                    # flex="1"+min_width="0" на тригері (не на select.root — той
                    # не рендерить власний DOM-стилізовний елемент) замість
                    # width="100%": селект тут ділить рядок із кнопкою-скидання,
                    # а Radix SelectTrigger має дефолтний flex-shrink:0, тому
                    # width="100%" не давав йому стиснутись під сусіда — кнопка
                    # вилазила за межі рядка.
                    rx.select.trigger(placeholder="Без ПДВ", flex="1", min_width="0"),
                    rx.select.content(
                        rx.select.item("Без ПДВ", value="None"),
                        rx.foreach(AddAdmissionState.list_nds_rates, lambda nr: rx.select.item(nr[0], value=nr[1])),
                        width="100%",
                    ),
                    value=AddAdmissionState.id_nds_rate,
                    on_change=AddAdmissionState.on_change_id_nds_rate,
                ),
                rx.button(
                    rx.icon("x", size=16),
                    type="button",
                    variant="soft",
                    color_scheme="gray",
                    title="Скинути ставку ПДВ",
                    disabled=AddAdmissionState.id_nds_rate == "",
                    on_click=AddAdmissionState.on_change_id_nds_rate(""),
                ),
                width="100%",
                align="center",
            ),
            create_lookup_button(Action.NDS_RATES_CREATE, "Створити ставку ПДВ", AddAdmissionState.open_nds_rate_create),
            nds_rate_create_dialog(AddAdmissionState),
            rx.hstack(
                rx.switch(default_value=False, value=AddAdmissionState.flag_nds, on_change=AddAdmissionState.on_change_flag_nds),
                rx.text("Ціна в рядках вказана з ПДВ"),
            ),
            rx.vstack(
                rx.hstack(rx.text("Сума без ПДВ:"), rx.text(AddAdmissionState.subtotal_display)),
                rx.hstack(rx.text("Сума ПДВ:"), rx.text(AddAdmissionState.nds_amount_display)),
                rx.hstack(rx.text("Разом з ПДВ:"), rx.text(AddAdmissionState.total_display)),
                width="100%",
            ),
            rx.hstack(
                rx.text("Курс долара:"),
                controls.input_field(required=True, value=AddAdmissionState.dollar_rate, on_change=AddAdmissionState.on_change_dollar_rate),
            ),
        ),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def add_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Постачання/Додавання",
            controls.button_secondary("Зберегти і продовжити", on_click=AddAdmissionState.add_one(True)),
            controls.button_primary("Зберегти", on_click=AddAdmissionState.add_one(False)),
            left=controls.button_back(routes.MOVEMENT_ADMISSIONS, label="Скасувати"),
            width="100%",
        ),
        _add_form(),
        on_mount=AddAdmissionState.on_load,
    )


def _edit_form() -> rx.Component:
    return rx.vstack(
        full_edit.full_edit_notice(EditAdmissionState),
        full_edit.save_reason_dialog(EditAdmissionState),
        titled_section(
            "Загальна інформація",
            rx.text("*Дата:", weight="medium"),
            controls.input_field(type="date", required=True, default_value=EditAdmissionState.item.movement.date, disabled=EditAdmissionState.is_view_only_edit, on_change=EditAdmissionState.on_change_date, width="100%"),
            rx.text("*Постачальник:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(EditAdmissionState.list_suppliers, lambda supplier: rx.select.item(supplier[0], value=supplier[1])),
                    width="100%",
                ),
                required=True,
                disabled=EditAdmissionState.is_view_only_edit,
                value=EditAdmissionState.id_supplier,
                default_value=EditAdmissionState.id_supplier,
                on_change=EditAdmissionState.on_change_id_supplier,
            ),
            rx.text("*Склад:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.vstack(
                        controls.search_field(
                            placeholder="Введіть назву для пошуку",
                            width="100%",
                            value=EditAdmissionState.search_name_destination_storage,
                            on_change=EditAdmissionState.on_change_search_name_destination_storage,
                        ),
                        rx.foreach(EditAdmissionState.list_storages, lambda storage: rx.select.item(storage[0], value=storage[1], width="100%")),
                        width="100%",
                    ),
                    width="100%",
                ),
                required=True,
                disabled=EditAdmissionState.is_view_only_edit,
                value=EditAdmissionState.id_destination_storage,
                default_value=EditAdmissionState.id_destination_storage,
                on_change=EditAdmissionState.on_change_id_destination_storage,
            ),
            rx.text("*Одержувач:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(EditAdmissionState.list_owners, lambda owner: rx.select.item(owner[0], value=owner[1])),
                    width="100%",
                ),
                required=True,
                disabled=EditAdmissionState.is_view_only_edit,
                value=EditAdmissionState.id_destination_owner,
                on_change=EditAdmissionState.on_change_id_destination_owner,
            ),
            rx.hstack(
                rx.text("*Статус:"),
                rx.select(
                    EditAdmissionState.editable_statuses,
                    placeholder="Оберіть зі списку",
                    required=True,
                    value=EditAdmissionState.status,
                    on_change=EditAdmissionState.on_change_status,
                ),
            ),
            rx.text("Коментар:", weight="medium"),
            controls.text_area_field(value=EditAdmissionState.item.movement.comment, on_change=EditAdmissionState.on_change_comment, width="100%"),
        ),
        titled_section(
            "Товари",
            rx.text("*Товари з каталогу:", weight="medium"),
            _edit_admission_products_catalog_dialog(),
            _edit_admission_add_product_button(),
            rx.cond(
                EditAdmissionState.has_item_movement_products_catalog,
                _edit_admission_products_catalog_table(),
                rx.center(rx.text("Нічого не обрано", color="gray"), width="100%", size="3"),
            ),
        ),
        titled_section(
            "Фінанси",
            rx.text("*Спосіб оплати:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(EditAdmissionState.list_payment_types, lambda payment_type: rx.select.item(payment_type[0], value=payment_type[1])),
                    width="100%",
                ),
                required=True,
                disabled=EditAdmissionState.is_view_only_edit,
                value=EditAdmissionState.id_payment_type,
                on_change=EditAdmissionState.on_change_id_payment_type,
            ),
            rx.text("Номер накладної оплати:", weight="medium"),
            controls.input_field(value=EditAdmissionState.invoice_number, on_change=EditAdmissionState.on_change_invoice_number),
            rx.text("Ставка ПДВ:", weight="medium"),
            rx.hstack(
                rx.select.root(
                    rx.select.trigger(placeholder="Без ПДВ", flex="1", min_width="0"),
                    rx.select.content(
                        rx.select.item("Без ПДВ", value="None"),
                        rx.foreach(EditAdmissionState.list_nds_rates, lambda nr: rx.select.item(nr[0], value=nr[1])),
                        width="100%",
                    ),
                    value=EditAdmissionState.id_nds_rate,
                    on_change=EditAdmissionState.on_change_id_nds_rate,
                ),
                rx.button(
                    rx.icon("x", size=16),
                    type="button",
                    variant="soft",
                    color_scheme="gray",
                    title="Скинути ставку ПДВ",
                    disabled=EditAdmissionState.id_nds_rate == "",
                    on_click=EditAdmissionState.on_change_id_nds_rate(""),
                ),
                width="100%",
                align="center",
            ),
            rx.hstack(
                rx.switch(default_value=False, disabled=EditAdmissionState.is_view_only_edit, value=EditAdmissionState.flag_nds, on_change=EditAdmissionState.on_change_flag_nds),
                rx.text("Ціна в рядках вказана з ПДВ"),
            ),
            rx.vstack(
                rx.hstack(rx.text("Сума без ПДВ:"), rx.text(EditAdmissionState.subtotal_display)),
                rx.hstack(rx.text("Сума ПДВ:"), rx.text(EditAdmissionState.nds_amount_display)),
                rx.hstack(rx.text("Разом з ПДВ:"), rx.text(EditAdmissionState.total_display)),
                width="100%",
            ),
            rx.hstack(
                rx.text("Курс долара:"),
                controls.input_field(required=True, disabled=EditAdmissionState.is_view_only_edit, value=EditAdmissionState.dollar_rate, on_change=EditAdmissionState.on_change_dollar_rate),
            ),
        ),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def edit_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Постачання/Редагування",
            controls.button_primary("Зберегти", on_click=EditAdmissionState.open_save_dialog),
            left=controls.button_back(routes.MOVEMENT_ADMISSIONS, label="Скасувати"),
            width="100%",
        ),
        rx.skeleton(_edit_form(), loading=EditAdmissionState.in_process, height="100%"),
    )
