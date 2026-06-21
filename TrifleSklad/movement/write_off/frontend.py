import reflex as rx

from components.elements import subpage_header

from TrifleSklad import routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.movement.write_off.backend import (
    AddWriteOffState,
    EditWriteOffState,
    ListWriteOffState,
    ViewWriteOffState,
    WriteOffState,
)
from TrifleSklad.movement.products.frontend import index as products
from TrifleSklad.movement.list_components import filter_button, filter_card, filter_select, pagination
from TrifleSklad.movement.inline_creator_components import (
    create_lookup_button,
    owner_create_dialog,
    storage_create_dialog,
)
from TrifleSklad.declared import StorageType

from TrifleSklad.models import Movement
from TrifleSklad.state import AppState


def cancel_conflict_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Скасування неможливе"),
            rx.dialog.description(
                "Товар із цього списання бере участь у наведених нижче рухах. "
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
                        ViewWriteOffState.cancel_conflict_rows,
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
                        on_click=ViewWriteOffState.set_cancel_conflict_dialog_open(False),
                    ),
                ),
                justify="end",
                margin_top="1em",
            ),
            max_width="42em",
        ),
        open=ViewWriteOffState.is_cancel_conflict_dialog_open,
        on_open_change=ViewWriteOffState.set_cancel_conflict_dialog_open,
    )


def item_preview() -> rx.Component:
    return rx.vstack(
        cancel_conflict_dialog(),
        rx.hstack(
            rx.text("Дата:"),
            rx.text(ViewWriteOffState.item.date)
        ),
        rx.hstack(
            rx.text("Склад:"),
            rx.text(ViewWriteOffState.item.incoming_storage.title)
        ),
        rx.hstack(
            rx.text("Власник:"),
            rx.text(ViewWriteOffState.item.incoming_owner.title)
        ),
        products(width="100%"),
        rx.hstack(
            rx.text("Статус:"),
            rx.text(ViewWriteOffState.item_status)
        ),
        rx.hstack(
            rx.text("Коментар:"),
            rx.text(ViewWriteOffState.item.comment)
        ),
        spacing="3",
        align="stretch",
        height="100%",
        width="100%"
    )


def item_preview_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            subpage_header(
                "Списання/Перегляд",
                left=rx.button(
                    "Повернутись",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(routes.MOVEMENT_WRITE_OFFS),
                ),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.WRITE_OFFS_EDIT)
                        & (ViewWriteOffState.current_is_canceled == False),
                        rx.button(
                            "Редагувати",
                            variant="ghost",
                            size="3",
                            on_click=rx.redirect(
                                f"{routes.MOVEMENT_WRITE_OFFS_EDIT_ID}{ViewWriteOffState.item.id}"
                            ),
                        ),
                    ),
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.WRITE_OFFS_DELETE)
                        & (ViewWriteOffState.current_is_canceled == False),
                        rx.button(
                            "Скасувати",
                            color_scheme="red",
                            variant="ghost",
                            size="3",
                            on_click=WriteOffState.delete_one(ViewWriteOffState.item.id),
                        ),
                    ),
                ],
            ),
            item_preview(),
            width="100%",
        ),
        value=WriteOffState.Pages.VIEW,
    )


def table_row(item: Movement) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item.id)),
        rx.table.row_header_cell(
            item.date,
            align="left"
        ),
        rx.table.cell(rx.text(item.incoming_storage.title)),
        rx.table.cell(rx.text(item.incoming_owner.title)),
        rx.table.cell(rx.text(ListWriteOffState.get_movement_statuses[item.status])),
        on_click=rx.redirect(f"{routes.MOVEMENT_WRITE_OFFS_VIEW_ID}{item.id}"),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("№", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Дата", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Склад", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Власник", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Статус", color=rx.color("accent", 2)),
            ),

            background_color=rx.color("accent", 9)
        ),
        rx.table.body(
            rx.foreach(ListWriteOffState.items, table_row),

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
                "Списання",
                actions=[
                    filter_button(ListWriteOffState),
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.WRITE_OFFS_CREATE),
                        rx.button(
                            "Додати",
                            variant="ghost",
                            size="3",
                            on_click=rx.redirect(routes.MOVEMENT_WRITE_OFFS_ADD),
                        ),
                    ),
                ],
            ),
            filter_card(
                ListWriteOffState,
                filter_select(
                    "Склад",
                    ListWriteOffState.filter_incoming_storage,
                    ListWriteOffState.list_warehouses,
                    ListWriteOffState.on_change_filter_incoming_storage,
                ),
                filter_select(
                    "Власник",
                    ListWriteOffState.filter_incoming_owner,
                    ListWriteOffState.list_owners,
                    ListWriteOffState.on_change_filter_incoming_owner,
                ),
            ),
            rx.cond(
                ListWriteOffState.has_items,
                table(),
                rx.text("Записів немає.")
            ),
            pagination(ListWriteOffState),
            width="100%",
            height="100%",
        ),
        value=WriteOffState.Pages.LIST,
    )


