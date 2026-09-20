import reflex as rx

from TrifleSklad.movement.list_mixin import ALL
from TrifleSklad.views.templates import controls


def filter_select(label: str, value, options, on_change) -> rx.Component:
    """Селект-фільтр зі сентинелом «Усі» (ALL) як окремий візуально
    відокремлений блок фільтра (`controls.filter_group`), щоб критерії в картці
    не зливались. options — список (назва, id-рядок)."""
    return controls.filter_group(
        label,
        rx.select.root(
            rx.select.trigger(placeholder="Усі", width="100%"),
            rx.select.content(
                rx.select.item("Усі", value=ALL),
                rx.foreach(options, lambda o: rx.select.item(o[0], value=o[1])),
                width="100%",
            ),
            value=value,
            on_change=on_change,
            width="100%",
        ),
    )


def _catalog_row(State, option) -> rx.Component:
    """Рядок мультивибору позиції каталогу: клік перемикає галочку.
    `option` — (id-рядок, «назва (одиниця)», чи обраний)."""
    return rx.hstack(
        rx.cond(
            option[2],
            rx.icon("check", size=16, color=rx.color("accent", 9)),
            rx.box(width="16px", height="16px", flex_shrink="0"),
        ),
        rx.text(option[1], size="2"),
        spacing="2",
        align="center",
        width="100%",
        padding="0.35em 0.5em",
        border_radius="0.35em",
        cursor="pointer",
        on_click=lambda: State.toggle_catalog(option[0]),
        _hover={"background_color": rx.color("accent", 3)},
    )


