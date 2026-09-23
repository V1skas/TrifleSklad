import reflex as rx

from TrifleSklad.movement.list_components import pagination
from TrifleSklad.states.catalog_movements_report import ALL, CatalogMovementsReportState
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.templates import controls
from TrifleSklad.views.templates.layouts import header_subpage, page_wrapper

State = CatalogMovementsReportState


def _filter_select(label, value, options, on_change, search_value=None, on_search=None) -> rx.Component:
    """Селект-фільтр зі сентинелом «Усі» та опційним полем пошуку всередині
    (для довгих списків складів). options — список (id, назва)."""
    content = []
    if on_search is not None:
        content.append(
            controls.input_field(
                rx.input.slot(rx.icon("search")),
                placeholder="Пошук",
                value=search_value,
                on_change=on_search,
                width="100%",
                margin_bottom="0.5em",
            )
        )
    content.append(rx.select.item("Усі", value=ALL))
    content.append(rx.foreach(options, lambda opt: rx.select.item(opt[1], value=opt[0])))
    return controls.filter_group(
        label,
        rx.select.root(
            rx.select.trigger(placeholder="Усі", width="100%"),
            rx.select.content(*content, width="100%"),
            value=value,
            on_change=on_change,
            width="100%",
        ),
    )


def _date_input(value, on_change) -> rx.Component:
    """Поле дати фільтра на «сирому» HTML-input (як у списках руху): надійно
    тримає контрольоване value і віддає рядок у on_change."""
    return rx.debounce_input(
        rx.el.input(
            type="date",
            value=value,
            on_change=on_change,
            border=f"1px solid {rx.color('gray', 7)}",
            border_radius="0.4em",
            padding="0.4em 0.6em",
            background_color=rx.color("gray", 1),
            color=rx.color("gray", 12),
            width="100%",
            min_width="7em",
            flex="1",
        ),
        debounce_timeout=controls.SEARCH_DEBOUNCE_MS,
    )


def _filter_card() -> rx.Component:
    return rx.card(
        rx.vstack(
            controls.filter_grid(
                controls.filter_group(
                    "Пошук",
                    controls.search_field(
                        rx.input.slot(rx.icon("search")),
                        placeholder="Назва позиції каталогу",
                        value=State.search_text,
                        on_change=State.on_change_search_text,
                        width="100%",
                    ),
                    wide=True,
                ),
                _filter_select(
                    "Категорія",
                    State.filter_category_value,
                    State.list_categories,
                    State.on_change_category,
                ),
                _filter_select(
                    "Об'єкт відправлення",
                    State.filter_incoming_storage_value,
                    State.filtered_incoming_storages,
                    State.on_change_incoming_storage,
                    search_value=State.search_incoming_storage,
                    on_search=State.on_change_search_incoming_storage,
                ),
                _filter_select(
                    "Об'єкт отримання",
                    State.filter_destination_storage_value,
                    State.filtered_destination_storages,
                    State.on_change_destination_storage,
                    search_value=State.search_destination_storage,
                    on_search=State.on_change_search_destination_storage,
                ),
                _filter_select(
                    "Власник відправлення",
                    State.filter_incoming_owner_value,
                    State.list_owners,
                    State.on_change_incoming_owner,
                ),
                _filter_select(
                    "Власник отримання",
                    State.filter_destination_owner_value,
                    State.list_owners,
                    State.on_change_destination_owner,
                ),
                controls.filter_group(
                    "Період",
                    rx.hstack(
                        _date_input(State.date_from, State.on_change_date_from),
                        rx.text("—", size="2", flex_shrink="0"),
                        _date_input(State.date_to, State.on_change_date_to),
                        spacing="2",
                        align="center",
                        width="100%",
                    ),
                    wide=True,
                ),
            ),
            controls.filter_group(
                "Скасовані рухи",
                rx.checkbox(
                    "Виключити скасовані рухи",
                    checked=State.exclude_canceled,
                    on_change=State.on_change_exclude_canceled,
                ),
                height="auto",
            ),
            controls.filter_actions(
                rx.button("Скинути фільтри", variant="soft", type="button", on_click=State.reset_filters),
            ),
            spacing="3",
            width="100%",
        ),
        width="100%",
    )


