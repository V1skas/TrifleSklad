import reflex as rx

from components.elements import subpage_header
from TrifleSklad.movement.list_components import filter_button, filter_card, pagination

from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.declared import movements_status_list

from TrifleSklad import routes
from TrifleSklad.movement.admissions.backend import *

from TrifleSklad.movement.admissions.backend import AdmissionState, AddAdmissionState, MovementProductCatalogAddEditFormState, MovementProductCatalogDetailedViewState
from TrifleSklad.models import Admission
from TrifleSklad.declared import MovementsStatus
from TrifleSklad.state import AppState

def create_category_dialog() -> rx.Component:
    # Вкладений діалог створення нової категорії з діалогу створення товару.
    State = MovementProductCatalogAddEditFormState
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Створення категорії"),
            rx.vstack(
                rx.text("*Назва:", size="2"),
                rx.input(
                    value=State.new_category_title,
                    on_change=State.on_change_new_category_title,
                    width="100%",
                ),
                rx.text("Опис:", size="2"),
                rx.text_area(
                    value=State.new_category_description,
                    on_change=State.on_change_new_category_description,
                    width="100%",
                ),
                rx.hstack(
                    rx.button(
                        "Скасувати",
                        variant="outline",
                        type="button",
                        on_click=State.set_create_category_open(False),
                    ),
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


def create_product_dialog() -> rx.Component:
    # Вкладений діалог створення нового товару каталогу прямо з поставки.
    State = MovementProductCatalogAddEditFormState
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Створення товару каталогу"),
            rx.vstack(
                rx.text("*Назва:", size="2"),
                rx.input(value=State.new_title, on_change=State.on_change_new_title, width="100%"),
                rx.text("Опис:", size="2"),
                rx.text_area(value=State.new_description, on_change=State.on_change_new_description, width="100%"),
                rx.text("*Категорія:", size="2"),
                rx.select.root(
                    rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                    rx.select.content(
                        rx.foreach(
                            State.list_categories,
                            lambda c: rx.select.item(c[1], value=c[0]),
                        ),
                        width="100%",
                    ),
                    value=State.new_id_category,
                    on_change=State.on_change_new_category,
                    width="100%",
                ),
                rx.hstack(
                    rx.spacer(),
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.CATEGORIES_CREATE),
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
                create_category_dialog(),
                rx.text("Одиниця виміру:", size="2"),
                rx.input(
                    value=State.new_unit,
                    on_change=State.on_change_new_unit,
                    list="units-datalist-admission",
                    width="100%",
                ),
                rx.el.datalist(
                    rx.foreach(
                        State.units_cache,
                        lambda unit: rx.el.option(value=unit),
                    ),
                    id="units-datalist-admission",
                ),
                rx.text("Місткість:", size="2"),
                rx.input(
                    type="number",
                    min="0",
                    value=State.new_capacity,
                    on_change=State.on_change_new_capacity,
                    disabled=State.new_uniq,
                    width="100%",
                ),
                rx.checkbox(
                    "Має серійний номер",
                    checked=State.new_uniq,
                    on_change=State.on_change_new_uniq,
                ),
                rx.checkbox(
                    "Подільний",
                    checked=State.new_divisible,
                    on_change=State.on_change_new_divisible,
                    disabled=State.new_uniq,
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


def movement_product_catalog_add_edit_form() -> rx.Component:
    return rx.vstack(
        rx.text("Найменування з каталогу:", width="100%"),
        rx.select.root(
            rx.select.trigger(
                placeholder="Оберіть зі списку",
                width="100%",
            ),
            rx.select.content(
                rx.foreach(
                    MovementProductCatalogAddEditFormState.products_catalog_list,
                    lambda product_catalog: rx.select.item(product_catalog[0], value=product_catalog[1])
                ),
                width="100%",
            ),

            name="id_product_catalog",
            required=True,

            value=MovementProductCatalogAddEditFormState.id_product_catalog,

            on_change=MovementProductCatalogAddEditFormState.on_change_id_product_catalog,

            width="100%"
        ),
        rx.hstack(
            rx.spacer(),
            rx.cond(
                AppState.get_user_actions.contains(ActionEnum.PRODUCTS_CREATE),
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
        create_product_dialog(),
        rx.hstack(
            rx.text("Кількість:"),
            rx.input(
                name="count",
                type="number",
                min="0",
                step="1",
                required=True,
                is_invalid=MovementProductCatalogAddEditFormState.error_count,
                color_scheme=rx.cond(
                    MovementProductCatalogAddEditFormState.error_count,
                    "red",
                    "None"
                ),
                style=rx.cond(
                    MovementProductCatalogAddEditFormState.error_count,
                    {
                        "border": "2px solid red",
                        "box-shadow": "0 0 0 1px red"
                    },
                    {}
                ),

                value=MovementProductCatalogAddEditFormState.count,
                on_change=MovementProductCatalogAddEditFormState.on_change_count
            ),

            width="100%"
        ),
        rx.hstack(
            rx.text("Вартість за одиницю:"),
            rx.input(
                name="price",
                type="number",
                min="0",
                step="0.01",
                required=True,
                is_invalid=MovementProductCatalogAddEditFormState.error_price,
                color_scheme=rx.cond(
                    MovementProductCatalogAddEditFormState.error_price,
                    "red",
                    "None"
                ),
                style=rx.cond(
                    MovementProductCatalogAddEditFormState.error_price,
                    {
                        "border": "1px solid red",
                        "box-shadow": "0 0 0 1px red"
                    },
                    {}
                ),

                value=MovementProductCatalogAddEditFormState.price,
                on_change=MovementProductCatalogAddEditFormState.on_change_price
            ),

            width="100%"
        ),

        rx.cond(MovementProductCatalogAddEditFormState.product_is_uniq,
            rx.accordion.root(
                rx.accordion.item(
                    header=rx.text("Серійні номери"),
                    content=rx.scroll_area(
                        rx.vstack(
                            rx.foreach(
                                MovementProductCatalogAddEditFormState.item_products_list,
                                lambda item: rx.hstack(
                                    rx.input(
                                        type="text",

                                        value=item[1].serial_number,
                                        on_change=MovementProductCatalogAddEditFormState.on_change_serial_numbers(
                                            item[0]),

                                        width="100%"
                                    ),
                                    width="100%"
                                ),
                            ),

                            width="100%",
                            height="100%",
                        ),

                        padding="0.5em",
                        width="100%",
                        height="8em",
                    )
                ),

                collapsible=True,
                variant="outline",

                width="100%"
            ),
        ),
    )

def movement_product_catalog_detailed_view_form() -> rx.Component:
    return rx.vstack(
        rx.text("Товари з каталогу:", width="100%"),
        rx.text(
            MovementProductCatalogDetailedViewState.item.product.title,
            weight="bold",
            decoration="underline",
            width="100%"
        ),
        rx.hstack(
            rx.text("Кількість:"),
            rx.text(
                MovementProductCatalogDetailedViewState.item.count,
                weight="bold",
                decoration="underline",
                width="100%"
            )
        ),
        rx.hstack(
            rx.text("Вартість за одиницю:"),
            rx.text(
                MovementProductCatalogDetailedViewState.item.price,
                weight="bold",
                decoration="underline",
                width="100%"
            )
        ),
        rx.cond(MovementProductCatalogDetailedViewState.item.product.uniq,
            rx.accordion.root(
                rx.accordion.item(
                    header=rx.text("Серійні номери"),
                    content=rx.scroll_area(
                        rx.vstack(
                            rx.foreach(
                                MovementProductCatalogDetailedViewState.item_products_list,
                                lambda item: rx.hstack(
                                    rx.text(
                                        rx.cond(item[1].serial_number, item[1].serial_number, "-"),
                                        text_align="center",
                                        width="100%"
                                    ),
                                    width="100%"
                                ),
                            ),

                            width="100%",
                            height="100%",
                        ),

                        padding="0.5em",
                        width="100%",
                        height="8em",
                    )
                ),

                collapsible=True,
                variant="outline",

                width="100%"
            ),
        ),
    )

def add_admission_products_catalog_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Інформація про товар"),
            rx.tabs.root(
                rx.tabs.content(
                    movement_product_catalog_add_edit_form(),
                    value=AddAdmissionState.ProductCatalogDialogPages.EDIT,

                    width="100%",
                    height="100%"
                ),
                rx.tabs.content(
                    movement_product_catalog_detailed_view_form(),
                    value=AddAdmissionState.ProductCatalogDialogPages.VIEW,

                    width="100%",
                    height="100%"
                ),

                default_value=AddAdmissionState.ProductCatalogDialogPages.EMPTY,
                value=AddAdmissionState.product_catalog_dialog_page,
            ),
            rx.cond(AddAdmissionState.is_product_dialog_view_mode,
                    rx.hstack(
                        rx.button("Видалити", variant="outline", color_scheme="red",
                                  on_click=AddAdmissionState.on_close_product_catalog_dialog),
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

            width="30em"
        ),

        open=AddAdmissionState.is_open_product_catalog_dialog,
        on_open_change=AddAdmissionState.on_close_product_catalog_dialog,
    )

def product_catalog_table_row(item: Tuple[int, MovementProductsCatalog]):
    return rx.table.row(
        rx.table.cell(rx.link(item[1].product.title, on_click=AddAdmissionState.view_product_catalog_dialog(item[0]))),
        rx.table.cell(item[1].count),
        rx.table.cell(item[1].price)
    )

def product_catalog_table():
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Товар", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Кількість", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Вартість", color=rx.color("accent", 2)),
            ),

            background_color=rx.color("accent", 9)
        ),
        rx.table.body(
            rx.foreach(
                enumerate(AddAdmissionState.item.products),
                lambda item: product_catalog_table_row(item)
            ),

            height="100%",
            width="100%"
        ),

        variant="surface",
        height="100%",
        width="100%"
    )

def add_admission_products_catalog_table() -> rx.Component:
    return rx.vstack(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Товар", color=rx.color("accent", 2)),
                    rx.table.column_header_cell("Кількість", color=rx.color("accent", 2)),
                    rx.table.column_header_cell("Вартість", color=rx.color("accent", 2)),
                ),

                background_color=rx.color("accent", 9)
            ),
            rx.table.body(
                rx.foreach(
                    AddAdmissionState.item_movement_products_catalog_list,
                    lambda item: rx.table.row(
                        rx.table.cell(rx.link(item[1].product.title, on_click=AddAdmissionState.view_product_catalog_dialog(item[0]))),
                        rx.table.cell(item[1].count),
                        rx.table.cell(item[1].price)
                    )
                ),

                height="100%",
                width="100%"
            ),

            variant="surface",
            height="100%",
            width="100%"
        ),

        width="100%",
    )