def catalog_filter(State) -> rx.Component:
    """Фільтр за позиціями каталогу, що входять до руху: кнопка-поповер зі
    списком і пошуком. Обрані позиції спливають наверх, повторний клік знімає
    вибір. Спільний для всіх типів руху (стан у MovementListFilterMixin)."""
    return controls.filter_group(
        "Товари в русі",
        rx.popover.root(
            rx.popover.trigger(
                rx.button(
                    rx.icon("package", size=16),
                    rx.cond(
                        State.catalog_filter_count > 0,
                        "Обрано: " + State.catalog_filter_count.to_string(),
                        "Оберіть товари",
                    ),
                    variant="soft",
                    color_scheme="gray",
                    width="100%",
                    justify="start",
                ),
            ),
            rx.popover.content(
                rx.vstack(
                    rx.select.root(
                        rx.select.trigger(placeholder="Усі категорії", width="100%"),
                        rx.select.content(
                            rx.select.item("Усі категорії", value=ALL),
                            rx.foreach(
                                State.list_categories,
                                lambda c: rx.select.item(c[0], value=c[1]),
                            ),
                            width="100%",
                        ),
                        value=State.catalog_filter_category,
                        on_change=State.set_catalog_category,
                        width="100%",
                    ),
                    controls.search_field(
                        rx.input.slot(rx.icon("search", size=16)),
                        placeholder="Пошук товару",
                        value=State.catalog_filter_search,
                        on_change=State.set_catalog_search,
                        width="100%",
                    ),
                    rx.scroll_area(
                        rx.vstack(
                            rx.foreach(
                                State.catalog_options_for_filter,
                                lambda option: _catalog_row(State, option),
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        type="hover",
                        scrollbars="vertical",
                        height="16em",
                        width="100%",
                    ),
                    spacing="2",
                    width="100%",
                ),
                width="24em",
                max_width="90vw",
            ),
        ),
    )


def _date_input(value, on_change, enabled) -> rx.Component:
    """Поле дати фільтра на «сирому» HTML-input: на відміну від Radix-TextField,
    він надійно тримає контрольоване value (зокрема при скиданні) і віддає рядок
    у on_change — інакше фільтр за датою не спрацьовував.
    Обгорнуте в debounce: фільтр застосовується одразу зі зміною, але з паузою —
    щоб ручне введення дати не смикало перезавантаження на кожен сегмент."""
    return rx.debounce_input(
        rx.el.input(
            type="date",
            value=value,
            on_change=on_change,
            disabled=~enabled,
            border=f"1px solid {rx.color('gray', 7)}",
            border_radius="0.4em",
            padding="0.4em 0.6em",
            background_color=rx.color("gray", 1),
            color=rx.color("gray", 12),
            width="100%",
            # Нативний date-input має власну мінімальну ширину під «дд.мм.рррр» +
            # іконку календаря; без цього flex стискає поле і дата обрізається.
            min_width="7em",
            flex="1",
        ),
        debounce_timeout=controls.SEARCH_DEBOUNCE_MS,
    )


def filter_button(State) -> rx.Component:
    """Кнопка-перемикач картки фільтра (для шапки списку)."""
    return rx.button(
        rx.icon("filter", size=16),
        "Фільтр",
        variant=rx.cond(State.has_active_filters, "solid", "ghost"),
        size="3",
        on_click=State.toggle_filter,
    )


def filter_card(State, *extra) -> rx.Component:
    """Картка фільтра за датою та статусами — з'являється по кнопці «Фільтр».
    `*extra` — додаткові контроли фільтра секції (склад/власник/відповідальний),
    рендеряться між статусами та кнопками дій."""
    return controls.filter_shell(
        State.is_filter_open,
        controls.filter_grid(
            controls.filter_group(
                "Період",
                # Обидві дати в один рядок — блок лишається заввишки як
                # сусідні селекти, тож сітка виходить рівною.
                rx.hstack(
                    _date_input(
                        State.filter_date_from,
                        State.on_change_filter_date_from,
                        State.filter_date_enabled,
                    ),
                    rx.text("—", size="2", flex_shrink="0"),
                    _date_input(
                        State.filter_date_to,
                        State.on_change_filter_date_to,
                        State.filter_date_enabled,
                    ),
                    spacing="2",
                    align="center",
                    width="100%",
                ),
                # Перемикач — у шапці блока, щоб не додавати зайвий рядок.
                action=rx.switch(
                    checked=State.filter_date_enabled,
                    on_change=State.on_change_filter_date_enabled,
                    size="1",
                ),
                # Дві дати не влазять в одну колонку сітки — блок на дві.
                wide=True,
            ),
            *extra,
            # Універсальний фільтр за позиціями каталогу — на всіх типах руху.
            catalog_filter(State),
        ),
        # Прапорці — окремою смугою на всю ширину: у ряд вони займають один
        # рядок, тоді як у вузькій колонці сітки розтягли б блок по висоті.
        controls.filter_group(
            "Статуси",
            rx.hstack(
                rx.foreach(
                    State.statuses_for_filter,
                    lambda s: rx.checkbox(
                        s[1],
                        checked=s[2],
                        on_change=lambda checked: State.set_status(s[0], checked),
                    ),
                ),
                spacing="5",
                wrap="wrap",
                align="center",
            ),
            height="auto",
        ),
        # Фільтри застосовуються одразу зі зміною полів — окремої кнопки
        # «Застосувати» немає; лишається тільки скидання.
        controls.filter_actions(
            rx.button(
                "Скинути",
                variant="soft",
                color_scheme="gray",
                on_click=State.reset_filters,
            ),
        ),
    )


def pagination(State) -> rx.Component:
    """Контроли сторінкування (Назад / номер / усього / Вперед)."""
    return rx.hstack(
        rx.button("Назад", variant="soft", on_click=State.current_page_decrement),
        controls.input_field(
            value=State.get_current_page,
            on_change=State.on_change_current_page,
            type="number",
            min="1",
            max=State.get_all_pages,
            width="5em",
            text_align="center",
        ),
        rx.text("/"),
        rx.text(State.get_all_pages),
        rx.button("Вперед", variant="soft", on_click=State.current_page_increment),
        spacing="2",
        align="center",
        justify="center",
        width="100%",
    )
