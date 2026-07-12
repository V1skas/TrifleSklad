from typing import Tuple

import reflex as rx

from components.elements import subpage_header

from TrifleSklad import routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.models import ClientIssue
from TrifleSklad.state import AppState
from TrifleSklad.movement.client_issues.backend import (
    AddClientIssueState,
    ClientIssueState,
    EditClientIssueState,
    ListClientIssueState,
    ViewClientIssueState,
)
from TrifleSklad.movement.products.frontend import index as products
from TrifleSklad.movement.list_components import filter_button, filter_card, filter_select, pagination
from TrifleSklad.movement.inline_creator_components import (
    create_lookup_button,
    owner_create_dialog,
    worker_create_dialog,
    storage_create_dialog,
)
from TrifleSklad.declared import StorageType


def client_issues_table_row(item: Tuple[int, ClientIssue]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item[1].id)),
        rx.table.row_header_cell(
            item[1].movement.date,
            align="left",
        ),
        rx.table.cell(rx.text(item[1].movement.destination_storage.title)),
        rx.table.cell(rx.text(item[1].contract_number)),
        rx.table.cell(rx.text(item[1].recipient.fio)),
        rx.table.cell(
            rx.text(ListClientIssueState.get_movement_statuses[item[1].movement.status])
        ),
        on_click=rx.redirect(f"{routes.MOVEMENT_CLIENT_ISSUES_VIEW_ID}{item[1].id}"),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def client_issues_table() -> rx.Component:
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
        rx.table.body(
            rx.foreach(ListClientIssueState.get_items, client_issues_table_row),
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
                "Видачі клієнту",
                actions=[
                    filter_button(ListClientIssueState),
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.CLIENT_ISSUES_CREATE),
                        rx.button(
                            "Додати",
                            variant="ghost",
                            size="3",
                            on_click=rx.redirect(routes.MOVEMENT_CLIENT_ISSUES_ADD),
                        ),
                    ),
                ],
            ),
            filter_card(
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
            rx.cond(ListClientIssueState.has_items, client_issues_table(), rx.text("Записів немає.")),
            pagination(ListClientIssueState),
            width="100%",
            height="100%",
        ),
        value=ClientIssueState.Pages.LIST,
    )


def add_form() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text("*Дата:"),
            rx.input(
                name="date",
                type="date",
                required=True,
                size="3",
                default_value=AddClientIssueState.item.movement.date,
                width="100%",
                on_change=AddClientIssueState.on_change_date,
            ),
            rx.text("*Склад:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%",
                ),
                rx.select.content(
                    rx.foreach(
                        AddClientIssueState.list_incoming_storages,
                        lambda storage: rx.select.item(storage[0], value=storage[1]),
                    ),
                    width="100%",
                ),
                name="id_incoming_storage",
                required=True,
                value=AddClientIssueState.id_incoming_storage,
                on_change=AddClientIssueState.on_change_id_incoming_storage,
            ),
            create_lookup_button(ActionEnum.STORAGE_CREATE, "Створити склад", AddClientIssueState.open_storage_create(StorageType.WAREHOUSE, "incoming", False)),
            rx.text("*Власник:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%",
                ),
                rx.select.content(
                    rx.foreach(
                        AddClientIssueState.list_owners,
                        lambda owner: rx.select.item(owner[0], value=owner[1]),
                    ),
                    width="100%",
                ),
                name="id_incoming_owner",
                required=True,
                value=AddClientIssueState.id_incoming_owner,
                on_change=AddClientIssueState.on_change_id_incoming_owner,
            ),
            create_lookup_button(ActionEnum.OWNERS_CREATE, "Створити власника", AddClientIssueState.open_owner_create),
            owner_create_dialog(AddClientIssueState),
            rx.text("*Клієнт:"),
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
                                on_click=AddClientIssueState.on_click_search_name_destination_storage,
                            ),
                            rx.input(
                                placeholder="Введіть назву для пошуку",
                                width="100%",
                                value=AddClientIssueState.search_name_destination_storage,
                                on_change=AddClientIssueState.on_change_search_name_destination_storage,
                            ),
                            width="100%",
                        ),
                        rx.foreach(
                            AddClientIssueState.list_destination_storages,
                            lambda storage: rx.select.item(
                                storage[0], value=storage[1], width="100%"
                            ),
                        ),
                        width="100%",
                    ),
                    width="100%",
                ),
                name="id_destination_storage",
                required=True,
                value=AddClientIssueState.id_destination_storage,
                on_change=AddClientIssueState.on_change_id_destination_storage,
            ),
            create_lookup_button(ActionEnum.STORAGE_CREATE, "Створити клієнта", AddClientIssueState.open_storage_create(StorageType.CLIENT, "destination", False)),
            storage_create_dialog(AddClientIssueState),
            rx.text("*Номер договору:"),
            rx.input(
                name="contract_number",
                required=True,
                size="3",
                width="100%",
                value=AddClientIssueState.item.contract_number,
                on_change=AddClientIssueState.on_change_contract_number,
            ),
            rx.text("*Адреса встановлення:"),
            rx.input(
                name="installation_address",
                required=True,
                size="3",
                width="100%",
                value=AddClientIssueState.item.installation_address,
                on_change=AddClientIssueState.on_change_installation_address,
            ),
            rx.text("*Відповідальний:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%",
                ),
                rx.select.content(
                    rx.foreach(
                        AddClientIssueState.list_workers,
                        lambda worker: rx.select.item(worker[0], value=worker[1]),
                    ),
                    width="100%",
                ),
                name="id_recipient",
                required=True,
                value=AddClientIssueState.id_recipient,
                on_change=AddClientIssueState.on_change_id_recipient,
            ),
            create_lookup_button(ActionEnum.WORKERS_CREATE, "Створити співробітника", AddClientIssueState.open_worker_create),
            worker_create_dialog(AddClientIssueState),
            products(width="100%"),
            rx.hstack(
                rx.text("*Статус:"),
                rx.select(
                    AddClientIssueState.editable_statuses,
                    name="status",
                    placeholder="Оберіть зі списку",
                    required=True,
                    width="100%",
                    value=AddClientIssueState.status,
                    on_change=AddClientIssueState.on_change_status,
                ),
            ),
            rx.text("Коментар:"),
            rx.text_area(
                name="comment",
                width="100%",
                value=AddClientIssueState.item.movement.comment,
                on_change=AddClientIssueState.on_change_comment,
            ),
            spacing="3",
            align="stretch",
            width="100%",
        ),
        width="100%",
        height="100%",
    )