def view_admission_products_catalog_table() -> rx.Component:
    return rx.vstack(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell("Товар", color=rx.color("accent", 2)),
                    rx.table.column_header_cell("Кількість", color=rx.color("accent", 2)),
                    rx.table.column_header_cell("Вартість", color=rx.color("accent", 2)),
                ),

                background_color=rx.color("accent", 9)
            ),
            rx.table.body(
                rx.foreach(
                    ViewAdmissionState.item_movement_products_catalog_list,
                    lambda item: rx.table.row(
                        rx.table.cell(rx.link(item[1].product.title, on_click=ViewAdmissionState.on_change_dialog_open(item[0]))),
                        rx.table.cell(item[1].count),
                        rx.table.cell(item[1].price)
                    )
                ),

                height="100%",
                width="100%"
            ),

            variant="surface",
            height="100%",
            width="100%"
        ),

        width="100%",
    )

def cancel_conflict_dialog() -> rx.Component:
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
                        on_click=ViewAdmissionState.set_cancel_conflict_dialog_open(False),
                    ),
                ),
                justify="end",
                margin_top="1em",
            ),
            max_width="42em",
        ),
        open=ViewAdmissionState.is_cancel_conflict_dialog_open,
        on_open_change=ViewAdmissionState.set_cancel_conflict_dialog_open,
    )


