import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.models import ProductCategory
from TrifleSklad.states.category import (
    NONE,
    AddCategoriesState,
    EditCategoriesState,
    ListCategoriesState,
    ViewCategoriesState,
)
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.templates import controls
from TrifleSklad.views.templates.history import history_block
from TrifleSklad.views.templates.layouts import header_subpage, page_wrapper


def _table_row(item: ProductCategory) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(
            rx.cond(item.id_parent, rx.text(f"— {item.title}"), rx.text(item.title, weight="bold")),
            align="left",
        ),
        on_click=rx.redirect(routes.CATALOG_CATEGORIES_VIEW_ID + item.id.to_string()),
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
            rx.foreach(ListCategoriesState.items, _table_row),
        ),
        variant="surface",
        width="100%",
    )


def list_page_content() -> rx.Component:
    return rx.cond(
        ListCategoriesState.has_items,
        _table(),
        controls.empty_placeholder(),
    )


@require_login
def list_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Категорії ТМЦ",
            rx.cond(
                ListCategoriesState.get_user_actions.contains(Action.CATEGORIES_CREATE),
                controls.button_primary("Створити", on_click=ListCategoriesState.on_click_add),
            ),
            width="100%",
        ),
        rx.skeleton(list_page_content(), loading=ListCategoriesState.in_progress, height="100%"),
        on_mount=ListCategoriesState.on_load,
    )


def _parent_select(value, on_change, options) -> rx.Component:
    return rx.select.root(
        rx.select.trigger(placeholder="Без батьківської категорії"),
        rx.select.content(
            rx.select.item("Без батьківської категорії", value=NONE),
            rx.foreach(options, lambda opt: rx.select.item(opt[1], value=opt[0])),
        ),
        value=value,
        on_change=on_change,
    )


def add_page_content() -> rx.Component:
    return rx.vstack(
        rx.text("*Назва", weight="medium"),
        controls.input_field(value=AddCategoriesState.title, on_change=AddCategoriesState.set_title, placeholder="Назва", width="100%"),
        rx.text("Батьківська категорія", weight="medium"),
        _parent_select(AddCategoriesState.parent_id, AddCategoriesState.set_parent_id, AddCategoriesState.list_parent_categories),
        rx.text("Опис", weight="medium"),
        controls.text_area_field(value=AddCategoriesState.description, on_change=AddCategoriesState.set_description, placeholder="Опис", width="100%"),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def add_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Категорії ТМЦ/Додавання",
            controls.button_primary("Зберегти", on_click=AddCategoriesState.on_save),
            left=controls.button_back(routes.CATALOG_CATEGORIES, label="Скасувати"),
            width="100%",
        ),
        add_page_content(),
        on_mount=AddCategoriesState.on_load,
    )


def edit_page_content() -> rx.Component:
    return rx.vstack(
        rx.text("*Назва", weight="medium"),
        controls.input_field(value=EditCategoriesState.title, on_change=EditCategoriesState.set_title, placeholder="Назва", width="100%"),
        rx.cond(
            EditCategoriesState.can_set_parent,
            rx.fragment(
                rx.text("Батьківська категорія", weight="medium"),
                _parent_select(EditCategoriesState.parent_id, EditCategoriesState.set_parent_id, EditCategoriesState.list_parent_categories),
            ),
        ),
        rx.text("Опис", weight="medium"),
        controls.text_area_field(value=EditCategoriesState.description, on_change=EditCategoriesState.set_description, placeholder="Опис", width="100%"),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def edit_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Категорії ТМЦ/Редагування",
            controls.button_primary("Зберегти", on_click=EditCategoriesState.on_save),
            left=controls.button_back(routes.CATALOG_CATEGORIES, label="Скасувати"),
            width="100%",
        ),
        rx.skeleton(edit_page_content(), loading=EditCategoriesState.in_process, height="100%"),
    )


def _child_row(item: ProductCategory) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(item.title, align="left"),
        on_click=rx.redirect(routes.CATALOG_CATEGORIES_VIEW_ID + item.id.to_string()),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def view_page_content() -> rx.Component:
    return rx.vstack(
        rx.hstack(rx.text("Назва:", weight="medium"), rx.text(ViewCategoriesState.title), width="100%"),
        rx.cond(
            ViewCategoriesState.parent_title != "",
            rx.hstack(rx.text("Батьківська категорія:", weight="medium"), rx.text(ViewCategoriesState.parent_title), width="100%"),
        ),
        rx.hstack(rx.text("Опис:", weight="medium"), rx.text(ViewCategoriesState.description), width="100%"),
        rx.cond(
            ViewCategoriesState.children.length() > 0,
            rx.vstack(
                rx.text("Підкатегорії:", weight="medium"),
                rx.table.root(
                    rx.table.body(rx.foreach(ViewCategoriesState.children, _child_row)),
                    variant="surface",
                    width="100%",
                ),
                width="100%",
                align="stretch",
            ),
        ),
        history_block(ViewCategoriesState),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def view_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Категорії ТМЦ/Перегляд",
            rx.cond(
                ViewCategoriesState.get_user_actions.contains(Action.CATEGORIES_DELETE),
                controls.delete_with_confirm(on_confirm=ViewCategoriesState.on_click_delete),
            ),
            rx.cond(
                ViewCategoriesState.get_user_actions.contains(Action.CATEGORIES_EDIT),
                controls.button_primary("Редагувати", on_click=ViewCategoriesState.on_click_edit),
            ),
            left=controls.button_back(routes.CATALOG_CATEGORIES, label="Повернутись"),
            width="100%",
        ),
        rx.skeleton(view_page_content(), loading=ViewCategoriesState.in_process, height="100%"),
    )
