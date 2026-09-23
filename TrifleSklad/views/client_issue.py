from typing import Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.declared import StorageType
from TrifleSklad.models import ClientIssue
from TrifleSklad.movement.inline_creator_components import (
    create_lookup_button,
    owner_create_dialog,
    storage_create_dialog,
    worker_create_dialog,
)
from TrifleSklad.movement.list_components import filter_button, filter_card, filter_select, pagination
from TrifleSklad.movement.products.frontend import index as products_widget
from TrifleSklad.states.client_issue import (
    AddClientIssueState,
    EditClientIssueState,
    ListClientIssueState,
    ViewClientIssueState,
)
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.templates import controls, full_edit
from TrifleSklad.views.templates.history import history_block
from TrifleSklad.views.templates.layouts import field_row, header_subpage, page_wrapper, titled_section


def _table_row(item: Tuple[int, ClientIssue]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item[1].id)),
        rx.table.row_header_cell(item[1].movement.date, align="left"),
        rx.table.cell(rx.text(item[1].movement.destination_storage.title)),
        rx.table.cell(rx.text(item[1].contract_number)),
        rx.table.cell(rx.text(item[1].recipient.fio)),
        rx.table.cell(rx.text(ListClientIssueState.get_movement_statuses[item[1].movement.status])),
        on_click=rx.redirect(f"{routes.MOVEMENT_CLIENT_ISSUES_VIEW_ID}{item[1].id}"),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def _table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("№", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Дата", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Клієнт", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Номер договору", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Відповідальний", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Статус", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(rx.foreach(ListClientIssueState.get_items, _table_row)),
        variant="surface",
        width="100%",
    )


def list_page_content() -> rx.Component:
    return rx.vstack(
        rx.cond(ListClientIssueState.has_items, _table(), controls.empty_placeholder()),
        pagination(ListClientIssueState),
        spacing="3",
        width="100%",
    )


@require_login
def list_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Видачі клієнту",
            filter_button(ListClientIssueState),
            rx.cond(
                ListClientIssueState.get_user_actions.contains(Action.CLIENT_ISSUES_CREATE),
                controls.button_primary("Створити", on_click=ListClientIssueState.on_click_add),
            ),
            width="100%",
        ),
        rx.skeleton(list_page_content(), loading=ListClientIssueState.in_progress, height="100%"),
        filter_panel=filter_card(
            ListClientIssueState,
            filter_select(
                "Склад відправлення",
                ListClientIssueState.filter_incoming_storage,
                ListClientIssueState.list_warehouses,
                ListClientIssueState.on_change_filter_incoming_storage,
            ),
            filter_select(
                "Власник відправлення",
                ListClientIssueState.filter_incoming_owner,
                ListClientIssueState.list_owners,
                ListClientIssueState.on_change_filter_incoming_owner,
            ),
            filter_select(
                "Відповідальний",
                ListClientIssueState.filter_recipient,
                ListClientIssueState.list_recipients,
                ListClientIssueState.on_change_filter_recipient,
            ),
            filter_select(
                "Клієнт",
                ListClientIssueState.filter_client,
                ListClientIssueState.list_clients,
                ListClientIssueState.on_change_filter_client,
            ),
        ),
        on_mount=ListClientIssueState.on_load,
    )