def item_preview() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            rx.text("Дата:"),
            rx.text(ViewAdmissionState.item.movement.date)
        ),
        rx.hstack(
            rx.text("Постачальник:"),
            rx.text(ViewAdmissionState.item.supplier.title)
        ),
        rx.hstack(
            rx.text("Одержувач:"),
            rx.text(ViewAdmissionState.item.movement.destination_owner.title)
        ),
        rx.hstack(
            rx.text("Склад:"),
            rx.text(ViewAdmissionState.item.movement.destination_storage.title)
        ),
        rx.text("Товари з каталогу:", width="100%"),
        view_admission_products_catalog_table(),
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("Інформація про товар"),
                movement_product_catalog_detailed_view_form(),

                width="30em"
            ),

            open=ViewAdmissionState.dialog_open,
            on_open_change=ViewAdmissionState.close_dialog
        ),
        rx.hstack(
            rx.text("Сума без ПДВ:"),
            rx.text(ViewAdmissionState.subtotal_display)
        ),
        rx.hstack(
            rx.text("Ставка ПДВ:"),
            rx.text(ViewAdmissionState.nds_rate_title)
        ),
        rx.hstack(
            rx.text("Сума ПДВ:"),
            rx.text(ViewAdmissionState.nds_amount_display)
        ),
        rx.hstack(
            rx.text("Разом з ПДВ:"),
            rx.text(ViewAdmissionState.total_display)
        ),
        rx.hstack(
            rx.text("ПДВ включений у ціну:"),
            rx.text(rx.cond(ViewAdmissionState.item.flag_nds, "Так", "Ні"))
        ),
        rx.hstack(
            rx.text("Спосіб оплати:"),
            rx.text(ViewAdmissionState.item.payment_type.title)
        ),
        rx.hstack(
            rx.text("Номер накладної оплати:"),
            rx.text(ViewAdmissionState.invoice_number)
        ),
        rx.hstack(
            rx.text("Курс долара:"),
            rx.text(ViewAdmissionState.item.dollar_rate)
        ),
        rx.hstack(
            rx.text("Статус:"),
            rx.text(ViewAdmissionState.item_status)
        ),
        rx.hstack(
            rx.text("Коментар:"),
            rx.text(ViewAdmissionState.item.movement.comment)
        ),

        spacing="3",
        align="stretch",

        height="100%",
        width="100%"
    )

