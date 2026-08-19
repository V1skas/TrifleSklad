import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.models import ProductCatalog
from TrifleSklad.movement.list_components import pagination
from TrifleSklad.states.product import (
    ALL,
    AddProductsState,
    EditProductsState,
    ListProductsState,
    ViewProductsState,
)
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.templates import controls
from TrifleSklad.views.templates.history import history_block
from TrifleSklad.views.templates.layouts import field_row, header_subpage, page_wrapper, titled_section


def _bool_badge(value) -> rx.Component:
    return rx.cond(
        value,
        rx.badge("Так", color_scheme="grass", variant="soft"),
        rx.badge("Ні", color_scheme="gray", variant="soft"),
    )


def _table_row(item: ProductCatalog) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(item.title, align="left"),
        rx.table.cell(item.category.title),
        rx.table.cell(item.unit),
        rx.table.cell(_bool_badge(item.divisible)),
        rx.table.cell(
            rx.cond(
                item.no_fixed_capacity,
                rx.text("∞"),
                rx.cond(item.divisible, rx.text(item.capacity), rx.text("-")),
            )
        ),
        rx.table.cell(_bool_badge(item.uniq)),
        on_click=rx.redirect(routes.CATALOG_PRODUCTS_VIEW_ID + item.id.to_string()),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def _table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Назва", align="left", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Категорія", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Одиниця виміру", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Подільний", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Місткість", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Серійний номер", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(ListProductsState.items, _table_row),
        ),
        variant="surface",
        width="100%",
    )


def _filter_shell() -> rx.Component:
    return controls.filter_shell(
        ListProductsState.is_filter_open,
        controls.filter_grid(
            controls.filter_group(
                "Пошук",
                controls.search_field(
                    rx.input.slot(rx.icon("search")),
                    placeholder="Назва товару",
                    value=ListProductsState.get_search_str,
                    on_change=ListProductsState.set_search_str,
                    width="100%",
                ),
            ),
            controls.filter_group(
                "Категорія",
                rx.select.root(
                    # width — на trigger, не на root (rx.select.root не рендерить
                    # власний стилізовний DOM-елемент).
                    rx.select.trigger(placeholder="Усі категорії", width="100%"),
                    rx.select.content(
                        rx.select.item("Усі категорії", value=ALL),
                        rx.foreach(
                            ListProductsState.list_categories,
                            lambda c: rx.select.item(c[0], value=c[1]),
                        ),
                        width="100%",
                    ),
                    value=ListProductsState.filter_category_id,
                    on_change=ListProductsState.set_filter_category_id,
                    width="100%",
                ),
            ),
        ),
    )


def list_page_content() -> rx.Component:
    return rx.vstack(
        rx.cond(
            ListProductsState.has_items,
            _table(),
            controls.empty_placeholder(),
        ),
        pagination(ListProductsState),
        spacing="3",
        width="100%",
    )


@require_login
def list_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Каталог ТМЦ",
            controls.filter_toggle_button(
                ListProductsState.is_filter_open,
                ListProductsState.toggle_filter,
                active=ListProductsState.has_active_filters,
            ),
            rx.cond(
                ListProductsState.get_user_actions.contains(Action.PRODUCTS_CREATE),
                controls.button_primary("Створити", on_click=ListProductsState.on_click_add),
            ),
            width="100%",
        ),
        rx.skeleton(list_page_content(), loading=ListProductsState.in_progress, height="100%"),
        filter_panel=_filter_shell(),
        on_mount=ListProductsState.on_load,
    )


def _create_category_dialog(state) -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Створення категорії"),
            rx.vstack(
                rx.text("*Назва:", size="2"),
                controls.input_field(value=state.new_category_title, on_change=state.set_new_category_title, width="100%"),
                rx.text("Опис:", size="2"),
                controls.text_area_field(value=state.new_category_description, on_change=state.set_new_category_description, width="100%"),
                rx.hstack(
                    rx.button("Скасувати", variant="outline", type="button", on_click=state.set_create_category_open(False)),
                    rx.spacer(),
                    rx.button("Створити", type="button", on_click=state.create_category),
                    width="100%",
                    padding_top="0.5em",
                ),
                spacing="2",
                width="100%",
            ),
            width="28em",
        ),
        open=state.is_create_category_open,
        on_open_change=state.set_create_category_open,
    )


def _category_select_row(state) -> rx.Component:
    return rx.vstack(
        rx.select.root(
            rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
            rx.select.content(
                rx.foreach(state.list_categories, lambda c: rx.select.item(c[1], value=c[0])),
                width="100%",
            ),
            value=state.category_id,
            on_change=state.set_category_id,
            size="3",
            width="100%",
        ),
        rx.hstack(
            rx.spacer(),
            rx.cond(
                state.get_user_actions.contains(Action.CATEGORIES_CREATE),
                rx.button(
                    rx.icon("plus", size=14),
                    "Створити категорію",
                    variant="ghost",
                    size="2",
                    type="button",
                    on_click=state.open_create_category,
                ),
            ),
            width="100%",
        ),
        _create_category_dialog(state),
        spacing="1",
        width="100%",
    )


