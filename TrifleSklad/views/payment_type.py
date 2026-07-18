import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.models import PaymentType
from TrifleSklad.states.payment_type import (
    AddPaymentTypeState,
    EditPaymentTypeState,
    ListPaymentTypeState,
    ViewPaymentTypeState,
)
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.templates import controls
from TrifleSklad.views.templates.layouts import header_subpage, page_wrapper


def _table_row(item: PaymentType) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(item.title, align="left"),
        on_click=rx.redirect(routes.CATALOG_PAYMENT_TYPES_VIEW_ID + item.id.to_string()),
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
            rx.foreach(ListPaymentTypeState.items, _table_row),
        ),
        variant="surface",
        width="100%",
    )


def list_page_content() -> rx.Component:
    return rx.cond(
        ListPaymentTypeState.has_items,
        _table(),
        controls.empty_placeholder(),
    )


@require_login
def list_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Типи оплат",
            rx.cond(
                ListPaymentTypeState.get_user_actions.contains(Action.PAYMENT_TYPE_CREATE),
                controls.button_primary("Створити", on_click=ListPaymentTypeState.on_click_add),
            ),
            width="100%",
        ),
        rx.skeleton(list_page_content(), loading=ListPaymentTypeState.in_progress, height="100%"),
        on_mount=ListPaymentTypeState.on_load,
    )


def _form_fields(title, description, is_default, set_title, set_description, set_is_default) -> rx.Component:
    return rx.vstack(
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
        spacing="3",
        align="stretch",
        width="100%",
    )


def add_page_content() -> rx.Component:
    return _form_fields(
        AddPaymentTypeState.title,
        AddPaymentTypeState.description,
        AddPaymentTypeState.is_default,
        AddPaymentTypeState.set_title,
        AddPaymentTypeState.set_description,
        AddPaymentTypeState.set_is_default,
    )


@require_login
def add_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Типи оплат/Додавання",
            controls.button_primary("Зберегти", on_click=AddPaymentTypeState.on_save),
            left=controls.button_back(routes.CATALOG_PAYMENT_TYPES, label="Скасувати"),
            width="100%",
        ),
        add_page_content(),
        on_mount=AddPaymentTypeState.on_load,
    )


def edit_page_content() -> rx.Component:
    return _form_fields(
        EditPaymentTypeState.title,
        EditPaymentTypeState.description,
        EditPaymentTypeState.is_default,
        EditPaymentTypeState.set_title,
        EditPaymentTypeState.set_description,
        EditPaymentTypeState.set_is_default,
    )


@require_login
def edit_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Типи оплат/Редагування",
            controls.button_primary("Зберегти", on_click=EditPaymentTypeState.on_save),
            left=controls.button_back(routes.CATALOG_PAYMENT_TYPES, label="Скасувати"),
            width="100%",
        ),
        rx.skeleton(edit_page_content(), loading=EditPaymentTypeState.in_process, height="100%"),
    )


def view_page_content() -> rx.Component:
    return rx.vstack(
        rx.hstack(rx.text("Назва:", weight="medium"), rx.text(ViewPaymentTypeState.title), width="100%"),
        rx.hstack(rx.text("Опис:", weight="medium"), rx.text(ViewPaymentTypeState.description), width="100%"),
        rx.hstack(
            rx.text("За замовчуванням для рухів:", weight="medium"),
            rx.text(rx.cond(ViewPaymentTypeState.is_default, "Так", "Ні")),
            width="100%",
        ),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def view_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Типи оплат/Перегляд",
            rx.cond(
                ViewPaymentTypeState.get_user_actions.contains(Action.PAYMENT_TYPE_DELETE),
                controls.delete_with_confirm(on_confirm=ViewPaymentTypeState.on_click_delete),
            ),
            rx.cond(
                ViewPaymentTypeState.get_user_actions.contains(Action.PAYMENT_TYPE_EDIT),
                controls.button_primary("Редагувати", on_click=ViewPaymentTypeState.on_click_edit),
            ),
            left=controls.button_back(routes.CATALOG_PAYMENT_TYPES, label="Повернутись"),
            width="100%",
        ),
        rx.skeleton(view_page_content(), loading=ViewPaymentTypeState.in_process, height="100%"),
    )