def item_preview_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            cancel_conflict_dialog(),
            subpage_header(
                "Постачання/Перегляд",
                left=rx.button(
                    "Повернутись",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(routes.MOVEMENT_ADMISSIONS),
                ),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.ADMISSIONS_EDIT),
                        rx.button(
                            "Редагувати",
                            variant="ghost",
                            size="3",
                            on_click=rx.redirect(
                                f"{routes.MOVEMENT_ADMISSIONS_EDIT_ID}{ViewAdmissionState.item.id}"
                            ),
                        ),
                    ),
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.ADMISSIONS_DELETE),
                        rx.button(
                            "Видалити",
                            color_scheme="red",
                            variant="ghost",
                            size="3",
                            on_click=AdmissionState.delete_one(ViewAdmissionState.item.id),
                        ),
                    ),
                ],
            ),
            item_preview(),
            width="100%",
        ),
        value=AdmissionState.Pages.VIEW
    )

def table_row(item: Tuple[int, Admission]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item[1].id)),
        rx.table.row_header_cell(
            rx.link(
                item[1].movement.date,
                href=f"{routes.MOVEMENT_ADMISSIONS_VIEW_ID}{item[1].id}"
            ),

            align="left"
        ),
        rx.table.cell(rx.text(item[1].supplier.title)),
        rx.table.cell(rx.text(item[1].movement.destination_storage.title)),
        rx.table.cell(rx.text(item[1].movement.destination_owner.title)),
        rx.table.cell(rx.text(item[1].payment_type.title)),
        rx.table.cell(rx.text(item[1].movement.total_cost)),
        rx.table.cell(rx.text(rx.cond(item[1].flag_nds, "Так", "Ні"))),
        rx.table.cell(rx.text(ListAdmissionState.get_movement_statuses[item[1].movement.status]))
    )

def table() -> rx.Component:
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

            background_color=rx.color("accent", 9)
        ),
        rx.table.body(
            rx.foreach(ListAdmissionState.get_items, table_row),

            height="100%",
            width="100%"
        ),

        variant="surface",
        height="100%",
        width="100%"
    )

def list_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            subpage_header(
                "Постачання",
                actions=[
                    filter_button(ListAdmissionState),
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.ADMISSIONS_CREATE),
                        rx.button(
                            "Додати",
                            variant="ghost",
                            size="3",
                            on_click=rx.redirect(routes.MOVEMENT_ADMISSIONS_ADD),
                        ),
                    ),
                ],
            ),
            filter_card(ListAdmissionState),
            rx.cond(ListAdmissionState.has_items,
                table(),
                rx.text("Записів немає.")
            ),
            pagination(ListAdmissionState),

            width="100%",
            height="100%",
        ),

        value=AdmissionState.Pages.LIST,
    )