def add_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            subpage_header(
                "Видачі клієнту/Додавання",
                left=rx.button(
                    "Скасувати",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(routes.MOVEMENT_CLIENT_ISSUES),
                ),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.CLIENT_ISSUES_CREATE),
                        rx.button(
                            "Зберегти і продовжити",
                            variant="ghost",
                            size="3",
                            on_click=AddClientIssueState.add_one(True),
                        ),
                    ),
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.CLIENT_ISSUES_CREATE),
                        rx.button(
                            "Зберегти",
                            variant="ghost",
                            size="3",
                            on_click=AddClientIssueState.add_one(False),
                        ),
                    ),
                ],
            ),
            add_form(),
            width="100%",
        ),
        value=ClientIssueState.Pages.ADD,
    )


def edit_form() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text("*Дата:"),
            rx.input(
                name="date",
                type="date",
                required=True,
                size="3",
                disabled=True,
                default_value=EditClientIssueState.item.movement.date,
                width="100%",
                on_change=EditClientIssueState.on_change_date,
            ),
            rx.text("*Склад:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%",
                ),
                rx.select.content(
                    rx.foreach(
                        EditClientIssueState.list_incoming_storages,
                        lambda storage: rx.select.item(storage[0], value=storage[1]),
                    ),
                    width="100%",
                ),
                disabled=True,
                name="id_incoming_storage",
                required=True,
                value=EditClientIssueState.id_incoming_storage,
                on_change=EditClientIssueState.on_change_id_incoming_storage,
            ),
            rx.text("*Власник:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%",
                ),
                rx.select.content(
                    rx.foreach(
                        EditClientIssueState.list_owners,
                        lambda owner: rx.select.item(owner[0], value=owner[1]),
                    ),
                    width="100%",
                ),
                name="id_incoming_owner",
                required=True,
                disabled=True,
                value=EditClientIssueState.id_incoming_owner,
                on_change=EditClientIssueState.on_change_id_incoming_owner,
            ),
            rx.text("*Клієнт:"),
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
                                on_click=EditClientIssueState.on_click_search_name_destination_storage,
                            ),
                            rx.input(
                                placeholder="Введіть назву для пошуку",
                                width="100%",
                                value=EditClientIssueState.search_name_destination_storage,
                                on_change=EditClientIssueState.on_change_search_name_destination_storage,
                            ),
                            width="100%",
                        ),
                        rx.foreach(
                            EditClientIssueState.list_destination_storages,
                            lambda storage: rx.select.item(
                                storage[0], value=storage[1], width="100%"
                            ),
                        ),
                        width="100%",
                    ),
                    width="100%",
                ),
                name="id_destination_storage",
                required=True,
                disabled=True,
                value=EditClientIssueState.id_destination_storage,
                on_change=EditClientIssueState.on_change_id_destination_storage,
            ),
            rx.text("*Номер договору:"),
            rx.input(
                name="contract_number",
                required=True,
                size="3",
                width="100%",
                value=EditClientIssueState.item.contract_number,
                on_change=EditClientIssueState.on_change_contract_number,
            ),
            rx.text("*Адреса встановлення:"),
            rx.input(
                name="installation_address",
                required=True,
                size="3",
                width="100%",
                value=EditClientIssueState.item.installation_address,
                on_change=EditClientIssueState.on_change_installation_address,
            ),
            rx.text("*Відповідальний:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%",
                ),
                rx.select.content(
                    rx.foreach(
                        EditClientIssueState.list_workers,
                        lambda worker: rx.select.item(worker[0], value=worker[1]),
                    ),
                    width="100%",
                ),
                name="id_recipient",
                required=True,
                disabled=True,
                value=EditClientIssueState.id_recipient,
                on_change=EditClientIssueState.on_change_id_recipient,
            ),
            products(width="100%"),
            rx.hstack(
                rx.text("*Статус:"),
                rx.select(
                    EditClientIssueState.editable_statuses,
                    name="status",
                    placeholder="Оберіть зі списку",
                    required=True,
                    width="100%",
                    value=EditClientIssueState.status,
                    on_change=EditClientIssueState.on_change_status,
                ),
            ),
            rx.text("Коментар:"),
            rx.text_area(
                name="comment",
                width="100%",
                value=EditClientIssueState.item.movement.comment,
                on_change=EditClientIssueState.on_change_comment,
            ),
            spacing="3",
            align="stretch",
            width="100%",
        ),
        width="100%",
        height="100%",
    )