def _dialog_pagination() -> rx.Component:
    """Пагінація діалогу рухів — окрема від пагінації головної таблиці
    (спільний `list_components.pagination` жорстко зав'язаний на її computed vars,
    тож для діалогу — власний контрол на dialog_* полях стейту)."""
    return rx.hstack(
        rx.button("Назад", variant="soft", on_click=State.dialog_page_decrement),
        controls.input_field(
            value=State.dialog_current_page,
            on_change=State.on_change_dialog_page,
            type="number",
            min="1",
            max=State.dialog_all_pages,
            width="5em",
            text_align="center",
        ),
        rx.text("/"),
        rx.text(State.dialog_all_pages),
        rx.button("Вперед", variant="soft", on_click=State.dialog_page_increment),
        spacing="2",
        align="center",
        justify="center",
        width="100%",
    )


def _movements_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            controls.dialog_heading(f"Рухи: {State.selected_title}"),
            rx.cond(
                State.movement_rows.length() > 0,
                rx.vstack(
                    rx.table.root(
                        rx.table.header(
                            rx.table.row(
                                rx.table.column_header_cell("№", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                                rx.table.column_header_cell("Тип", color=rx.color("accent", 2)),
                                rx.table.column_header_cell("Дата", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                                rx.table.column_header_cell("Відправник", color=rx.color("accent", 2)),
                                rx.table.column_header_cell("Отримувач", color=rx.color("accent", 2)),
                                rx.table.column_header_cell("Кількість", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                                rx.table.column_header_cell("Статус", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                            ),
                            background_color=rx.color("accent", 9),
                        ),
                        rx.table.body(
                            rx.foreach(
                                State.movement_rows,
                                lambda m: rx.table.row(
                                    rx.table.cell(m[0], width="1%", white_space="nowrap"),
                                    rx.table.cell(m[1]),
                                    rx.table.cell(m[2], width="1%", white_space="nowrap"),
                                    rx.table.cell(m[3]),
                                    rx.table.cell(m[4]),
                                    rx.table.cell(m[5], width="1%", white_space="nowrap"),
                                    rx.table.cell(m[6], width="1%", white_space="nowrap"),
                                    on_click=rx.redirect(m[7]),
                                    cursor="pointer",
                                    _hover={"background_color": rx.color("accent", 3)},
                                ),
                            ),
                        ),
                        variant="surface",
                        width="100%",
                        margin_top="1em",
                    ),
                    _dialog_pagination(),
                    spacing="3",
                    width="100%",
                ),
                rx.center(rx.text("Рухів не знайдено", color="gray"), width="100%", padding="2em"),
            ),
            rx.flex(
                rx.dialog.close(rx.button("Закрити", on_click=State.set_movements_open(False))),
                justify="end",
                margin_top="1em",
            ),
            max_width="60em",
        ),
        open=State.is_movements_open,
        on_open_change=State.set_movements_open,
    )


def _table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Назва позиції", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Категорія", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Одиниця виміру", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
                rx.table.column_header_cell("Кількість рухів", color=rx.color("accent", 2), width="1%", white_space="nowrap"),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(
                State.rows,
                lambda row: rx.table.row(
                    rx.table.cell(row[1]),
                    rx.table.cell(row[3]),
                    rx.table.cell(row[2], width="1%", white_space="nowrap"),
                    rx.table.cell(row[4], width="1%", white_space="nowrap"),
                    on_click=State.open_movements(row[0], row[1]),
                    cursor="pointer",
                    _hover={"background_color": rx.color("accent", 3)},
                ),
            ),
        ),
        variant="surface",
        width="100%",
    )


def page_content() -> rx.Component:
    return rx.vstack(
        _filter_card(),
        rx.cond(
            State.has_rows,
            _table(),
            controls.empty_placeholder("Рухів по каталогу не знайдено"),
        ),
        pagination(State),
        _movements_dialog(),
        spacing="4",
        width="100%",
    )


@require_login
def page() -> rx.Component:
    return page_wrapper(
        header_subpage("Звіти/Рух по каталогу", width="100%"),
        rx.skeleton(page_content(), loading=State.in_progress, height="100%"),
        on_mount=State.on_load,
    )