def add_form() -> rx.Component:
    return rx.card(
            rx.vstack(
                rx.text("Дата:"),
                rx.input(name="date", type="date", required=True, size="3", default_value=AddAdmissionState.item.movement.date, width="100%", on_change=AddAdmissionState.on_change_date),
                rx.text("Постачальник:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Оберіть зі списку",
                        width="100%",
                    ),
                    rx.select.content(
                        rx.foreach(
                            AddAdmissionState.list_suppliers,
                            lambda supplier: rx.select.item(supplier[0], value=supplier[1])
                        ),
                        width="100%",
                    ),

                    name="id_supplier",
                    required=True,

                    value=AddAdmissionState.id_supplier,

                    on_change=AddAdmissionState.on_change_id_supplier
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
                                    "Поиск",
                                    type="button",

                                    on_click=AddAdmissionState.on_click_search_name_destination_storage
                                ),
                                rx.input(
                                    placeholder="Введіть назву для пошуку",
                                    width="100%",

                                    value=AddAdmissionState.search_name_destination_storage,
                                    on_change=AddAdmissionState.on_change_search_name_destination_storage,
                                ),

                                width="100%"
                            ),

                            rx.foreach(
                                AddAdmissionState.list_storages,
                                lambda storage: rx.select.item(storage[0], value=storage[1], width="100%")
                            ),

                            width="100%",
                        ),

                        width="100%",
                    ),

                    name="id_destination_storage",
                    required=True,

                    value=AddAdmissionState.id_destination_storage,

                    on_change=AddAdmissionState.on_change_id_destination_storage
                ),
                rx.text("Одержувач:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Оберіть зі списку",
                        width="100%",
                    ),
                    rx.select.content(
                        rx.foreach(
                            AddAdmissionState.list_owners,
                            lambda owner: rx.select.item(owner[0], value=owner[1])
                        ),
                        width="100%",
                    ),

                    name="id_destination_owner",
                    required=True,

                    value=AddAdmissionState.id_destination_owner,

                    on_change=AddAdmissionState.on_change_id_destination_owner
                ),
                rx.text("Товари з каталогу:"),
                add_admission_products_catalog_dialog(),
                rx.cond(AddAdmissionState.has_item_movement_products_catalog,
                        add_admission_products_catalog_table(),
                        rx.center(rx.text("Нічого не обрано", color="gray"), width="100%", size="3")),
                rx.button(
                    "Додати",

                    on_click=AddAdmissionState.add_product_catalog_dialog_open
                ),
                rx.text("Спосіб оплати:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Оберіть зі списку",
                        width="100%",
                    ),
                    rx.select.content(
                        rx.foreach(
                            AddAdmissionState.list_payment_types,
                            lambda payment_type: rx.select.item(payment_type[0], value=payment_type[1])
                        ),
                        width="100%",
                    ),

                    name="id_payment_type",
                    required=True,

                    value=AddAdmissionState.id_payment_type,

                    on_change=AddAdmissionState.on_change_id_payment_type
                ),
                rx.text("Номер накладної оплати:"),
                rx.input(
                    name="invoice_number",
                    value=AddAdmissionState.invoice_number,
                    on_change=AddAdmissionState.on_change_invoice_number,
                ),
                rx.text("Ставка ПДВ:"),
                rx.hstack(
                    rx.select.root(
                        rx.select.trigger(
                            placeholder="Без ПДВ",
                            width="100%",
                        ),
                        rx.select.content(
                            rx.select.item("Без ПДВ", value="None"),
                            rx.foreach(
                                AddAdmissionState.list_nds_rates,
                                lambda nr: rx.select.item(nr[0], value=nr[1])
                            ),
                            width="100%",
                        ),
                        name="id_nds_rate",
                        value=AddAdmissionState.id_nds_rate,
                        on_change=AddAdmissionState.on_change_id_nds_rate,
                        width="100%",
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
                rx.hstack(
                    rx.switch(
                        name="flag_nds",
                        default_value=False,

                        value=AddAdmissionState.flag_nds,

                        on_change=AddAdmissionState.on_change_flag_nds
                    ),
                    rx.text("Ціна в рядках вказана з ПДВ")
                ),
                rx.vstack(
                    rx.hstack(rx.text("Сума без ПДВ:"), rx.text(AddAdmissionState.subtotal_display)),
                    rx.hstack(rx.text("Сума ПДВ:"), rx.text(AddAdmissionState.nds_amount_display)),
                    rx.hstack(rx.text("Разом з ПДВ:"), rx.text(AddAdmissionState.total_display)),
                    width="100%",
                ),
                rx.hstack(
                    rx.text("Курс долара:"),
                    rx.input(
                        name="dollar_rate",
                        required=True,

                        value=AddAdmissionState.dollar_rate,

                        on_change=AddAdmissionState.on_change_dollar_rate
                    )
                ),
                rx.hstack(
                    rx.text("Статус:"),
                    rx.select(
                        AddAdmissionState.editable_statuses,

                        name="status",
                        placeholder="Оберіть зі списку",
                        required=True,

                        value=AddAdmissionState.status,

                        on_change=AddAdmissionState.on_change_status
                    ),
                ),
                rx.text("Коментар:"),
                rx.text_area(name="comment", value=AddAdmissionState.item.movement.comment, on_change=AddAdmissionState.on_change_comment, width="100%"),

                spacing="3",
                align="stretch",
                width="100%",
            ),

        height="100%",
        width="100%"
    )

