import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.declared import StorageType
from TrifleSklad.models import Movement
from TrifleSklad.movement.inline_creator_components import (
    create_lookup_button,
    storage_create_dialog,
)
from TrifleSklad.movement.list_components import filter_button, filter_card, filter_select, pagination
from TrifleSklad.movement.products.frontend import index as products_widget
from TrifleSklad.states.returns import (
    AddReturnsState,
    EditReturnsState,
    ListReturnsState,
    ViewReturnsState,
)
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.templates import controls, full_edit
from TrifleSklad.views.templates.history import history_block
from TrifleSklad.views.templates.layouts import header_subpage, page_wrapper


def _table_row(item: Movement) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item.id)),
        rx.table.row_header_cell(item.date, align="left"),
        rx.table.cell(rx.text(item.incoming_storage.title)),
        rx.table.cell(rx.text(item.destination_storage.title)),
        rx.table.cell(rx.text(ListReturnsState.get_movement_statuses[item.status])),
        on_click=rx.redirect(f"{routes.MOVEMENT_RETURNS_VIEW_ID}{item.id}"),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def _table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("№", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Дата", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Звідки", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Склад призначення", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Статус", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(rx.foreach(ListReturnsState.items, _table_row)),
        variant="surface",
        width="100%",
    )


def list_page_content() -> rx.Component:
    return rx.vstack(
        rx.cond(ListReturnsState.has_items, _table(), controls.empty_placeholder()),
        pagination(ListReturnsState),
        spacing="3",
        width="100%",
    )


@require_login
def list_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Повернення",
            filter_button(ListReturnsState),
            rx.cond(
                ListReturnsState.get_user_actions.contains(Action.RETURNS_CREATE),
                controls.button_primary("Створити", on_click=ListReturnsState.on_click_add),
            ),
            width="100%",
        ),
        rx.skeleton(list_page_content(), loading=ListReturnsState.in_progress, height="100%"),
        filter_panel=filter_card(
            ListReturnsState,
            filter_select(
                "Об'єкт відправлення",
                ListReturnsState.filter_incoming_storage,
                ListReturnsState.list_sites,
                ListReturnsState.on_change_filter_incoming_storage,
            ),
            filter_select(
                "Склад призначення",
                ListReturnsState.filter_destination_storage,
                ListReturnsState.list_warehouses,
                ListReturnsState.on_change_filter_destination_storage,
            ),
        ),
        on_mount=ListReturnsState.on_load,
    )


def _add_form() -> rx.Component:
    return rx.vstack(
        rx.text("*Дата:", weight="medium"),
        controls.input_field(
            value=AddReturnsState.current_date,
            on_change=AddReturnsState.on_change_date,
            type="date",
            required=True,
            width="100%",
        ),
        rx.text("*Звідки (площадка/відділ/клієнт):", weight="medium"),
        rx.select.root(
            rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
            rx.select.content(
                rx.foreach(
                    AddReturnsState.list_source_storages,
                    lambda storage: rx.select.item(storage[0], value=storage[1]),
                ),
                width="100%",
            ),
            required=True,
            value=AddReturnsState.id_incoming_storage,
            on_change=AddReturnsState.on_change_id_incoming_storage,
        ),
        create_lookup_button(
            Action.STORAGE_CREATE,
            "Створити площадку/відділ/клієнта",
            AddReturnsState.open_storage_create(StorageType.TECHNICAL_SITE, "incoming", True),
        ),
        rx.text("*Склад призначення:", weight="medium"),
        rx.select.root(
            rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
            rx.select.content(
                rx.foreach(
                    AddReturnsState.list_destination_storages,
                    lambda storage: rx.select.item(storage[0], value=storage[1]),
                ),
                width="100%",
            ),
            required=True,
            value=AddReturnsState.id_destination_storage,
            on_change=AddReturnsState.on_change_id_destination_storage,
        ),
        create_lookup_button(
            Action.STORAGE_CREATE,
            "Створити склад",
            AddReturnsState.open_storage_create(StorageType.WAREHOUSE, "destination", False),
        ),
        storage_create_dialog(AddReturnsState),
        products_widget(width="100%"),
        rx.text("*Статус:", weight="medium"),
        rx.select(
            AddReturnsState.editable_statuses,
            placeholder="Оберіть зі списку",
            required=True,
            value=AddReturnsState.status,
            on_change=AddReturnsState.on_change_status,
        ),
        rx.text("Коментар:", weight="medium"),
        controls.text_area_field(value=AddReturnsState.comment, on_change=AddReturnsState.on_change_comment, width="100%"),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def add_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Повернення/Додавання",
            controls.button_secondary("Зберегти і продовжити", on_click=AddReturnsState.add_one(True)),
            controls.button_primary("Зберегти", on_click=AddReturnsState.add_one(False)),
            left=controls.button_back(routes.MOVEMENT_RETURNS, label="Скасувати"),
            width="100%",
        ),
        _add_form(),
        on_mount=AddReturnsState.on_load,
    )


