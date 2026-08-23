import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.models import Storage
from TrifleSklad.states.client import (
    AddClientState,
    EditClientState,
    ListClientState,
    ViewClientState,
)
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.templates import controls
from TrifleSklad.views.templates.history import history_block
from TrifleSklad.views.templates.layouts import field_row, header_subpage, page_wrapper, titled_section


def _table_row(item: Storage) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(item.title, align="left"),
        rx.table.cell(item.address),
        on_click=rx.redirect(routes.CATALOG_CLIENTS_VIEW_ID + item.id.to_string()),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def _table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Назва", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Адреса", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(ListClientState.filtered_items, _table_row),
        ),
        variant="surface",
        width="100%",
    )


def _filter_shell() -> rx.Component:
    return controls.filter_shell(
        ListClientState.is_filter_open,
        controls.filter_grid(
            controls.filter_group(
                "Назва",
                controls.search_field(
                    rx.input.slot(rx.icon("search")),
                    value=ListClientState.filter_title,
                    on_change=ListClientState.set_filter_title,
                    placeholder="Пошук за назвою",
                    width="100%",
                ),
            ),
            controls.filter_group(
                "Адреса",
                controls.search_field(
                    rx.input.slot(rx.icon("search")),
                    value=ListClientState.filter_address,
                    on_change=ListClientState.set_filter_address,
                    placeholder="Пошук за адресою",
                    width="100%",
                ),
            ),
        ),
    )


def list_page_content() -> rx.Component:
    return rx.cond(
        ListClientState.has_items,
        _table(),
        controls.empty_placeholder(),
    )


@require_login
def list_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Клієнти",
            controls.filter_toggle_button(
                ListClientState.is_filter_open,
                ListClientState.toggle_filter,
                active=ListClientState.has_active_filters,
            ),
            rx.cond(
                ListClientState.get_user_actions.contains(Action.CLIENT_CREATE),
                controls.button_primary("Створити", on_click=ListClientState.on_click_add),
            ),
            width="100%",
        ),
        rx.skeleton(list_page_content(), loading=ListClientState.in_progress, height="100%"),
        filter_panel=_filter_shell(),
        on_mount=ListClientState.on_load,
    )


def _worker_select(value, on_change, workers) -> rx.Component:
    return rx.select.root(
        rx.select.trigger(placeholder="Оберіть відповідального"),
        rx.select.content(
            rx.foreach(workers, lambda w: rx.select.item(w[1], value=w[0])),
        ),
        value=value,
        on_change=on_change,
    )


def add_page_content() -> rx.Component:
    return titled_section(
        "Інформація",
        rx.text("*Назва", weight="medium"),
        controls.input_field(value=AddClientState.title, on_change=AddClientState.set_title, placeholder="Назва", width="100%"),
        rx.text("Адреса", weight="medium"),
        controls.input_field(value=AddClientState.address, on_change=AddClientState.set_address, placeholder="Адреса", width="100%"),
        rx.text("Відповідальний", weight="medium"),
        _worker_select(AddClientState.id_responsible, AddClientState.set_id_responsible, AddClientState.list_workers),
        rx.text("Опис", weight="medium"),
        controls.text_area_field(value=AddClientState.description, on_change=AddClientState.set_description, placeholder="Опис", width="100%"),
        rx.hstack(
            rx.switch(checked=AddClientState.is_default, on_change=AddClientState.set_is_default),
            rx.text("За замовчуванням для рухів"),
            align="center",
            spacing="2",
        ),
    )


@require_login
def add_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Клієнти/Додавання",
            controls.button_primary("Зберегти", on_click=AddClientState.on_save),
            left=controls.button_back(routes.CATALOG_CLIENTS, label="Скасувати"),
            width="100%",
        ),
        add_page_content(),
        on_mount=AddClientState.on_load,
    )


def edit_page_content() -> rx.Component:
    return titled_section(
        "Інформація",
        rx.text("*Назва", weight="medium"),
        controls.input_field(value=EditClientState.title, on_change=EditClientState.set_title, placeholder="Назва", width="100%"),
        rx.text("Адреса", weight="medium"),
        controls.input_field(value=EditClientState.address, on_change=EditClientState.set_address, placeholder="Адреса", width="100%"),
        rx.text("Відповідальний", weight="medium"),
        _worker_select(EditClientState.id_responsible, EditClientState.set_id_responsible, EditClientState.list_workers),
        rx.text("Опис", weight="medium"),
        controls.text_area_field(value=EditClientState.description, on_change=EditClientState.set_description, placeholder="Опис", width="100%"),
        rx.hstack(
            rx.switch(checked=EditClientState.is_default, on_change=EditClientState.set_is_default),
            rx.text("За замовчуванням для рухів"),
            align="center",
            spacing="2",
        ),
    )


@require_login
def edit_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Клієнти/Редагування",
            controls.button_primary("Зберегти", on_click=EditClientState.on_save),
            left=controls.button_back(routes.CATALOG_CLIENTS, label="Скасувати"),
            width="100%",
        ),
        rx.skeleton(edit_page_content(), loading=EditClientState.in_process, height="100%"),
    )


def view_page_content() -> rx.Component:
    return rx.vstack(
        titled_section(
            "Інформація",
            field_row("Назва", ViewClientState.title),
            field_row("Адреса", ViewClientState.address),
            field_row("Відповідальний", ViewClientState.responsible),
            field_row("Опис", ViewClientState.description),
            field_row("За замовчуванням для рухів", rx.cond(ViewClientState.is_default, "Так", "Ні")),
        ),
        history_block(ViewClientState),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def view_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Клієнти/Перегляд",
            rx.cond(
                ViewClientState.get_user_actions.contains(Action.CLIENT_DELETE),
                controls.delete_with_confirm(on_confirm=ViewClientState.on_click_delete),
            ),
            rx.cond(
                ViewClientState.get_user_actions.contains(Action.CLIENT_EDIT),
                controls.button_primary("Редагувати", on_click=ViewClientState.on_click_edit),
            ),
            left=controls.button_back(routes.CATALOG_CLIENTS, label="Повернутись"),
            width="100%",
        ),
        rx.skeleton(view_page_content(), loading=ViewClientState.in_process, height="100%"),
    )
