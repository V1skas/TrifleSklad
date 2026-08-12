import reflex as rx

from TrifleSklad.views.templates import controls


def _conflicts_table(state) -> rx.Component:
    """Пізніші рухи, що заблокували редагування — з переходом по кліку."""
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("№"),
                rx.table.column_header_cell("Тип"),
                rx.table.column_header_cell("Дата"),
                rx.table.column_header_cell("Статус"),
            ),
        ),
        rx.table.body(
            rx.foreach(
                state.full_edit_conflicts,
                lambda row: rx.table.row(
                    rx.table.cell(row[0]),
                    rx.table.cell(row[1]),
                    rx.table.cell(row[2]),
                    rx.table.cell(row[3]),
                    on_click=rx.redirect(row[4]),
                    cursor="pointer",
                    _hover={"background_color": rx.color("accent", 3)},
                ),
            ),
        ),
        variant="surface",
        width="100%",
        margin_top="0.75em",
    )


def full_edit_notice(state) -> rx.Component:
    """Плашка «Повне редагування недоступне» з поясненням причини. Показується
    лише коли форма урізана до статусу й коментаря."""
    return rx.cond(
        state.is_view_only_edit,
        rx.box(
            rx.vstack(
                rx.hstack(
                    rx.icon("info", size=18, color=rx.color("amber", 11), flex_shrink="0"),
                    rx.text(
                        "Доступні лише статус і коментар.",
                        size="2",
                        weight="medium",
                        color=rx.color("amber", 11),
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.text(state.full_edit_block_message, size="2", color=rx.color("gray", 11)),
                rx.cond(state.has_full_edit_conflicts, _conflicts_table(state)),
                spacing="2",
                align="start",
                width="100%",
            ),
            padding="0.75rem 1rem",
            border_radius="0.5rem",
            background_color=rx.color("amber", 2),
            border=f"1px solid {rx.color('amber', 6)}",
            width="100%",
        ),
    )


def reason_field(state) -> rx.Component:
    """Обов'язкове поле «Причина коригування»: текст іде в аудит-лог і видимий у
    блоці «Історія змін» усім, хто має право на історію."""
    return rx.cond(
        state.can_edit_full,
        rx.vstack(
            rx.text("*Причина коригування", size="2", weight="medium"),
            controls.text_area_field(
                placeholder="Чому змінюється вже проведений рух",
                value=state.edit_reason,
                on_change=state.on_change_edit_reason,
            ),
            rx.cond(
                state.edit_reason_error,
                rx.text("Вкажіть причину коригування!", size="1", color=rx.color("red", 11)),
            ),
            spacing="1",
            align="start",
            width="100%",
        ),
    )