def edit_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            subpage_header(
                "Видачі клієнту/Редагування",
                left=rx.button(
                    "Скасувати",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(routes.MOVEMENT_CLIENT_ISSUES),
                ),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.CLIENT_ISSUES_EDIT),
                        rx.button(
                            "Зберегти",
                            variant="ghost",
                            size="3",
                            on_click=EditClientIssueState.edit_one,
                        ),
                    ),
                ],
            ),
            edit_form(),
            width="100%",
        ),
        value=ClientIssueState.Pages.EDIT,
    )


def cancel_conflict_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Скасування неможливе"),
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
                    rx.button(
                        "Закрити",
                        on_click=ViewClientIssueState.set_cancel_conflict_dialog_open(False),
                    ),
                ),
                justify="end",
                margin_top="1em",
            ),
            max_width="42em",
        ),
        open=ViewClientIssueState.is_cancel_conflict_dialog_open,
        on_open_change=ViewClientIssueState.set_cancel_conflict_dialog_open,
    )


def view_body() -> rx.Component:
    return rx.vstack(
        rx.text(f"Дата: {ViewClientIssueState.item.movement.date}"),
        rx.text(f"Склад: {ViewClientIssueState.item.movement.incoming_storage.title}"),
        rx.text(f"Власник: {ViewClientIssueState.item.movement.incoming_owner.title}"),
        rx.text(f"Клієнт: {ViewClientIssueState.item.movement.destination_storage.title}"),
        rx.text(f"Номер договору: {ViewClientIssueState.item.contract_number}"),
        rx.text(f"Адреса встановлення: {ViewClientIssueState.item.installation_address}"),
        rx.text(f"Відповідальний: {ViewClientIssueState.item.recipient.fio}"),
        rx.text(
            f"Статус: {ListClientIssueState.get_movement_statuses[ViewClientIssueState.item.movement.status]}"
        ),
        rx.text(f"Коментар: {ViewClientIssueState.item.movement.comment}"),
        products(width="100%"),
        spacing="3",
        align="stretch",
        width="100%",
        height="100%",
    )


def view_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            cancel_conflict_dialog(),
            subpage_header(
                "Видачі клієнту/Перегляд",
                left=rx.button(
                    "Повернутись",
                    variant="ghost",
                    size="3",
                    on_click=rx.redirect(routes.MOVEMENT_CLIENT_ISSUES),
                ),
                actions=[
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.CLIENT_ISSUES_EDIT)
                        & (ViewClientIssueState.current_is_canceled == False),
                        rx.button(
                            "Редагувати",
                            variant="ghost",
                            size="3",
                            on_click=rx.redirect(
                                f"{routes.MOVEMENT_CLIENT_ISSUES_EDIT_ID}{ViewClientIssueState.item.id}"
                            ),
                        ),
                    ),
                    rx.cond(
                        AppState.get_user_actions.contains(ActionEnum.CLIENT_ISSUES_DELETE)
                        & (ViewClientIssueState.current_is_canceled == False),
                        rx.button(
                            "Скасувати",
                            color_scheme="red",
                            variant="ghost",
                            size="3",
                            on_click=ClientIssueState.delete_one,
                        ),
                    ),
                ],
            ),
            view_body(),
            width="100%",
        ),
        value=ClientIssueState.Pages.VIEW,
    )


def index() -> rx.Component:
    return rx.tabs.root(
        rx.cond(AppState.get_user_actions.contains(ActionEnum.CLIENT_ISSUES_LIST),
            list_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.CLIENT_ISSUES_CREATE),
            add_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.CLIENT_ISSUES_VIEW),
            view_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.CLIENT_ISSUES_EDIT),
            edit_tab_content()),
        value=ClientIssueState.current_page,
        height="100%",
        width="100%",
    )
