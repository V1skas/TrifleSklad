import reflex as rx
from docutils.nodes import decoration

from TrifleSklad.declared import movements_status_list

from TrifleSklad import routes
from TrifleSklad.movement.admissions.backend import *
from TrifleSklad.movement.products_catalog.frontend import index as products_catalog_table

from TrifleSklad.movement.admissions.backend import AdmissionState, AddAdmissionState, MovementProductCatalogAddEditFormState, MovementProductCatalogDetailedViewState
from TrifleSklad.models import Admission
from TrifleSklad.declared import MovementsStatus

def movement_product_catalog_add_edit_form() -> rx.Component:
    return rx.vstack(
        rx.text("Наименование из каталога:", width="100%"),
        rx.select.root(
            rx.select.trigger(
                placeholder="Выберите из списка",
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
            rx.text("Количество:"),
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
            rx.text("Стоимость за единицу:"),
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
                    header=rx.text("Серийные номера"),
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
        rx.text("Товары из каталога:", width="100%"),
        rx.text(
            MovementProductCatalogDetailedViewState.item.product.title,
            weight="bold",
            decoration="underline",
            width="100%"
        ),
        rx.hstack(
            rx.text("Количество:"),
            rx.text(
                MovementProductCatalogDetailedViewState.item.count,
                weight="bold",
                decoration="underline",
                width="100%"
            )
        ),
        rx.hstack(
            rx.text("Стоимость за единицу:"),
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
                    header=rx.text("Серийные номера"),
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
            rx.dialog.title("Информация о товаре"),
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
                        rx.button("Удалить", variant="outline", color_scheme="red",
                                  on_click=AddAdmissionState.on_close_product_catalog_dialog),
                        rx.spacer(),
                        rx.button("Редактировать", type="button", on_click=AddAdmissionState.edit_product_catalog_dialog),

                        padding_top="1em",

                        width="100%",
                    ),
                    rx.hstack(
                        rx.button("Отменить", variant="outline", on_click=AddAdmissionState.on_close_product_catalog_dialog),
                        rx.spacer(),
                        rx.button("Сохранить", disabled=MovementProductCatalogAddEditFormState.has_errors, on_click=AddAdmissionState.on_save_product_catalog_dialog),

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
                rx.table.column_header_cell("Количество", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Стоимость", color=rx.color("accent", 2)),
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
                    rx.table.column_header_cell("Количество", color=rx.color("accent", 2)),
                    rx.table.column_header_cell("Стоимость", color=rx.color("accent", 2)),
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
                    rx.table.column_header_cell("Количество", color=rx.color("accent", 2)),
                    rx.table.column_header_cell("Стоимость", color=rx.color("accent", 2)),
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

def item_preview() -> rx.Component:
    return rx.vstack(
        rx.heading(f"Поставка №{ViewAdmissionState.item.id}", size="7", width="100%"),
        rx.hstack(
            rx.text("Дата:"),
            rx.text(ViewAdmissionState.item.movement.date)
        ),
        rx.hstack(
            rx.text("Поставщик:"),
            rx.text(ViewAdmissionState.item.supplier.title)
        ),
        rx.hstack(
            rx.text("Получатель:"),
            rx.text(ViewAdmissionState.item.movement.destination_owner.title)
        ),
        rx.hstack(
            rx.text("Склад:"),
            rx.text(ViewAdmissionState.item.movement.destination_storage.title)
        ),
        rx.text("Товары из каталога:", width="100%"),
        view_admission_products_catalog_table(),
        rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("Информация о товаре"),
                movement_product_catalog_detailed_view_form(),

                width="30em"
            ),

            open=ViewAdmissionState.dialog_open,
            on_open_change=ViewAdmissionState.close_dialog
        ),
        rx.hstack(
            rx.text("Итоговая стоимость:"),
            rx.text(f"{ViewAdmissionState.item.movement.total_cost}")
        ),
        rx.hstack(
            rx.text("НДС:"),
            rx.text(rx.cond(ViewAdmissionState.item.flag_nds, "Есть", "Нет"))
        ),
        rx.hstack(
            rx.text("Способ оплаты:"),
            rx.text(ViewAdmissionState.item.payment_type.title)
        ),
        rx.hstack(
            rx.text("Курс доллара:"),
            rx.text(ViewAdmissionState.item.dollar_rate)
        ),
        rx.hstack(
            rx.text("Статус:"),
            rx.text(ViewAdmissionState.item_status)
        ),
        rx.hstack(
            rx.text("Комментарий:"),
            rx.text(ViewAdmissionState.item.movement.comment)
        ),
        rx.spacer(),
        rx.hstack(
            rx.button(
                "Редактировать",

                on_click=rx.redirect(f"{routes.MOVEMENT_ADMISSIONS_EDIT_ID}{ViewAdmissionState.item.id}")
            ),
            rx.spacer(),
            rx.button(
                "Удалить",
                color_scheme="red",

                on_click=AdmissionState.delete_one(ViewAdmissionState.item.id)
            ),

            width="100%",
        ),

        spacing="3",

        height="100%",
        width="100%"
    )

def item_preview_tab_content() -> rx.Component:
    return rx.tabs.content(
        item_preview(),

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
        rx.table.cell(rx.text(rx.cond(item[1].flag_nds, "Да", "Нет"))),
        rx.table.cell(rx.text(ListAdmissionState.get_movement_statuses[item[1].movement.status]))
    )

def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("№", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Дата", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Поставщик", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Склад", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Владелец", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Тип платежа", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Сумма", color=rx.color("accent", 2)),
                rx.table.column_header_cell("НДС", color=rx.color("accent", 2)),
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
            rx.hstack(
                rx.heading("Поставки", size="6"),
                rx.spacer(),
                rx.button(
                    "Добавить",
                    on_click=rx.redirect(routes.MOVEMENT_ADMISSIONS_ADD)
                ),

                width="100%"
            ),
            rx.cond(ListAdmissionState.has_items,
                table(),
                rx.text("Записей нет.")
            ),

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
                rx.text("Поставщик:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Выберите из списка",
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
                        placeholder="Выберите из списка",
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
                                    placeholder="Введите название для поиска",
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
                rx.text("Владелец:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Выберите из списка",
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
                rx.text("Товары из каталога:"),
                add_admission_products_catalog_dialog(),
                rx.cond(AddAdmissionState.has_item_movement_products_catalog,
                        add_admission_products_catalog_table(),
                        rx.center(rx.text("Ничего не выбрано", color="gray"), width="100%", size="3")),
                rx.button(
                    "Добавить",

                    on_click=AddAdmissionState.add_product_catalog_dialog_open
                ),
                rx.text("Способ оплаты:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Выберите из списка",
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
                rx.hstack(
                    rx.switch(
                        name="flag_nds",
                        default_value=False,

                        value=AddAdmissionState.flag_nds,

                        on_change=AddAdmissionState.on_change_flag_nds
                    ),
                    rx.text("НДС")
                ),
                rx.hstack(
                    rx.text("Курс доллара:"),
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
                        AddAdmissionState.get_movement_statuses,

                        name="status",
                        placeholder="Выберите из списка",
                        required=True,

                        value=AddAdmissionState.status,

                        on_change=AddAdmissionState.on_change_status
                    ),
                ),
                rx.text("Комментарий:"),
                rx.text_area(name="comment", value=AddAdmissionState.item.movement.comment, on_change=AddAdmissionState.on_change_comment),

                rx.hstack(
                    rx.button("Отмена", type="reset", color_scheme="red", on_click=rx.redirect(routes.MOVEMENT_ADMISSIONS)),
                    rx.button("Сохранить", color_scheme="green", type="submit", on_click=AddAdmissionState.add_one),

                    justify="end"
                ),

                align="stretch"
            ),

        height="100%",
        width="100%"
    )

def edit_form() -> rx.Component:
    return rx.card(
            rx.vstack(
                rx.text("Дата:"),
                rx.input(name="date", type="date", required=True, size="3", default_value=EditAdmissionState.item.movement.date, disabled=True),
                rx.text("Поставщик:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Выберите из списка",
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
                        placeholder="Выберите из списка",
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
                                    placeholder="Введите название для поиска",
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
                rx.text("Владелец:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Выберите из списка",
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
                rx.text("Товары из каталога:"),
                add_admission_products_catalog_dialog(),
                rx.cond(EditAdmissionState.has_item_movement_products_catalog,
                        add_admission_products_catalog_table(),
                        rx.center(rx.text("Ничего не выбрано", color="gray"), width="100%", size="3")),
                rx.text("Способ оплаты:"),
                rx.select.root(
                    rx.select.trigger(
                        placeholder="Выберите из списка",
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
                rx.hstack(
                    rx.switch(
                        name="flag_nds",
                        default_value=False,
                        disabled=True,

                        value=EditAdmissionState.flag_nds,

                        on_change=EditAdmissionState.on_change_flag_nds
                    ),
                    rx.text("НДС")
                ),
                rx.hstack(
                    rx.text("Курс доллара:"),
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
                        placeholder="Выберите из списка",
                        required=True,

                        value=EditAdmissionState.status,

                        on_change=EditAdmissionState.on_change_status
                    ),
                ),
                rx.text("Комментарий:"),
                rx.text_area(name="comment", value=EditAdmissionState.item.movement.comment, on_change=EditAdmissionState.on_change_comment),

                rx.hstack(
                    rx.button("Отмена", type="reset", color_scheme="red", on_click=rx.redirect(routes.MOVEMENT_ADMISSIONS)),
                    rx.button("Сохранить", color_scheme="green", type="submit", on_click=EditAdmissionState.edit_one),

                    justify="end"
                ),

                align="stretch"
            ),

        height="100%",
        width="100%"
    )

def add_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading("Добавление поставки", size="7", width="100%", margin_bottom="0.5em"),
        add_form(),

        value=AdmissionState.Pages.ADD
    )

def edit_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading("Редактирование поставки", size="7", width="100%", margin_bottom="0.5em"),
        edit_form(),

        value=AdmissionState.Pages.EDIT
    )

def index() -> rx.Component:
    return rx.tabs.root(
        list_tab_content(),
        add_tab_content(),
        edit_tab_content(),
        item_preview_tab_content(),

        value=AdmissionState.current_page,

        height="100%",
        width="100%"
    )
