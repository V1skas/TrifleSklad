import reflex as rx

from TrifleSklad.views.templates import controls


def _action_badge(action_label) -> rx.Component:
    return rx.match(
        action_label,
        ("Створення", rx.badge("Створення", color_scheme="green", variant="soft", size="1")),
        ("Видалення", rx.badge("Видалення", color_scheme="red", variant="soft", size="1")),
        rx.badge(action_label, color_scheme="blue", variant="soft", size="1"),
    )


def _detail_row(row) -> rx.Component:
    return rx.hstack(
        rx.text(row[0], size="2", weight="medium", color=rx.color("gray", 12), width="35%", flex_shrink="0"),
        rx.hstack(
            rx.cond(
                row[1] != "",
                rx.text(row[1], size="2", color=rx.color("red", 10), text_decoration="line-through"),
            ),
            rx.cond(
                (row[1] != "") & (row[2] != ""),
                rx.icon("arrow-right", size=13, color=rx.color("gray", 9)),
            ),
            rx.cond(
                row[2] != "",
                rx.text(row[2], size="2", color=rx.color("grass", 10), weight="medium"),
            ),
            spacing="2",
            wrap="wrap",
            align="center",
        ),
        width="100%",
        align="start",
        padding_y="0.3em",
    )


def _detail_list(details) -> rx.Component:
    return rx.vstack(
        rx.divider(),
        rx.foreach(details, _detail_row),
        spacing="1",
        width="100%",
        align="stretch",
    )


def _history_card(state, entry) -> rx.Component:
    log_id = entry[0]
    expanded = state.history_expanded[log_id]
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.hstack(
                        _action_badge(entry[3]),
                        rx.text(entry[1], size="2", color=rx.color("gray", 10)),
                        spacing="2",
                        align="center",
                    ),
                    rx.text(entry[4], size="2", weight="medium", width="100%"),
                    # Причина коригування видима без права на деталізацію —
                    # це «навіщо», а не «що саме змінилось».
                    rx.cond(
                        entry[6] != "",
                        rx.text(
                            f"Причина коригування: {entry[6]}",
                            size="2",
                            color=rx.color("amber", 11),
                            width="100%",
                        ),
                    ),
                    rx.text(entry[2], size="1", color=rx.color("gray", 9)),
                    spacing="1",
                    align="start",
                    width="100%",
                ),
                rx.spacer(),
                rx.cond(
                    state.can_view_history_detail,
                    rx.icon(
                        "chevron-down",
                        size=18,
                        color=rx.color("gray", 9),
                        style={
                            "transform": rx.cond(expanded, "rotate(0deg)", "rotate(-90deg)"),
                            "transition": "transform 0.15s",
                            "flex_shrink": "0",
                        },
                    ),
                ),
                width="100%",
                align="center",
            ),
            rx.cond(
                state.can_view_history_detail,
                rx.cond(expanded, _detail_list(entry[5])),
            ),
            spacing="2",
            width="100%",
            align="stretch",
        ),
        on_click=state.toggle_history(log_id),
        cursor=rx.cond(state.can_view_history_detail, "pointer", "default"),
        _hover={"background_color": rx.color("accent", 2)},
        width="100%",
    )


def _history_list(state) -> rx.Component:
    return rx.vstack(
        rx.foreach(state.history_entries, lambda entry: _history_card(state, entry)),
        spacing="2",
        width="100%",
        align="stretch",
    )


def history_block(state) -> rx.Component:
    """Блок «Історія змін» — додається останнім child'ом у `view_page_content()`
    кожного екрана детального перегляду. `state` — клас `View*State`, що
    підмішує `AuditHistoryMixin` (`states/audit_mixin.py`). Список карток:
    клік по картці розгортає деталізацію змін (лише за наявності права
    `history_detail` — інакше картка неактивна, деталі й не надсилаються
    на клієнт, див. `AuditHistoryMixin._load_history`)."""
    return rx.cond(
        state.can_view_history,
        rx.vstack(
            rx.heading("Історія змін", size="4", width="100%"),
            rx.cond(
                state.has_history,
                _history_list(state),
                controls.empty_placeholder("Історія змін відсутня"),
            ),
            spacing="3",
            width="100%",
        ),
    )