def _add_form() -> rx.Component:
    return rx.vstack(
        titled_section(
            "Загальна інформація",
            rx.text("*Дата:", weight="medium"),
            controls.input_field(
                type="date",
                required=True,
                default_value=AddClientIssueState.item.movement.date,
                width="100%",
                on_change=AddClientIssueState.on_change_date,
            ),
            rx.text("*Склад:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(
                        AddClientIssueState.list_incoming_storages,
                        lambda storage: rx.select.item(storage[0], value=storage[1]),
                    ),
                    width="100%",
                ),
                required=True,
                value=AddClientIssueState.id_incoming_storage,
                on_change=AddClientIssueState.on_change_id_incoming_storage,
            ),
            create_lookup_button(
                Action.STORAGE_CREATE,
                "Створити склад",
                AddClientIssueState.open_storage_create(StorageType.WAREHOUSE, "incoming", False),
            ),
            rx.text("*Власник:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(
                        AddClientIssueState.list_owners,
                        lambda owner: rx.select.item(owner[0], value=owner[1]),
                    ),
                    width="100%",
                ),
                required=True,
                value=AddClientIssueState.id_incoming_owner,
                on_change=AddClientIssueState.on_change_id_incoming_owner,
            ),
            create_lookup_button(Action.OWNERS_CREATE, "Створити власника", AddClientIssueState.open_owner_create("")),
            owner_create_dialog(AddClientIssueState),
            rx.text("*Клієнт:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.vstack(
                        controls.search_field(
                            placeholder="Введіть назву для пошуку",
                            width="100%",
                            value=AddClientIssueState.search_name_destination_storage,
                            on_change=AddClientIssueState.on_change_search_name_destination_storage,
                        ),
                        rx.foreach(
                            AddClientIssueState.list_destination_storages,
                            lambda storage: rx.select.item(storage[0], value=storage[1], width="100%"),
                        ),
                        width="100%",
                    ),
                    width="100%",
                ),
                required=True,
                value=AddClientIssueState.id_destination_storage,
                on_change=AddClientIssueState.on_change_id_destination_storage,
            ),
            create_lookup_button(
                Action.STORAGE_CREATE,
                "Створити клієнта",
                AddClientIssueState.open_storage_create(StorageType.CLIENT, "destination", False),
            ),
            storage_create_dialog(AddClientIssueState),
            rx.text("Номер договору:", weight="medium"),
            controls.input_field(
                width="100%",
                value=AddClientIssueState.item.contract_number,
                on_change=AddClientIssueState.on_change_contract_number,
            ),
            rx.text("*Адреса встановлення:", weight="medium"),
            controls.input_field(
                required=True,
                width="100%",
                value=AddClientIssueState.item.installation_address,
                on_change=AddClientIssueState.on_change_installation_address,
            ),
            rx.text("*Відповідальний:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(
                        AddClientIssueState.list_workers,
                        lambda worker: rx.select.item(worker[0], value=worker[1]),
                    ),
                    width="100%",
                ),
                required=True,
                value=AddClientIssueState.id_recipient,
                on_change=AddClientIssueState.on_change_id_recipient,
            ),
            create_lookup_button(Action.WORKERS_CREATE, "Створити співробітника", AddClientIssueState.open_worker_create),
            worker_create_dialog(AddClientIssueState),
            rx.text("*Статус:", weight="medium"),
            rx.select(
                AddClientIssueState.editable_statuses,
                placeholder="Оберіть зі списку",
                required=True,
                width="100%",
                value=AddClientIssueState.status,
                on_change=AddClientIssueState.on_change_status,
            ),
            rx.text("Коментар:", weight="medium"),
            controls.text_area_field(
                width="100%",
                value=AddClientIssueState.item.movement.comment,
                on_change=AddClientIssueState.on_change_comment,
            ),
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
            "Видачі клієнту/Додавання",
            controls.button_secondary("Зберегти і продовжити", on_click=AddClientIssueState.add_one(True)),
            controls.button_primary("Зберегти", on_click=AddClientIssueState.add_one(False)),
            left=controls.button_back(routes.MOVEMENT_CLIENT_ISSUES, label="Скасувати"),
            width="100%",
        ),
        _add_form(),
        on_mount=AddClientIssueState.on_load,
    )


def _edit_form() -> rx.Component:
    return rx.vstack(
        full_edit.full_edit_notice(EditClientIssueState),
        full_edit.save_reason_dialog(EditClientIssueState),
        titled_section(
            "Загальна інформація",
            rx.text("*Дата:", weight="medium"),
            controls.input_field(
                type="date",
                required=True,
                disabled=EditClientIssueState.is_view_only_edit,
                default_value=EditClientIssueState.item.movement.date,
                width="100%",
                on_change=EditClientIssueState.on_change_date,
            ),
            rx.text("*Склад:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(
                        EditClientIssueState.list_incoming_storages,
                        lambda storage: rx.select.item(storage[0], value=storage[1]),
                    ),
                    width="100%",
                ),
                disabled=EditClientIssueState.is_view_only_edit,
                required=True,
                value=EditClientIssueState.id_incoming_storage,
                on_change=EditClientIssueState.on_change_id_incoming_storage,
            ),
            rx.text("*Власник:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(
                        EditClientIssueState.list_owners,
                        lambda owner: rx.select.item(owner[0], value=owner[1]),
                    ),
                    width="100%",
                ),
                required=True,
                disabled=EditClientIssueState.is_view_only_edit,
                value=EditClientIssueState.id_incoming_owner,
                on_change=EditClientIssueState.on_change_id_incoming_owner,
            ),
            rx.text("*Клієнт:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.vstack(
                        controls.search_field(
                            placeholder="Введіть назву для пошуку",
                            width="100%",
                            value=EditClientIssueState.search_name_destination_storage,
                            on_change=EditClientIssueState.on_change_search_name_destination_storage,
                        ),
                        rx.foreach(
                            EditClientIssueState.list_destination_storages,
                            lambda storage: rx.select.item(storage[0], value=storage[1], width="100%"),
                        ),
                        width="100%",
                    ),
                    width="100%",
                ),
                required=True,
                disabled=EditClientIssueState.is_view_only_edit,
                value=EditClientIssueState.id_destination_storage,
                on_change=EditClientIssueState.on_change_id_destination_storage,
            ),
            rx.text("Номер договору:", weight="medium"),
            controls.input_field(
                width="100%",
                value=EditClientIssueState.item.contract_number,
                on_change=EditClientIssueState.on_change_contract_number,
            ),
            rx.text("*Адреса встановлення:", weight="medium"),
            controls.input_field(
                required=True,
                width="100%",
                value=EditClientIssueState.item.installation_address,
                on_change=EditClientIssueState.on_change_installation_address,
            ),
            rx.text("*Відповідальний:", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                rx.select.content(
                    rx.foreach(
                        EditClientIssueState.list_workers,
                        lambda worker: rx.select.item(worker[0], value=worker[1]),
                    ),
                    width="100%",
                ),
                required=True,
                disabled=EditClientIssueState.is_view_only_edit,
                value=EditClientIssueState.id_recipient,
                on_change=EditClientIssueState.on_change_id_recipient,
            ),
            rx.text("*Статус:", weight="medium"),
            rx.select(
                EditClientIssueState.editable_statuses,
                placeholder="Оберіть зі списку",
                required=True,
                width="100%",
                value=EditClientIssueState.status,
                on_change=EditClientIssueState.on_change_status,
            ),
            rx.text("Коментар:", weight="medium"),
            controls.text_area_field(
                width="100%",
                value=EditClientIssueState.item.movement.comment,
                on_change=EditClientIssueState.on_change_comment,
            ),
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
            "Видачі клієнту/Редагування",
            controls.button_primary("Зберегти", on_click=EditClientIssueState.open_save_dialog),
            left=controls.button_back(routes.MOVEMENT_CLIENT_ISSUES, label="Скасувати"),
            width="100%",
        ),
        rx.skeleton(_edit_form(), loading=EditClientIssueState.in_process, height="100%"),
    )


