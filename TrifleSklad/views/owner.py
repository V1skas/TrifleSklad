import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.models import Owner
from TrifleSklad.states.owner import (
    AddOwnerState,
    EditOwnerState,
    ListOwnerState,
    ViewOwnerState,
)
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.templates import controls
from TrifleSklad.views.templates.history import history_block
from TrifleSklad.views.templates.layouts import field_row, header_subpage, page_wrapper, titled_section


def _table_row(item: Owner) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(item.title, align="left"),
        on_click=rx.redirect(routes.CATALOG_OWNERS_VIEW_ID + item.id.to_string()),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def _table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Назва", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(ListOwnerState.items, _table_row),
        ),
        variant="surface",
        width="100%",
    )


def list_page_content() -> rx.Component:
    return rx.cond(
        ListOwnerState.has_items,
        _table(),
        controls.empty_placeholder(),
    )


@require_login
def list_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Власники ТМЦ",
            rx.cond(
                ListOwnerState.get_user_actions.contains(Action.OWNERS_CREATE),
                controls.button_primary("Створити", on_click=ListOwnerState.on_click_add),
            ),
            width="100%",
        ),
        rx.skeleton(list_page_content(), loading=ListOwnerState.in_progress, height="100%"),
        on_mount=ListOwnerState.on_load,
    )


def _form_fields(title, description, is_default, set_title, set_description, set_is_default) -> rx.Component:
    return titled_section(
        "Інформація",
        rx.text("*Назва", weight="medium"),
        controls.input_field(value=title, on_change=set_title, placeholder="Назва", width="100%"),
        rx.text("Опис", weight="medium"),
        controls.text_area_field(value=description, on_change=set_description, placeholder="Опис", width="100%"),
        rx.hstack(
            rx.switch(checked=is_default, on_change=set_is_default),
            rx.text("За замовчуванням для рухів"),
            align="center",
            spacing="2",
        ),
    )


def add_page_content() -> rx.Component:
    return _form_fields(
        AddOwnerState.title,
        AddOwnerState.description,
        AddOwnerState.is_default,
        AddOwnerState.set_title,
        AddOwnerState.set_description,
        AddOwnerState.set_is_default,
    )


@require_login
def add_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Власники ТМЦ/Додавання",
            controls.button_primary("Зберегти", on_click=AddOwnerState.on_save),
            left=controls.button_back(routes.CATALOG_OWNERS, label="Скасувати"),
            width="100%",
        ),
        add_page_content(),
        on_mount=AddOwnerState.on_load,
    )


def edit_page_content() -> rx.Component:
    return _form_fields(
        EditOwnerState.title,
        EditOwnerState.description,
        EditOwnerState.is_default,
        EditOwnerState.set_title,
        EditOwnerState.set_description,
        EditOwnerState.set_is_default,
    )


@require_login
def edit_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Власники ТМЦ/Редагування",
            controls.button_primary("Зберегти", on_click=EditOwnerState.on_save),
            left=controls.button_back(routes.CATALOG_OWNERS, label="Скасувати"),
            width="100%",
        ),
        rx.skeleton(edit_page_content(), loading=EditOwnerState.in_process, height="100%"),
    )


def view_page_content() -> rx.Component:
    return rx.vstack(
        titled_section(
            "Інформація",
            field_row("Назва", ViewOwnerState.title),
            field_row("Опис", ViewOwnerState.description),
            field_row("За замовчуванням для рухів", rx.cond(ViewOwnerState.is_default, "Так", "Ні")),
        ),
        history_block(ViewOwnerState),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def view_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Власники ТМЦ/Перегляд",
            rx.cond(
                ViewOwnerState.get_user_actions.contains(Action.OWNERS_DELETE),
                controls.delete_with_confirm(on_confirm=ViewOwnerState.on_click_delete),
            ),
            rx.cond(
                ViewOwnerState.get_user_actions.contains(Action.OWNERS_EDIT),
                controls.button_primary("Редагувати", on_click=ViewOwnerState.on_click_edit),
            ),
            left=controls.button_back(routes.CATALOG_OWNERS, label="Повернутись"),
            width="100%",
        ),
        rx.skeleton(view_page_content(), loading=ViewOwnerState.in_process, height="100%"),
    )
