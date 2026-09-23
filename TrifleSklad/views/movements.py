import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.declared import StorageType
from TrifleSklad.models import Movement
from TrifleSklad.movement.inline_creator_components import (
    create_lookup_button,
    owner_create_dialog,
    storage_create_dialog,
)
from TrifleSklad.movement.list_components import filter_button, filter_card, filter_select, pagination
from TrifleSklad.movement.products.frontend import index as products_widget
from TrifleSklad.states.movements import (
    AddMovementsState,
    EditMovementsState,
    ListMovementsState,
    ViewMovementsState,
)
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.templates import controls, full_edit
from TrifleSklad.views.templates.history import history_block
from TrifleSklad.views.templates.layouts import field_row, header_subpage, page_wrapper, titled_section


def _table_row(item: Movement) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item.id)),
        rx.table.row_header_cell(item.date, align="left"),
        rx.table.cell(rx.text(item.incoming_storage.title)),
        rx.table.cell(rx.text(item.incoming_owner.title)),
        rx.table.cell(rx.text(item.destination_storage.title)),
        rx.table.cell(rx.text(item.destination_owner.title)),
        rx.table.cell(rx.text(ListMovementsState.get_movement_statuses[item.status])),
        on_click=rx.redirect(f"{routes.MOVEMENT_MOVEMENTS_VIEW_ID}{item.id}"),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def _table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("№", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Дата", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Склад відправлення", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Власник відправлення", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Склад призначення", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Власник призначення", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Статус", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(rx.foreach(ListMovementsState.items, _table_row)),
        variant="surface",
        width="100%",
    )


def list_page_content() -> rx.Component:
    return rx.vstack(
        rx.cond(ListMovementsState.has_items, _table(), controls.empty_placeholder()),
        pagination(ListMovementsState),
        spacing="3",
        width="100%",
    )


@require_login
def list_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Переміщення",
            filter_button(ListMovementsState),
            rx.cond(
                ListMovementsState.get_user_actions.contains(Action.MOVEMENTS_CREATE),
                controls.button_primary("Створити", on_click=ListMovementsState.on_click_add),
            ),
            width="100%",
        ),
        rx.skeleton(list_page_content(), loading=ListMovementsState.in_progress, height="100%"),
        filter_panel=filter_card(
            ListMovementsState,
            filter_select(
                "Склад відправлення",
                ListMovementsState.filter_incoming_storage,
                ListMovementsState.list_warehouses,
                ListMovementsState.on_change_filter_incoming_storage,
            ),
            filter_select(
                "Власник відправлення",
                ListMovementsState.filter_incoming_owner,
                ListMovementsState.list_owners,
                ListMovementsState.on_change_filter_incoming_owner,
            ),
            filter_select(
                "Склад призначення",
                ListMovementsState.filter_destination_storage,
                ListMovementsState.list_warehouses,
                ListMovementsState.on_change_filter_destination_storage,
            ),
            filter_select(
                "Власник призначення",
                ListMovementsState.filter_destination_owner,
                ListMovementsState.list_owners,
                ListMovementsState.on_change_filter_destination_owner,
            ),
        ),
        on_mount=ListMovementsState.on_load,
    )