def _cancel_conflict_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            controls.dialog_heading("Скасування неможливе"),
            rx.dialog.description(
                "Товар із цієї видачі бере участь у наведених нижче рухах. "
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
                        ViewClientIssueState.cancel_conflict_rows,
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
                    rx.button("Закрити", on_click=ViewClientIssueState.set_cancel_conflict_dialog_open(False)),
                ),
                justify="end",
                margin_top="1em",
            ),
            max_width="42em",
        ),
        open=ViewClientIssueState.is_cancel_conflict_dialog_open,
        on_open_change=ViewClientIssueState.set_cancel_conflict_dialog_open,
    )


def view_page_content() -> rx.Component:
    return rx.vstack(
        _cancel_conflict_dialog(),
        titled_section(
            "Загальна інформація",
            field_row("Дата", ViewClientIssueState.item.movement.date),
            field_row("Склад", ViewClientIssueState.item.movement.incoming_storage.title),
            field_row("Власник", ViewClientIssueState.item.movement.incoming_owner.title),
            field_row("Клієнт", ViewClientIssueState.item.movement.destination_storage.title),
            field_row("Номер договору", ViewClientIssueState.item.contract_number),
            field_row("Адреса встановлення", ViewClientIssueState.item.installation_address),
            field_row("Відповідальний", ViewClientIssueState.item.recipient.fio),
            field_row("Статус", ViewClientIssueState.item_status),
            field_row("Коментар", ViewClientIssueState.item.movement.comment),
        ),
        titled_section("Товари", products_widget(width="100%")),
        history_block(ViewClientIssueState),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def view_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Видачі клієнту/Перегляд",
            rx.cond(
                ViewClientIssueState.get_user_actions.contains(Action.CLIENT_ISSUES_DELETE)
                & (ViewClientIssueState.current_is_canceled == False),
                controls.cancel_with_reason(
                    open=ViewClientIssueState.is_cancel_reason_dialog_open,
                    on_open_change=ViewClientIssueState.set_cancel_reason_dialog_open,
                    value=ViewClientIssueState.cancel_reason,
                    on_change=ViewClientIssueState.on_change_cancel_reason,
                    on_open_trigger=ViewClientIssueState.open_cancel_reason_dialog,
                    on_confirm=ViewClientIssueState.confirm_cancel,
                    title="Підтвердження скасування",
                    trigger_label="Скасувати",
                    description="Скасувати цю видачу?",
                ),
            ),
            rx.cond(
                ViewClientIssueState.get_user_actions.contains(Action.CLIENT_ISSUES_EDIT)
                & (ViewClientIssueState.current_is_canceled == False),
                controls.button_primary("Редагувати", on_click=ViewClientIssueState.on_click_edit),
            ),
            left=controls.button_back(routes.MOVEMENT_CLIENT_ISSUES, label="Повернутись"),
            width="100%",
        ),
        rx.skeleton(view_page_content(), loading=ViewClientIssueState.in_process, height="100%"),
    )
