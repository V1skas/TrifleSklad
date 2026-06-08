import reflex as rx


def filter_button(State) -> rx.Component:
    """Кнопка-перемикач картки фільтра (для шапки списку)."""
    return rx.button(
        rx.icon("filter", size=16),
        "Фільтр",
        variant=rx.cond(State.has_active_filters, "solid", "ghost"),
        size="3",
        on_click=State.toggle_filter,
    )


def filter_card(State) -> rx.Component:
    """Картка фільтра за датою та статусами — з'являється по кнопці «Фільтр»."""
    return rx.cond(
        State.is_filter_open,
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.text("Дата від:", size="2"),
                        rx.input(
                            type="date",
                            value=State.filter_date_from,
                            on_change=State.on_change_filter_date_from,
                        ),
                        spacing="1",
                    ),
                    rx.vstack(
                        rx.text("Дата до:", size="2"),
                        rx.input(
                            type="date",
                            value=State.filter_date_to,
                            on_change=State.on_change_filter_date_to,
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