def _add_form() -> rx.Component:
    return rx.vstack(
        titled_section(
            "Загальна інформація",
            rx.text("*Дата:", weight="medium"),
            controls.input_field(
                value=AddMovementsState.current_date,
                on_change=AddMovementsState.on_change_date,
                type="date",
                required=True,
                width="100%",
            ),
            rx.text("*Склад відправлення:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.vstack(
                        controls.search_field(
                            value=AddMovementsState.search_name_incoming_storage,
                            on_change=AddMovementsState.on_change_search_name_incoming_storage,
                            placeholder="Введіть назву для пошуку",
                            width="100%",
                        ),
                        rx.foreach(
                            AddMovementsState.filtered_incoming_storages,
                            lambda storage: rx.select.item(storage[0], value=storage[1], width="100%"),
                        ),
                        width="100%",
                    ),
                    width="100%",
                ),
                required=True,
                value=AddMovementsState.id_incoming_storage,
                on_change=AddMovementsState.on_change_id_incoming_storage,
            ),
            create_lookup_button(
                Action.STORAGE_CREATE,
                "Створити склад",
                AddMovementsState.open_storage_create(StorageType.WAREHOUSE, "incoming", False),
            ),
            rx.text("*Власник відправлення:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(
                        AddMovementsState.list_owners,
                        lambda owner: rx.select.item(owner[0], value=owner[1]),
                    ),
                    width="100%",
                ),
                required=True,
                value=AddMovementsState.id_incoming_owner,
                on_change=AddMovementsState.on_change_id_incoming_owner,
            ),
            create_lookup_button(Action.OWNERS_CREATE, "Створити власника", AddMovementsState.open_owner_create("incoming")),
            owner_create_dialog(AddMovementsState),
            rx.text("*Склад призначення:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.vstack(
                        controls.search_field(
                            value=AddMovementsState.search_name_destination_storage,
                            on_change=AddMovementsState.on_change_search_name_destination_storage,
                            placeholder="Введіть назву для пошуку",
                            width="100%",
                        ),
                        rx.foreach(
                            AddMovementsState.filtered_destination_storages,
                            lambda storage: rx.select.item(storage[0], value=storage[1], width="100%"),
                        ),
                        width="100%",
                    ),
                    width="100%",
                ),
                required=True,
                value=AddMovementsState.id_destination_storage,
                on_change=AddMovementsState.on_change_id_destination_storage,
            ),
            create_lookup_button(
                Action.STORAGE_CREATE,
                "Створити склад",
                AddMovementsState.open_storage_create(StorageType.WAREHOUSE, "destination", False),
            ),
            storage_create_dialog(AddMovementsState),
            rx.text("*Власник призначення:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(
                        AddMovementsState.list_owners,
                        lambda owner: rx.select.item(owner[0], value=owner[1]),
                    ),
                    width="100%",
                ),
                required=True,
                value=AddMovementsState.id_destination_owner,
                on_change=AddMovementsState.on_change_id_destination_owner,
            ),
            create_lookup_button(Action.OWNERS_CREATE, "Створити власника", AddMovementsState.open_owner_create("destination")),
            rx.text("*Статус:", weight="medium"),
            rx.select(
                AddMovementsState.editable_statuses,
                placeholder="Оберіть зі списку",
                required=True,
                value=AddMovementsState.status,
                on_change=AddMovementsState.on_change_status,
            ),
            rx.text("Коментар:", weight="medium"),
            controls.text_area_field(value=AddMovementsState.comment, on_change=AddMovementsState.on_change_comment, width="100%"),
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
            "Переміщення/Додавання",
            controls.button_secondary("Зберегти і продовжити", on_click=AddMovementsState.add_one(True)),
            controls.button_primary("Зберегти", on_click=AddMovementsState.add_one(False)),
            left=controls.button_back(routes.MOVEMENT_MOVEMENTS, label="Скасувати"),
            width="100%",
        ),
        _add_form(),
        on_mount=AddMovementsState.on_load,
    )


