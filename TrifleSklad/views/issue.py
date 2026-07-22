from typing import Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.declared import StorageType
from TrifleSklad.models import Issue
from TrifleSklad.movement.inline_creator_components import (
    create_lookup_button,
    owner_create_dialog,
    storage_create_dialog,
    worker_create_dialog,
)
from TrifleSklad.movement.list_components import filter_button, filter_card, filter_select, pagination
from TrifleSklad.movement.products.frontend import index as products_widget
from TrifleSklad.states.issue import (
    AddIssueState,
    EditIssueState,
    ListIssueState,
    ViewIssueState,
)
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.templates import controls
from TrifleSklad.views.templates.history import history_block
from TrifleSklad.views.templates.layouts import header_subpage, page_wrapper


def _table_row(item: Tuple[int, Issue]) -> rx.Component:
    return rx.table.row(
        rx.table.cell(rx.text(item[1].id)),
        rx.table.row_header_cell(item[1].movement.date, align="left"),
        rx.table.cell(rx.text(item[1].movement.destination_storage.title)),
        rx.table.cell(rx.text(item[1].recipient.fio)),
        rx.table.cell(rx.text(ListIssueState.get_movement_statuses[item[1].movement.status])),
        on_click=rx.redirect(f"{routes.MOVEMENT_ISSUES_VIEW_ID}{item[1].id}"),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def _table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("№", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Дата", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Місце призначення", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Одержувач", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Статус", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(rx.foreach(ListIssueState.get_items, _table_row)),
        variant="surface",
        width="100%",
    )


def list_page_content() -> rx.Component:
    return rx.vstack(
        rx.cond(ListIssueState.has_items, _table(), controls.empty_placeholder()),
        pagination(ListIssueState),
        spacing="3",
        width="100%",
    )


@require_login
def list_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Видачі",
            filter_button(ListIssueState),
            rx.cond(
                ListIssueState.get_user_actions.contains(Action.ISSUES_CREATE),
                controls.button_primary("Створити", on_click=ListIssueState.on_click_add),
            ),
            width="100%",
        ),
        rx.skeleton(list_page_content(), loading=ListIssueState.in_progress, height="100%"),
        filter_panel=filter_card(
            ListIssueState,
            filter_select(
                "Склад відправлення",
                ListIssueState.filter_incoming_storage,
                ListIssueState.list_warehouses,
                ListIssueState.on_change_filter_incoming_storage,
            ),
            filter_select(
                "Власник відправлення",
                ListIssueState.filter_incoming_owner,
                ListIssueState.list_owners,
                ListIssueState.on_change_filter_incoming_owner,
            ),
            filter_select(
                "Відповідальний",
                ListIssueState.filter_recipient,
                ListIssueState.list_recipients,
                ListIssueState.on_change_filter_recipient,
            ),
            filter_select(
                "Площадка/Відділ",
                ListIssueState.filter_site,
                ListIssueState.list_sites,
                ListIssueState.on_change_filter_site,
            ),
        ),
        on_mount=ListIssueState.on_load,
    )


def _request_picker() -> rx.Component:
    return rx.cond(
        AddIssueState.get_user_actions.contains(Action.REQUESTS_PROCESS)
        & AddIssueState.has_requests,
        rx.vstack(
            rx.text("Заявка (необов'язково):", weight="medium"),
            rx.select.root(
                rx.select.trigger(placeholder="Без заявки", width="100%"),
                rx.select.content(
                    rx.foreach(
                        AddIssueState.list_requests,
                        lambda r: rx.select.item(r[0], value=r[1]),
                    ),
                    width="100%",
                ),
                value=AddIssueState.selected_request_id,
                on_change=AddIssueState.on_change_request,
                width="100%",
            ),
            rx.cond(
                AddIssueState.has_request_positions,
                rx.vstack(
                    rx.text("Потрібно за заявкою:", weight="bold", size="2"),
                    rx.foreach(
                        AddIssueState.request_positions,
                        lambda p: rx.text(f"• {p[0]} — {p[1]}", size="2"),
                    ),
                    spacing="1",
                    align="stretch",
                    width="100%",
                ),
            ),
            rx.divider(),
            spacing="2",
            align="stretch",
            width="100%",
        ),
    )