def edit_form() -> rx.Component:
    return rx.card(
            rx.vstack(
                rx.text("Дата:"),
                rx.input(name="date", type="date", required=True, size="3", default_value=EditAdmissionState.item.movement.date, disabled=True),
                rx.text("Постачальник:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Оберіть зі списку",
                        width="100%",
                    ),
                    rx.select.content(
                        rx.foreach(
                            EditAdmissionState.list_suppliers,
                            lambda supplier: rx.select.item(supplier[0], value=supplier[1])
                        ),
                        width="100%",
                    ),

                    name="id_supplier",
                    required=True,
                    disabled=True,

                    value=EditAdmissionState.id_supplier,
                    default_value=EditAdmissionState.id_supplier,

                    on_change=EditAdmissionState.on_change_id_supplier
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
                                    "Поиск",
                                    type="button",

                                    on_click=EditAdmissionState.on_click_search_name_destination_storage
                                ),
                                rx.input(
                                    placeholder="Введіть назву для пошуку",
                                    width="100%",

                                    value=EditAdmissionState.search_name_destination_storage,
                                    on_change=EditAdmissionState.on_change_search_name_destination_storage,
                                ),

                                width="100%"
                            ),

                            rx.foreach(
                                EditAdmissionState.list_storages,
                                lambda storage: rx.select.item(storage[0], value=storage[1], width="100%")
                            ),

                            width="100%",
                        ),

                        width="100%",
                    ),

                    name="id_destination_storage",
                    required=True,
                    disabled=True,

                    value=EditAdmissionState.id_destination_storage,
                    default_value=EditAdmissionState.id_destination_storage,

                    on_change=EditAdmissionState.on_change_id_destination_storage
                ),
                rx.text("Одержувач:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Оберіть зі списку",
                        width="100%",
                    ),
                    rx.select.content(
                        rx.foreach(
                            EditAdmissionState.list_owners,
                            lambda owner: rx.select.item(owner[0], value=owner[1])
                        ),
                        width="100%",
                    ),

                    name="id_destination_owner",
                    required=True,
                    disabled=True,

                    value=EditAdmissionState.id_destination_owner,

                    on_change=EditAdmissionState.on_change_id_destination_owner
                ),
                rx.text("Товари з каталогу:"),
                add_admission_products_catalog_dialog(),
                rx.cond(EditAdmissionState.has_item_movement_products_catalog,
                        add_admission_products_catalog_table(),
                        rx.center(rx.text("Нічого не обрано", color="gray"), width="100%", size="3")),
                rx.text("Спосіб оплати:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Оберіть зі списку",
                        width="100%",
                    ),
                    rx.select.content(
                        rx.foreach(
                            EditAdmissionState.list_payment_types,
                            lambda payment_type: rx.select.item(payment_type[0], value=payment_type[1])
                        ),
                        width="100%",
                    ),

                    name="id_payment_type",
                    required=True,
                    disabled=True,

                    value=EditAdmissionState.id_payment_type,

                    on_change=EditAdmissionState.on_change_id_payment_type
                ),
                rx.text("Номер накладної оплати:"),
                rx.input(
                    name="invoice_number",
                    value=EditAdmissionState.invoice_number,
                    on_change=EditAdmissionState.on_change_invoice_number,
                ),
                rx.text("Ставка ПДВ:"),
                rx.hstack(
                    rx.select.root(
                        rx.select.trigger(
                            placeholder="Без ПДВ",
                            width="100%",
                        ),
                        rx.select.content(
                            rx.select.item("Без ПДВ", value="None"),
                            rx.foreach(
                                EditAdmissionState.list_nds_rates,
                                lambda nr: rx.select.item(nr[0], value=nr[1])
                            ),
                            width="100%",
                        ),
                        name="id_nds_rate",
                        value=EditAdmissionState.id_nds_rate,
                        on_change=EditAdmissionState.on_change_id_nds_rate,
                        width="100%",
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
                    rx.switch(
                        name="flag_nds",
                        default_value=False,
                        disabled=True,

                        value=EditAdmissionState.flag_nds,

                        on_change=EditAdmissionState.on_change_flag_nds
                    ),
                    rx.text("Ціна в рядках вказана з ПДВ")
                ),
                rx.vstack(
                    rx.hstack(rx.text("Сума без ПДВ:"), rx.text(EditAdmissionState.subtotal_display)),
                    rx.hstack(rx.text("Сума ПДВ:"), rx.text(EditAdmissionState.nds_amount_display)),
                    rx.hstack(rx.text("Разом з ПДВ:"), rx.text(EditAdmissionState.total_display)),
                    width="100%",
                ),
                rx.hstack(
                    rx.text("Курс долара:"),
                    rx.input(
                        name="dollar_rate",
                        required=True,
                        disabled=True,

                        value=EditAdmissionState.dollar_rate,

                        on_change=EditAdmissionState.on_change_dollar_rate
                    )
                ),
                rx.hstack(
                    rx.text("Статус:"),
                    rx.select(
                        EditAdmissionState.get_movement_statuses,

                        name="status",
                        placeholder="Оберіть зі списку",
                        required=True,

                        value=EditAdmissionState.status,

                        on_change=EditAdmissionState.on_change_status
                    ),
                ),
                rx.text("Коментар:"),
                rx.text_area(name="comment", value=EditAdmissionState.item.movement.comment, on_change=EditAdmissionState.on_change_comment, width="100%"),

                spacing="3",
                align="stretch",
                width="100%",
            ),

        height="100%",
        width="100%"
    )