def add_form() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text("*Дата:"),
            rx.input(
                value=AddWriteOffState.current_date,
                on_change=AddWriteOffState.on_change_date,
                type="date",
                required=True,
                size="3",
                width="100%",
            ),
            rx.text("*Склад:"),
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
                                on_click=AddWriteOffState.on_click_search_name_incoming_storage,
                            ),
                            rx.input(
                                value=AddWriteOffState.search_name_incoming_storage,
                                on_change=AddWriteOffState.on_change_search_name_incoming_storage,
                                placeholder="Введіть назву для пошуку",
                                width="100%",
                            ),
                            width="100%",
                        ),
                        rx.foreach(
                            AddWriteOffState.list_storages,
                            lambda storage: rx.select.item(storage[0], value=storage[1], width="100%"),
                        ),
                        width="100%",
                    ),
                    width="100%",
                ),
                required=True,
                value=AddWriteOffState.id_incoming_storage,
                on_change=AddWriteOffState.on_change_id_incoming_storage,
            ),
            create_lookup_button(ActionEnum.STORAGE_CREATE, "Створити склад", AddWriteOffState.open_storage_create(StorageType.WAREHOUSE, "incoming", False)),
            storage_create_dialog(AddWriteOffState),
            rx.text("*Власник:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%",
                ),
                rx.select.content(
                    rx.foreach(
                        AddWriteOffState.list_owners,
                        lambda owner: rx.select.item(owner[0], value=owner[1]),
                    ),
                    width="100%",
                ),
                required=True,
                value=AddWriteOffState.id_incoming_owner,
                on_change=AddWriteOffState.on_change_id_incoming_owner,
            ),
            create_lookup_button(ActionEnum.OWNERS_CREATE, "Створити власника", AddWriteOffState.open_owner_create),
            owner_create_dialog(AddWriteOffState),
            products(width="100%"),
            rx.hstack(
                rx.text("*Статус:"),
                rx.select(
                    AddWriteOffState.editable_statuses,
                    placeholder="Оберіть зі списку",
                    required=True,
                    value=AddWriteOffState.status,
                    on_change=AddWriteOffState.on_change_status,
                ),
            ),
            rx.text("Коментар:"),
            rx.text_area(value=AddWriteOffState.comment, on_change=AddWriteOffState.on_change_comment, width="100%"),

            spacing="3",
            align="stretch",
            width="100%",
        ),

        height="100%",
        width="100%",
    )


def edit_form() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text("*Дата:"),
            rx.input(
                value=EditWriteOffState.item.date,
                type="date",
                required=True,
                size="3",
                disabled=True,
                width="100%",
            ),
            rx.text("*Склад:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%",
                ),
                rx.select.content(
                    rx.foreach(
                        EditWriteOffState.list_storages,
                        lambda storage: rx.select.item(storage[0], value=storage[1], width="100%"),
                    ),
                    width="100%",
                ),
                required=True,
                disabled=True,
                value=EditWriteOffState.id_incoming_storage,
                on_change=EditWriteOffState.on_change_id_incoming_storage,
            ),
            rx.text("*Власник:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%",
                ),
                rx.select.content(
                    rx.foreach(
                        EditWriteOffState.list_owners,
                        lambda owner: rx.select.item(owner[0], value=owner[1]),
                    ),
                    width="100%",
                ),
                required=True,
                disabled=True,
                value=EditWriteOffState.id_incoming_owner,
                on_change=EditWriteOffState.on_change_id_incoming_owner,
            ),
            products(width="100%"),
            rx.hstack(
                rx.text("*Статус:"),
                rx.select(
                    EditWriteOffState.editable_statuses,
                    placeholder="Оберіть зі списку",
                    required=True,
                    value=EditWriteOffState.status,
                    on_change=EditWriteOffState.on_change_status,
                ),
            ),
            rx.text("Коментар:"),
            rx.text_area(value=EditWriteOffState.item.comment, on_change=EditWriteOffState.on_change_comment, width="100%"),

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
                "Списання/Додавання",
                left=rx.button(
                    "Скасувати",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(routes.MOVEMENT_WRITE_OFFS),
                ),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.WRITE_OFFS_CREATE),
                        rx.button(
                            "Зберегти і продовжити",
                            variant="ghost",
                            size="3",
                            on_click=AddWriteOffState.add_one(True),
                        ),
                    ),
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.WRITE_OFFS_CREATE),
                        rx.button(
                            "Зберегти",
                            variant="ghost",
                            size="3",
                            on_click=AddWriteOffState.add_one(False),
                        ),
                    ),
                ],
            ),
            add_form(),
            width="100%",
        ),
        value=WriteOffState.Pages.ADD,
    )


def edit_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            subpage_header(
                "Списання/Редагування",
                left=rx.button(
                    "Скасувати",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(
                        f"{routes.MOVEMENT_WRITE_OFFS_VIEW_ID}{EditWriteOffState.item.id}"
                    ),
                ),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.WRITE_OFFS_EDIT),
                        rx.button(
                            "Зберегти",
                            variant="ghost",
                            size="3",
                            on_click=EditWriteOffState.edit_one,
                        ),
                    ),
                ],
            ),
            edit_form(),
            width="100%",
        ),
        value=WriteOffState.Pages.EDIT,
    )


def index() -> rx.Component:
    return rx.tabs.root(
        rx.cond(AppState.get_user_actions.contains(ActionEnum.WRITE_OFFS_LIST),
            list_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.WRITE_OFFS_CREATE),
            add_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.WRITE_OFFS_EDIT),
            edit_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.WRITE_OFFS_VIEW),
            item_preview_tab_content()),

        value=WriteOffState.current_page,

        height="100%",
        width="100%",
    )