def _add_form() -> rx.Component:
    return rx.vstack(
        _request_picker(),
        rx.text("*Дата:", weight="medium"),
        controls.input_field(
            type="date",
            required=True,
            default_value=AddIssueState.item.movement.date,
            width="100%",
            on_change=AddIssueState.on_change_date,
        ),
        rx.text("*Склад:", weight="medium"),
        rx.select.root(
            rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
            rx.select.content(
                rx.foreach(
                    AddIssueState.list_incoming_storages,
                    lambda storage: rx.select.item(storage[0], value=storage[1]),
                ),
                width="100%",
            ),
            required=True,
            value=AddIssueState.id_incoming_storage,
            on_change=AddIssueState.on_change_id_incoming_storage,
        ),
        create_lookup_button(
            Action.STORAGE_CREATE,
            "Створити склад",
            AddIssueState.open_storage_create(StorageType.WAREHOUSE, "incoming", False),
        ),
        rx.text("*Власник:", weight="medium"),
        rx.select.root(
            rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
            rx.select.content(
                rx.foreach(
                    AddIssueState.list_owners,
                    lambda owner: rx.select.item(owner[0], value=owner[1]),
                ),
                width="100%",
            ),
            required=True,
            value=AddIssueState.id_incoming_owner,
            on_change=AddIssueState.on_change_id_incoming_owner,
        ),
        create_lookup_button(Action.OWNERS_CREATE, "Створити власника", AddIssueState.open_owner_create("")),
        owner_create_dialog(AddIssueState),
        rx.text("*Місце призначення:", weight="medium"),
        rx.select.root(
            rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
            rx.select.content(
                rx.vstack(
                    controls.search_field(
                        placeholder="Введіть назву для пошуку",
                        width="100%",
                        value=AddIssueState.search_name_destination_storage,
                        on_change=AddIssueState.on_change_search_name_destination_storage,
                    ),
                    rx.foreach(
                        AddIssueState.list_destination_storages,
                        lambda storage: rx.select.item(storage[0], value=storage[1], width="100%"),
                    ),
                    width="100%",
                ),
                width="100%",
            ),
            required=True,
            value=AddIssueState.id_destination_storage,
            on_change=AddIssueState.on_change_id_destination_storage,
        ),
        create_lookup_button(
            Action.STORAGE_CREATE,
            "Створити площадку/відділ",
            AddIssueState.open_storage_create(StorageType.TECHNICAL_SITE, "destination", True),
        ),
        storage_create_dialog(AddIssueState),
        rx.text("*Одержувач:", weight="medium"),
        rx.select.root(
            rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
            rx.select.content(
                rx.foreach(
                    AddIssueState.list_workers,
                    lambda worker: rx.select.item(worker[0], value=worker[1]),
                ),
                width="100%",
            ),
            required=True,
            value=AddIssueState.id_recipient,
            on_change=AddIssueState.on_change_id_recipient,
        ),
        create_lookup_button(Action.WORKERS_CREATE, "Створити співробітника", AddIssueState.open_worker_create),
        worker_create_dialog(AddIssueState),
        products_widget(width="100%"),
        rx.text("*Статус:", weight="medium"),
        rx.select(
            AddIssueState.editable_statuses,
            placeholder="Оберіть зі списку",
            required=True,
            width="100%",
            value=AddIssueState.status,
            on_change=AddIssueState.on_change_status,
        ),
        rx.text("Коментар:", weight="medium"),
        controls.text_area_field(
            width="100%",
            value=AddIssueState.item.movement.comment,
            on_change=AddIssueState.on_change_comment,
        ),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def add_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Видачі/Додавання",
            controls.button_secondary("Зберегти і продовжити", on_click=AddIssueState.add_one(True)),
            controls.button_primary("Зберегти", on_click=AddIssueState.add_one(False)),
            left=controls.button_back(routes.MOVEMENT_ISSUES, label="Скасувати"),
            width="100%",
        ),
        _add_form(),
        on_mount=AddIssueState.on_load,
    )


