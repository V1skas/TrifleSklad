import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.models import NDSRate
from TrifleSklad.states.nds_rate import (
    AddNdsRateState,
    EditNdsRateState,
    ListNdsRateState,
    ViewNdsRateState,
)
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.templates import controls
from TrifleSklad.views.templates.history import history_block
from TrifleSklad.views.templates.layouts import field_row, header_subpage, page_wrapper, titled_section


def _table_row(item: NDSRate) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(item.title, align="left"),
        on_click=rx.redirect(routes.CATALOG_NDS_RATES_VIEW_ID + item.id.to_string()),
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
            rx.foreach(ListNdsRateState.items, _table_row),
        ),
        variant="surface",
        width="100%",
    )


def list_page_content() -> rx.Component:
    return rx.cond(
        ListNdsRateState.has_items,
        _table(),
        controls.empty_placeholder(),
    )


@require_login
def list_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Ставки ПДВ",
            rx.cond(
                ListNdsRateState.get_user_actions.contains(Action.NDS_RATES_CREATE),
                controls.button_primary("Створити", on_click=ListNdsRateState.on_click_add),
            ),
            width="100%",
        ),
        rx.skeleton(list_page_content(), loading=ListNdsRateState.in_progress, height="100%"),
        on_mount=ListNdsRateState.on_load,
    )


def _form_fields(
    title, rate, description, is_default, set_title, set_rate, set_description, set_is_default
) -> rx.Component:
    return titled_section(
        "Інформація",
        rx.text("*Назва", weight="medium"),
        controls.input_field(value=title, on_change=set_title, placeholder="Назва", width="100%"),
        rx.text("Ставка, %", weight="medium"),
        controls.input_field(value=rate, on_change=set_rate, placeholder="0", width="100%"),
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
        AddNdsRateState.title,
        AddNdsRateState.rate,
        AddNdsRateState.description,
        AddNdsRateState.is_default,
        AddNdsRateState.set_title,
        AddNdsRateState.set_rate,
        AddNdsRateState.set_description,
        AddNdsRateState.set_is_default,
    )


@require_login
def add_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Ставки ПДВ/Додавання",
            controls.button_primary("Зберегти", on_click=AddNdsRateState.on_save),
            left=controls.button_back(routes.CATALOG_NDS_RATES, label="Скасувати"),
            width="100%",
        ),
        add_page_content(),
        on_mount=AddNdsRateState.on_load,
    )


def edit_page_content() -> rx.Component:
    return _form_fields(
        EditNdsRateState.title,
        EditNdsRateState.rate,
        EditNdsRateState.description,
        EditNdsRateState.is_default,
        EditNdsRateState.set_title,
        EditNdsRateState.set_rate,
        EditNdsRateState.set_description,
        EditNdsRateState.set_is_default,
    )


@require_login
def edit_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Ставки ПДВ/Редагування",
            controls.button_primary("Зберегти", on_click=EditNdsRateState.on_save),
            left=controls.button_back(routes.CATALOG_NDS_RATES, label="Скасувати"),
            width="100%",
        ),
        rx.skeleton(edit_page_content(), loading=EditNdsRateState.in_process, height="100%"),
    )


def view_page_content() -> rx.Component:
    return rx.vstack(
        titled_section(
            "Інформація",
            field_row("Назва", ViewNdsRateState.title),
            field_row("Ставка", f"{ViewNdsRateState.rate}%"),
            field_row("Опис", ViewNdsRateState.description),
            field_row("За замовчуванням для рухів", rx.cond(ViewNdsRateState.is_default, "Так", "Ні")),
        ),
        history_block(ViewNdsRateState),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def view_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Ставки ПДВ/Перегляд",
            rx.cond(
                ViewNdsRateState.get_user_actions.contains(Action.NDS_RATES_DELETE),
                controls.delete_with_confirm(on_confirm=ViewNdsRateState.on_click_delete),
            ),
            rx.cond(
                ViewNdsRateState.get_user_actions.contains(Action.NDS_RATES_EDIT),
                controls.button_primary("Редагувати", on_click=ViewNdsRateState.on_click_edit),
            ),
            left=controls.button_back(routes.CATALOG_NDS_RATES, label="Повернутись"),
            width="100%",
        ),
        rx.skeleton(view_page_content(), loading=ViewNdsRateState.in_process, height="100%"),
    )
