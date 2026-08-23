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


def save_reason_dialog(state) -> rx.Component:
    """Діалог підтвердження збереження повного редагування — необов'язкова
    причина коригування (TS-56). Текст іде в аудит-лог і видимий у блоці
    «Історія змін» усім, хто має право на історію. Показується лише коли
    доступне повне редагування — «Зберегти» відкриває цей діалог
    (`FullEditMixin.open_save_dialog`), для урізаного редагування
    зберігається одразу."""
    return controls.confirm_with_reason_dialog(
        open=state.is_save_dialog_open,
        on_open_change=state.set_save_dialog_open,
        value=state.edit_reason,
        on_change=state.on_change_edit_reason,
        on_confirm=state.confirm_save,
        title="Причина коригування",
        confirm_label="Зберегти",
        confirm_color_scheme="blue",
        placeholder="Чому змінюється вже проведений рух",
    )