def _edit_form() -> rx.Component:
    return rx.vstack(
        rx.text("*Дата:", weight="medium"),
        controls.input_field(
            type="date",
            required=True,
            disabled=True,
            default_value=EditIssueState.item.movement.date,
            width="100%",
            on_change=EditIssueState.on_change_date,
        ),
        rx.text("*Склад:", weight="medium"),
        rx.select.root(
            rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
            rx.select.content(
                rx.foreach(
                    EditIssueState.list_incoming_storages,
                    lambda storage: rx.select.item(storage[0], value=storage[1]),
                ),
                width="100%",
            ),
            disabled=True,
            required=True,
            value=EditIssueState.id_incoming_storage,
            on_change=EditIssueState.on_change_id_incoming_storage,
        ),
        rx.text("*Власник:", weight="medium"),
        rx.select.root(
            rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
            rx.select.content(
                rx.foreach(
                    EditIssueState.list_owners,
                    lambda owner: rx.select.item(owner[0], value=owner[1]),
                ),
                width="100%",
            ),
            required=True,
            disabled=True,
            value=EditIssueState.id_incoming_owner,
            on_change=EditIssueState.on_change_id_incoming_owner,
        ),
        rx.text("*Місце призначення:", weight="medium"),
        rx.select.root(
            rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
            rx.select.content(
                rx.vstack(
                    controls.search_field(
                        placeholder="Введіть назву для пошуку",
                        width="100%",
                        value=EditIssueState.search_name_destination_storage,
                        on_change=EditIssueState.on_change_search_name_destination_storage,
                    ),
                    rx.foreach(
                        EditIssueState.list_destination_storages,
                        lambda storage: rx.select.item(storage[0], value=storage[1], width="100%"),
                    ),
                    width="100%",
                ),
                width="100%",
            ),
            required=True,
            disabled=True,
            value=EditIssueState.id_destination_storage,
            on_change=EditIssueState.on_change_id_destination_storage,
        ),
        rx.text("*Одержувач:", weight="medium"),
        rx.select.root(
            rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
            rx.select.content(
                rx.foreach(
                    EditIssueState.list_workers,
                    lambda worker: rx.select.item(worker[0], value=worker[1]),
                ),
                width="100%",
            ),
            required=True,
            disabled=True,
            value=EditIssueState.id_recipient,
            on_change=EditIssueState.on_change_id_recipient,
        ),
        products_widget(width="100%"),
        rx.text("*Статус:", weight="medium"),
        rx.select(
            EditIssueState.editable_statuses,
            placeholder="Оберіть зі списку",
            required=True,
            width="100%",
            value=EditIssueState.status,
            on_change=EditIssueState.on_change_status,
        ),
        rx.text("Коментар:", weight="medium"),
        controls.text_area_field(
            width="100%",
            value=EditIssueState.item.movement.comment,
            on_change=EditIssueState.on_change_comment,
        ),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def edit_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Видачі/Редагування",
            controls.button_primary("Зберегти", on_click=EditIssueState.edit_one),
            left=controls.button_back(routes.MOVEMENT_ISSUES, label="Скасувати"),
            width="100%",
        ),
        rx.skeleton(_edit_form(), loading=EditIssueState.in_process, height="100%"),
    )


def _cancel_conflict_dialog() -> rx.Component:
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
                        ViewIssueState.cancel_conflict_rows,
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
                    rx.button("Закрити", on_click=ViewIssueState.set_cancel_conflict_dialog_open(False)),
                ),
                justify="end",
                margin_top="1em",
            ),
            max_width="42em",
        ),
        open=ViewIssueState.is_cancel_conflict_dialog_open,
        on_open_change=ViewIssueState.set_cancel_conflict_dialog_open,
    )


def view_page_content() -> rx.Component:
    return rx.vstack(
        _cancel_conflict_dialog(),
        rx.text(f"Дата: {ViewIssueState.item.movement.date}"),
        rx.text(f"Склад: {ViewIssueState.item.movement.incoming_storage.title}"),
        rx.text(f"Власник: {ViewIssueState.item.movement.incoming_owner.title}"),
        rx.text(f"Місце призначення: {ViewIssueState.item.movement.destination_storage.title}"),
        rx.text(f"Одержувач: {ViewIssueState.item.recipient.fio}"),
        rx.text(f"Статус: {ViewIssueState.item_status}"),
        rx.text(f"Коментар: {ViewIssueState.item.movement.comment}"),
        products_widget(width="100%"),
        history_block(ViewIssueState),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def view_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Видачі/Перегляд",
            rx.cond(
                ViewIssueState.get_user_actions.contains(Action.ISSUES_DELETE)
                & (ViewIssueState.current_is_canceled == False),
                controls.delete_with_confirm(
                    title="Підтвердження скасування",
                    trigger_label="Скасувати",
                    description="Скасувати цю видачу?",
                    on_confirm=ViewIssueState.on_click_cancel,
                ),
            ),
            rx.cond(
                ViewIssueState.get_user_actions.contains(Action.ISSUES_EDIT)
                & (ViewIssueState.current_is_canceled == False),
                controls.button_primary("Редагувати", on_click=ViewIssueState.on_click_edit),
            ),
            left=controls.button_back(routes.MOVEMENT_ISSUES, label="Повернутись"),
            width="100%",
        ),
        rx.skeleton(view_page_content(), loading=ViewIssueState.in_process, height="100%"),
    )