def _units_datalist(state) -> rx.Component:
    return rx.el.datalist(
        rx.foreach(state.all_units_cache, lambda unit: rx.el.option(value=unit)),
        id="units-datalist",
    )


def _form_fields(state, uniq_disabled: bool) -> rx.Component:
    return rx.vstack(
        titled_section(
            "Основна інформація",
            rx.text("*Назва", weight="medium"),
            controls.input_field(value=state.title, on_change=state.set_title, width="100%"),
            rx.text("Опис", weight="medium"),
            controls.text_area_field(value=state.description, on_change=state.set_description, width="100%"),
            rx.text("*Категорія", weight="medium"),
            _category_select_row(state),
            rx.text("Одиниця виміру", weight="medium"),
            controls.input_field(list="units-datalist", value=state.unit, on_change=state.set_unit, width="100%"),
            _units_datalist(state),
        ),
        titled_section(
            "Параметри обліку",
            rx.text("Місткість", weight="medium"),
            controls.input_field(
                value=state.capacity,
                on_change=state.set_capacity,
                width="100%",
                disabled=state.uniq | state.no_fixed_capacity,
            ),
            rx.checkbox(
                "Має серійний номер",
                checked=state.uniq,
                on_change=state.set_uniq,
                size="3",
                disabled=uniq_disabled,
            ),
            rx.checkbox(
                "Подільний",
                checked=state.divisible,
                on_change=state.set_divisible,
                size="3",
                disabled=uniq_disabled or state.uniq,
            ),
            # Тумблер доступний лише для подільного неунікального ТМЦ; на редагуванні
            # не блокується — кількість завжди рахується за залишком (Product.count).
            rx.checkbox(
                "Без фіксованої ємності",
                checked=state.no_fixed_capacity,
                on_change=state.set_no_fixed_capacity,
                size="3",
                disabled=state.uniq | ~state.divisible,
            ),
        ),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def add_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Каталог ТМЦ/Додавання",
            controls.button_primary("Зберегти", on_click=AddProductsState.on_save),
            left=controls.button_back(routes.CATALOG_PRODUCTS, label="Скасувати"),
            width="100%",
        ),
        _form_fields(AddProductsState, uniq_disabled=False),
        on_mount=AddProductsState.on_load,
    )


@require_login
def edit_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Каталог ТМЦ/Редагування",
            controls.button_primary("Зберегти", on_click=EditProductsState.on_save),
            left=controls.button_back(routes.CATALOG_PRODUCTS, label="Скасувати"),
            width="100%",
        ),
        # divisible/uniq заблоковані на редагуванні — одиниці вже могли бути
        # створені за старою логікою (див. CLAUDE.md).
        rx.skeleton(_form_fields(EditProductsState, uniq_disabled=True), loading=EditProductsState.in_process, height="100%"),
    )


def view_page_content() -> rx.Component:
    return rx.vstack(
        titled_section(
            "Основна інформація",
            field_row("Назва", ViewProductsState.title),
            field_row("Опис", ViewProductsState.description),
            field_row("Категорія", ViewProductsState.category),
            field_row("Одиниця виміру", ViewProductsState.unit),
        ),
        titled_section(
            "Параметри обліку",
            field_row("Кількість", ViewProductsState.count),
            field_row("Подільний", rx.cond(ViewProductsState.divisible, "Так", "Ні")),
            rx.cond(
                ViewProductsState.divisible,
                field_row("Місткість", rx.cond(ViewProductsState.no_fixed_capacity, "∞", ViewProductsState.capacity)),
            ),
            rx.cond(
                ViewProductsState.divisible,
                field_row("Без фіксованої ємності", rx.cond(ViewProductsState.no_fixed_capacity, "Так", "Ні")),
            ),
            field_row("Має серійний номер", rx.cond(ViewProductsState.uniq, "Так", "Ні")),
        ),
        history_block(ViewProductsState),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def view_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Каталог ТМЦ/Перегляд",
            rx.cond(
                ViewProductsState.get_user_actions.contains(Action.PRODUCTS_DELETE),
                controls.delete_with_confirm(on_confirm=ViewProductsState.on_click_delete),
            ),
            rx.cond(
                ViewProductsState.get_user_actions.contains(Action.PRODUCTS_EDIT),
                controls.button_primary("Редагувати", on_click=ViewProductsState.on_click_edit),
            ),
            left=controls.button_back(routes.CATALOG_PRODUCTS, label="Повернутись"),
            width="100%",
        ),
        rx.skeleton(view_page_content(), loading=ViewProductsState.in_process, height="100%"),
    )
