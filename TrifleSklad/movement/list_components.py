import reflex as rx

from TrifleSklad.movement.list_mixin import ALL


def filter_select(label: str, value, options, on_change) -> rx.Component:
    """Селект-фільтр зі сентинелом «Усі» (ALL). options — список (назва, id-рядок)."""
    return rx.vstack(
        rx.text(label, size="2"),
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
        spacing="1",
        min_width="12em",
    )


def _date_input(value, on_change, enabled) -> rx.Component:
    """Поле дати фільтра на «сирому» HTML-input: на відміну від Radix-TextField,
    він надійно тримає контрольоване value (зокрема при скиданні) і віддає рядок
    у on_change — інакше фільтр за датою не спрацьовував."""
    return rx.el.input(
        type="date",
        value=value,
        on_change=on_change,
        disabled=~enabled,
        border=f"1px solid {rx.color('gray', 7)}",
        border_radius="0.4em",
        padding="0.4em 0.6em",
        background_color=rx.color("gray", 1),
        color=rx.color("gray", 12),
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
    return rx.cond(
        State.is_filter_open,
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.text("Фільтрувати за датою", size="2"),
                    rx.switch(
                        checked=State.filter_date_enabled,
                        on_change=State.on_change_filter_date_enabled,
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.hstack(
                    rx.vstack(
                        rx.text("Дата від:", size="2"),
                        _date_input(
                            State.filter_date_from,
                            State.on_change_filter_date_from,
                            State.filter_date_enabled,
                        ),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Дата до:", size="2"),
                        _date_input(
                            State.filter_date_to,
                            State.on_change_filter_date_to,
                            State.filter_date_enabled,
                        ),
                        spacing="1",
                    ),
                    spacing="4",
                    wrap="wrap",
                ),
                rx.text("Статуси:", size="2"),
                rx.hstack(
                    rx.foreach(
                        State.statuses_for_filter,
                        lambda s: rx.checkbox(
                            s[1],
                            checked=s[2],
                            on_change=lambda checked: State.set_status(s[0], checked),
                        ),
                    ),
                    spacing="4",
                    wrap="wrap",
                ),
                rx.hstack(
                    *extra,
                    spacing="4",
                    wrap="wrap",
                    width="100%",
                ),
                rx.hstack(
                    rx.button(
                        "Скинути",
                        variant="soft",
                        color_scheme="gray",
                        on_click=State.reset_filters,
                    ),
                    rx.button("Застосувати", on_click=State.apply_filters),
                    spacing="3",
                    justify="end",
                    width="100%",
                ),
                spacing="3",
                width="100%",
            ),
            width="100%",
        ),
    )


def pagination(State) -> rx.Component:
    """Контроли сторінкування (Назад / номер / усього / Вперед)."""
    return rx.hstack(
        rx.button("Назад", variant="soft", on_click=State.current_page_decrement),
        rx.input(
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
