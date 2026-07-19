import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.declared import storage_type_list
from TrifleSklad.models import Storage
from TrifleSklad.states.storage import (
    AddStorageState,
    EditStorageState,
    ListStorageState,
    ViewStorageState,
)
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.templates import controls
from TrifleSklad.views.templates.layouts import header_subpage, page_wrapper


def _table_row(item: Storage) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(item.title, align="left"),
        rx.table.cell(item.address),
        on_click=rx.redirect(routes.CATALOG_STORAGES_VIEW_ID + item.id.to_string()),
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
            rx.foreach(ListStorageState.filtered_items, _table_row),
        ),
        variant="surface",
        width="100%",
    )


def list_page_content() -> rx.Component:
    return rx.vstack(
        rx.hstack(
            controls.search_field(
                rx.input.slot(rx.icon("search")),
                value=ListStorageState.filter_title,
                on_change=ListStorageState.set_filter_title,
                placeholder="Пошук за назвою...",
                flex="1",
                min_width="0",
            ),
            controls.search_field(
                value=ListStorageState.filter_address,
                on_change=ListStorageState.set_filter_address,
                placeholder="Пошук за адресою...",
                flex="1",
                min_width="0",
            ),
            rx.select.root(
                # width/flex_shrink — на trigger, не на root: rx.select.root
                # не рендерить власний стилізовний DOM-елемент, тож пропси
                # розміру на ньому мовчки ігноруються (той самий баг, що вже
                # чинили на селекті ставки ПДВ у admission.py).
                rx.select.trigger(placeholder="Тип", width="14em", flex_shrink="0"),
                rx.select.content(
                    rx.select.item("Всі", value="all"),
                    rx.foreach(
                        ListStorageState.storage_type_options,
                        lambda opt: rx.select.item(opt[0], value=opt[1]),
                    ),
                    width="100%",
                ),
                value=ListStorageState.filter_type,
                on_change=ListStorageState.set_filter_type,
            ),
            spacing="3",
            width="100%",
            align="center",
        ),
        rx.cond(
            ListStorageState.has_items,
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
            "Об'єкти підприємства",
            rx.cond(
                ListStorageState.get_user_actions.contains(Action.STORAGE_CREATE),
                controls.button_primary("Створити", on_click=ListStorageState.on_click_add),
            ),
            width="100%",
        ),
        rx.skeleton(list_page_content(), loading=ListStorageState.in_progress, height="100%"),
        on_mount=ListStorageState.on_load,
    )


def _type_select(value, on_change) -> rx.Component:
    return rx.select.root(
        rx.select.trigger(placeholder="Оберіть тип"),
        rx.select.content(
            *[rx.select.item(title, value=str(t)) for t, title in storage_type_list.items()],
        ),
        value=value,
        on_change=on_change,
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
    return rx.vstack(
        rx.text("*Тип", weight="medium"),
        _type_select(AddStorageState.storage_type_id, AddStorageState.set_storage_type_id),
        rx.text("*Назва", weight="medium"),
        controls.input_field(value=AddStorageState.title, on_change=AddStorageState.set_title, placeholder="Назва", width="100%"),
        rx.text("Адреса", weight="medium"),
        controls.input_field(value=AddStorageState.address, on_change=AddStorageState.set_address, placeholder="Адреса", width="100%"),
        rx.text("Відповідальний", weight="medium"),
        _worker_select(AddStorageState.id_responsible, AddStorageState.set_id_responsible, AddStorageState.list_workers),
        rx.text("Опис", weight="medium"),
        controls.text_area_field(value=AddStorageState.description, on_change=AddStorageState.set_description, placeholder="Опис", width="100%"),
        rx.hstack(
            rx.switch(checked=AddStorageState.is_default, on_change=AddStorageState.set_is_default),
            rx.text("За замовчуванням для рухів"),
            align="center",
            spacing="2",
        ),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def add_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Об'єкти підприємства/Додавання",
            controls.button_primary("Зберегти", on_click=AddStorageState.on_save),
            left=controls.button_back(routes.CATALOG_STORAGES, label="Скасувати"),
            width="100%",
        ),
        add_page_content(),
        on_mount=AddStorageState.on_load,
    )


def edit_page_content() -> rx.Component:
    return rx.vstack(
        rx.text("*Тип", weight="medium"),
        _type_select(EditStorageState.storage_type_id, EditStorageState.set_storage_type_id),
        rx.text("*Назва", weight="medium"),
        controls.input_field(value=EditStorageState.title, on_change=EditStorageState.set_title, placeholder="Назва", width="100%"),
        rx.text("Адреса", weight="medium"),
        controls.input_field(value=EditStorageState.address, on_change=EditStorageState.set_address, placeholder="Адреса", width="100%"),
        rx.text("Відповідальний", weight="medium"),
        _worker_select(EditStorageState.id_responsible, EditStorageState.set_id_responsible, EditStorageState.list_workers),
        rx.text("Опис", weight="medium"),
        controls.text_area_field(value=EditStorageState.description, on_change=EditStorageState.set_description, placeholder="Опис", width="100%"),
        rx.hstack(
            rx.switch(checked=EditStorageState.is_default, on_change=EditStorageState.set_is_default),
            rx.text("За замовчуванням для рухів"),
            align="center",
            spacing="2",
        ),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def edit_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Об'єкти підприємства/Редагування",
            controls.button_primary("Зберегти", on_click=EditStorageState.on_save),
            left=controls.button_back(routes.CATALOG_STORAGES, label="Скасувати"),
            width="100%",
        ),
        rx.skeleton(edit_page_content(), loading=EditStorageState.in_process, height="100%"),
    )


def view_page_content() -> rx.Component:
    return rx.vstack(
        rx.hstack(rx.text("Тип:", weight="medium"), rx.text(ViewStorageState.storage_type), width="100%"),
        rx.hstack(rx.text("Назва:", weight="medium"), rx.text(ViewStorageState.title), width="100%"),
        rx.hstack(rx.text("Адреса:", weight="medium"), rx.text(ViewStorageState.address), width="100%"),
        rx.hstack(rx.text("Відповідальний:", weight="medium"), rx.text(ViewStorageState.responsible), width="100%"),
        rx.hstack(rx.text("Опис:", weight="medium"), rx.text(ViewStorageState.description), width="100%"),
        rx.hstack(
            rx.text("За замовчуванням для рухів:", weight="medium"),
            rx.text(rx.cond(ViewStorageState.is_default, "Так", "Ні")),
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
            "Об'єкти підприємства/Перегляд",
            rx.cond(
                ViewStorageState.get_user_actions.contains(Action.STORAGE_DELETE),
                controls.delete_with_confirm(on_confirm=ViewStorageState.on_click_delete),
            ),
            rx.cond(
                ViewStorageState.get_user_actions.contains(Action.STORAGE_EDIT),
                controls.button_primary("Редагувати", on_click=ViewStorageState.on_click_edit),
            ),
            left=controls.button_back(routes.CATALOG_STORAGES, label="Повернутись"),
            width="100%",
        ),
        rx.skeleton(view_page_content(), loading=ViewStorageState.in_process, height="100%"),
    )