def _edit_form() -> rx.Component:
    return rx.vstack(
        full_edit.full_edit_notice(EditReturnsState),
        rx.text("*Дата:", weight="medium"),
        controls.input_field(value=EditReturnsState.item.date, type="date", required=True, disabled=True, width="100%"),
        rx.text("*Звідки (площадка/відділ/клієнт):", weight="medium"),
        rx.select.root(
            rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
            rx.select.content(
                rx.foreach(
                    EditReturnsState.list_source_storages,
                    lambda storage: rx.select.item(storage[0], value=storage[1], width="100%"),
                ),
                width="100%",
            ),
            required=True,
            disabled=EditReturnsState.is_view_only_edit,
            value=EditReturnsState.id_incoming_storage,
            on_change=EditReturnsState.on_change_id_incoming_storage,
        ),
        rx.text("*Склад призначення:", weight="medium"),
        rx.select.root(
            rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
            rx.select.content(
                rx.foreach(
                    EditReturnsState.list_destination_storages,
                    lambda storage: rx.select.item(storage[0], value=storage[1], width="100%"),
                ),
                width="100%",
            ),
            required=True,
            disabled=EditReturnsState.is_view_only_edit,
            value=EditReturnsState.id_destination_storage,
            on_change=EditReturnsState.on_change_id_destination_storage,
        ),
        products_widget(width="100%"),
        full_edit.reason_field(EditReturnsState),
        rx.text("*Статус:", weight="medium"),
        rx.select(
            EditReturnsState.editable_statuses,
            placeholder="Оберіть зі списку",
            required=True,
            value=EditReturnsState.status,
            on_change=EditReturnsState.on_change_status,
        ),
        rx.text("Коментар:", weight="medium"),
        controls.text_area_field(value=EditReturnsState.item.comment, on_change=EditReturnsState.on_change_comment, width="100%"),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def edit_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Повернення/Редагування",
            controls.button_primary("Зберегти", on_click=EditReturnsState.edit_one),
            left=controls.button_back(routes.MOVEMENT_RETURNS, label="Скасувати"),
            width="100%",
        ),
        rx.skeleton(_edit_form(), loading=EditReturnsState.in_process, height="100%"),
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
                        ViewReturnsState.cancel_conflict_rows,
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
                    rx.button("Закрити", on_click=ViewReturnsState.set_cancel_conflict_dialog_open(False)),
                ),
                justify="end",
                margin_top="1em",
            ),
            max_width="42em",
        ),
        open=ViewReturnsState.is_cancel_conflict_dialog_open,
        on_open_change=ViewReturnsState.set_cancel_conflict_dialog_open,
    )


def view_page_content() -> rx.Component:
    return rx.vstack(
        _cancel_conflict_dialog(),
        rx.hstack(rx.text("Дата:", weight="medium"), rx.text(ViewReturnsState.item.date)),
        rx.hstack(
            rx.text("Звідки (площадка/відділ/клієнт):", weight="medium"),
            rx.text(ViewReturnsState.item.incoming_storage.title),
        ),
        rx.hstack(rx.text("Склад призначення:", weight="medium"), rx.text(ViewReturnsState.item.destination_storage.title)),
        products_widget(width="100%"),
        rx.hstack(rx.text("Статус:", weight="medium"), rx.text(ViewReturnsState.item_status)),
        rx.hstack(rx.text("Коментар:", weight="medium"), rx.text(ViewReturnsState.item.comment)),
        history_block(ViewReturnsState),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def view_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Повернення/Перегляд",
            rx.cond(
                ViewReturnsState.get_user_actions.contains(Action.RETURNS_DELETE)
                & (ViewReturnsState.current_is_canceled == False),
                controls.delete_with_confirm(
                    title="Підтвердження скасування",
                    trigger_label="Скасувати",
                    description="Скасувати це повернення? Товар буде повернено на попереднє місце.",
                    on_confirm=ViewReturnsState.on_click_cancel,
                ),
            ),
            rx.cond(
                ViewReturnsState.get_user_actions.contains(Action.RETURNS_EDIT)
                & (ViewReturnsState.current_is_canceled == False),
                controls.button_primary("Редагувати", on_click=ViewReturnsState.on_click_edit),
            ),
            left=controls.button_back(routes.MOVEMENT_RETURNS, label="Повернутись"),
            width="100%",
        ),
        rx.skeleton(view_page_content(), loading=ViewReturnsState.in_process, height="100%"),
    )