def add_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            subpage_header(
                "Постачання/Додавання",
                left=rx.button(
                    "Скасувати",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(routes.MOVEMENT_ADMISSIONS),
                ),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.ADMISSIONS_CREATE),
                        rx.button(
                            "Зберегти",
                            variant="ghost",
                            size="3",
                            on_click=AddAdmissionState.add_one,
                        ),
                    ),
                ],
            ),
            add_form(),
            width="100%",
        ),
        value=AdmissionState.Pages.ADD
    )

def edit_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            subpage_header(
                "Постачання/Редагування",
                left=rx.button(
                    "Скасувати",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(routes.MOVEMENT_ADMISSIONS),
                ),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.ADMISSIONS_EDIT),
                        rx.button(
                            "Зберегти",
                            variant="ghost",
                            size="3",
                            on_click=EditAdmissionState.edit_one,
                        ),
                    ),
                ],
            ),
            edit_form(),
            width="100%",
        ),
        value=AdmissionState.Pages.EDIT
    )

def index() -> rx.Component:
    return rx.tabs.root(
        rx.cond(AppState.get_user_actions.contains(ActionEnum.ADMISSIONS_LIST),
            list_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.ADMISSIONS_CREATE),
            add_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.ADMISSIONS_EDIT),
            edit_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.ADMISSIONS_VIEW),
            item_preview_tab_content()),

        value=AdmissionState.current_page,

        height="100%",
        width="100%"
    )
