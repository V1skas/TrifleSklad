import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.models import Supplier
from TrifleSklad.states.supplier import (
    AddSupplierState,
    EditSupplierState,
    ListSupplierState,
    ViewSupplierState,
)
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.templates import controls
from TrifleSklad.views.templates.layouts import header_subpage, page_wrapper


def _table_row(item: Supplier) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(item.title, align="left"),
        rx.table.cell(item.edrpou),
        on_click=rx.redirect(routes.CATALOG_SUPPLIERS_VIEW_ID + item.id.to_string()),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def _table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Назва", color=rx.color("accent", 2)),
                rx.table.column_header_cell("ЄДРПОУ", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(ListSupplierState.filtered_items, _table_row),
        ),
        variant="surface",
        width="100%",
    )


def list_page_content() -> rx.Component:
    return rx.vstack(
        controls.search_field(
            rx.input.slot(rx.icon("search")),
            value=ListSupplierState.filter_title,
            on_change=ListSupplierState.set_filter_title,
            placeholder="Пошук за назвою...",
            width="100%",
        ),
        rx.cond(
            ListSupplierState.has_items,
            _table(),
            controls.empty_placeholder(),
        ),
        spacing="3",
        width="100%",
    )


@require_login
def list_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Постачальники",
            rx.cond(
                ListSupplierState.get_user_actions.contains(Action.SUPPLIERS_CREATE),
                controls.button_primary("Створити", on_click=ListSupplierState.on_click_add),
            ),
            width="100%",
        ),
        rx.skeleton(list_page_content(), loading=ListSupplierState.in_progress, height="100%"),
        on_mount=ListSupplierState.on_load,
    )


def _form_fields(state) -> rx.Component:
    return rx.vstack(
        rx.text("*Назва", weight="medium"),
        controls.input_field(value=state.title, on_change=state.set_title, placeholder="Назва", width="100%"),
        rx.text("ЄДРПОУ", weight="medium"),
        controls.input_field(value=state.edrpou, on_change=state.set_edrpou, placeholder="ЄДРПОУ", width="100%"),
        rx.text("Адреса", weight="medium"),
        controls.input_field(value=state.address, on_change=state.set_address, placeholder="Адреса", width="100%"),
        rx.text("Email", weight="medium"),
        controls.input_field(value=state.email, on_change=state.set_email, placeholder="Email", width="100%"),
        rx.text("Контактна особа", weight="medium"),
        controls.input_field(value=state.contact_person, on_change=state.set_contact_person, placeholder="ПІБ", width="100%"),
        rx.text("Контактний телефон", weight="medium"),
        controls.input_field(value=state.contact_phone, on_change=state.set_contact_phone, placeholder="Телефон", width="100%"),
        rx.text("Опис", weight="medium"),
        controls.text_area_field(value=state.description, on_change=state.set_description, placeholder="Опис", width="100%"),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def add_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Постачальники/Додавання",
            controls.button_primary("Зберегти", on_click=AddSupplierState.on_save),
            left=controls.button_back(routes.CATALOG_SUPPLIERS, label="Скасувати"),
            width="100%",
        ),
        _form_fields(AddSupplierState),
        on_mount=AddSupplierState.on_load,
    )


@require_login
def edit_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Постачальники/Редагування",
            controls.button_primary("Зберегти", on_click=EditSupplierState.on_save),
            left=controls.button_back(routes.CATALOG_SUPPLIERS, label="Скасувати"),
            width="100%",
        ),
        rx.skeleton(_form_fields(EditSupplierState), loading=EditSupplierState.in_process, height="100%"),
    )


def view_page_content() -> rx.Component:
    return rx.vstack(
        rx.hstack(rx.text("Назва:", weight="medium"), rx.text(ViewSupplierState.title), width="100%"),
        rx.hstack(rx.text("ЄДРПОУ:", weight="medium"), rx.text(ViewSupplierState.edrpou), width="100%"),
        rx.hstack(rx.text("Адреса:", weight="medium"), rx.text(ViewSupplierState.address), width="100%"),
        rx.hstack(rx.text("Email:", weight="medium"), rx.text(ViewSupplierState.email), width="100%"),
        rx.hstack(rx.text("Контактна особа:", weight="medium"), rx.text(ViewSupplierState.contact_person), width="100%"),
        rx.hstack(rx.text("Контактний телефон:", weight="medium"), rx.text(ViewSupplierState.contact_phone), width="100%"),
        rx.hstack(rx.text("Опис:", weight="medium"), rx.text(ViewSupplierState.description), width="100%"),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def view_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Постачальники/Перегляд",
            rx.cond(
                ViewSupplierState.get_user_actions.contains(Action.SUPPLIERS_DELETE),
                controls.delete_with_confirm(on_confirm=ViewSupplierState.on_click_delete),
            ),
            rx.cond(
                ViewSupplierState.get_user_actions.contains(Action.SUPPLIERS_EDIT),
                controls.button_primary("Редагувати", on_click=ViewSupplierState.on_click_edit),
            ),
            left=controls.button_back(routes.CATALOG_SUPPLIERS, label="Повернутись"),
            width="100%",
        ),
        rx.skeleton(view_page_content(), loading=ViewSupplierState.in_process, height="100%"),
    )