def _edit_form() -> rx.Component:
    return rx.vstack(
        full_edit.full_edit_notice(EditMovementsState),
        full_edit.save_reason_dialog(EditMovementsState),
        titled_section(
            "Загальна інформація",
            rx.text("*Дата:", weight="medium"),
            controls.input_field(value=EditMovementsState.item.date, type="date", required=True, disabled=True, width="100%"),
            rx.text("*Склад відправлення:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(
                        EditMovementsState.list_storages,
                        lambda storage: rx.select.item(storage[0], value=storage[1], width="100%"),
                    ),
                    width="100%",
                ),
                required=True,
                disabled=EditMovementsState.is_view_only_edit,
                value=EditMovementsState.id_incoming_storage,
                on_change=EditMovementsState.on_change_id_incoming_storage,
            ),
            rx.text("*Власник відправлення:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(
                        EditMovementsState.list_owners,
                        lambda owner: rx.select.item(owner[0], value=owner[1]),
                    ),
                    width="100%",
                ),
                required=True,
                disabled=EditMovementsState.is_view_only_edit,
                value=EditMovementsState.id_incoming_owner,
                on_change=EditMovementsState.on_change_id_incoming_owner,
            ),
            rx.text("*Склад призначення:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(
                        EditMovementsState.list_storages,
                        lambda storage: rx.select.item(storage[0], value=storage[1], width="100%"),
                    ),
                    width="100%",
                ),
                required=True,
                disabled=EditMovementsState.is_view_only_edit,
                value=EditMovementsState.id_destination_storage,
                on_change=EditMovementsState.on_change_id_destination_storage,
            ),
            rx.text("*Власник призначення:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(
                        EditMovementsState.list_owners,
                        lambda owner: rx.select.item(owner[0], value=owner[1]),
                    ),
                    width="100%",
                ),
                required=True,
                disabled=EditMovementsState.is_view_only_edit,
                value=EditMovementsState.id_destination_owner,
                on_change=EditMovementsState.on_change_id_destination_owner,
            ),
            rx.text("*Статус:", weight="medium"),
            rx.select(
                EditMovementsState.editable_statuses,
                placeholder="Оберіть зі списку",
                required=True,
                value=EditMovementsState.status,
                on_change=EditMovementsState.on_change_status,
            ),
            rx.text("Коментар:", weight="medium"),
            controls.text_area_field(value=EditMovementsState.item.comment, on_change=EditMovementsState.on_change_comment, width="100%"),
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
            "Переміщення/Редагування",
            controls.button_primary("Зберегти", on_click=EditMovementsState.open_save_dialog),
            left=controls.button_back(routes.MOVEMENT_MOVEMENTS, label="Скасувати"),
            width="100%",
        ),
        rx.skeleton(_edit_form(), loading=EditMovementsState.in_process, height="100%"),
    )


def _cancel_conflict_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            controls.dialog_heading("Скасування неможливе"),
            rx.dialog.description(
                "Товар із цього переміщення бере участь у наведених нижче рухах. "
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
                        ViewMovementsState.cancel_conflict_rows,
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
                    rx.button("Закрити", on_click=ViewMovementsState.set_cancel_conflict_dialog_open(False)),
                ),
                justify="end",
                margin_top="1em",
            ),
            max_width="42em",
        ),
        open=ViewMovementsState.is_cancel_conflict_dialog_open,
        on_open_change=ViewMovementsState.set_cancel_conflict_dialog_open,
    )


def view_page_content() -> rx.Component:
    return rx.vstack(
        _cancel_conflict_dialog(),
        titled_section(
            "Загальна інформація",
            field_row("Дата", ViewMovementsState.item.date),
            field_row("Склад відправлення", ViewMovementsState.item.incoming_storage.title),
            field_row("Власник відправлення", ViewMovementsState.item.incoming_owner.title),
            field_row("Склад призначення", ViewMovementsState.item.destination_storage.title),
            field_row("Власник призначення", ViewMovementsState.item.destination_owner.title),
            field_row("Статус", ViewMovementsState.item_status),
            field_row("Коментар", ViewMovementsState.item.comment),
        ),
        titled_section("Товари", products_widget(width="100%")),
        history_block(ViewMovementsState),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def view_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Переміщення/Перегляд",
            rx.cond(
                ViewMovementsState.get_user_actions.contains(Action.MOVEMENTS_DELETE)
                & (ViewMovementsState.current_is_canceled == False),
                controls.cancel_with_reason(
                    open=ViewMovementsState.is_cancel_reason_dialog_open,
                    on_open_change=ViewMovementsState.set_cancel_reason_dialog_open,
                    value=ViewMovementsState.cancel_reason,
                    on_change=ViewMovementsState.on_change_cancel_reason,
                    on_open_trigger=ViewMovementsState.open_cancel_reason_dialog,
                    on_confirm=ViewMovementsState.confirm_cancel,
                    title="Підтвердження скасування",
                    trigger_label="Скасувати",
                    description="Скасувати це переміщення? Товар буде повернено на попереднє місце.",
                ),
            ),
            rx.cond(
                ViewMovementsState.get_user_actions.contains(Action.MOVEMENTS_EDIT)
                & (ViewMovementsState.current_is_canceled == False),
                controls.button_primary("Редагувати", on_click=ViewMovementsState.on_click_edit),
            ),
            left=controls.button_back(routes.MOVEMENT_MOVEMENTS, label="Повернутись"),
            width="100%",
        ),
        rx.skeleton(view_page_content(), loading=ViewMovementsState.in_process, height="100%"),
    )
