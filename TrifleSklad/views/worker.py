import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.models import Worker
from TrifleSklad.states.worker import (
    AddWorkerState,
    EditWorkerState,
    ListWorkersState,
    ViewWorkerState,
)
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.templates import controls
from TrifleSklad.views.templates.history import history_block
from TrifleSklad.views.templates.layouts import header_subpage, page_wrapper


def _table_row(item: Worker) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(item.fio, align="left"),
        rx.table.cell(item.position, align="left"),
        rx.table.cell(item.phone_number, align="left"),
        rx.table.cell(item.email, align="left"),
        on_click=rx.redirect(routes.ADMIN_WORKERS_VIEW_ID + item.id.to_string()),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def _table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Прізвище І.Б.", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Посада", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Телефон", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Email", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(ListWorkersState.items, _table_row),
        ),
        variant="surface",
        width="100%",
    )


def list_page_content() -> rx.Component:
    return rx.cond(
        ListWorkersState.has_items,
        _table(),
        controls.empty_placeholder(),
    )


@require_login
def list_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Співробітники",
            rx.cond(
                ListWorkersState.get_user_actions.contains(Action.WORKERS_CREATE),
                controls.button_primary("Створити", on_click=ListWorkersState.on_click_add),
            ),
            width="100%",
        ),
        rx.skeleton(list_page_content(), loading=ListWorkersState.in_progress, height="100%"),
        on_mount=ListWorkersState.on_load,
    )


def _form_fields(state) -> rx.Component:
    return rx.vstack(
        rx.text("*Прізвище І.Б.", weight="medium"),
        controls.input_field(value=state.worker_fio, on_change=state.set_worker_fio, width="100%"),
        rx.text("*Посада", weight="medium"),
        controls.input_field(value=state.position, on_change=state.set_position, width="100%"),
        rx.text("Телефон", weight="medium"),
        controls.input_field(type="tel", value=state.phone_number, on_change=state.set_phone_number, width="100%"),
        rx.text("Email", weight="medium"),
        controls.input_field(type="email", value=state.email, on_change=state.set_email, width="100%"),
        rx.hstack(
            rx.switch(checked=state.is_default, on_change=state.set_is_default),
            rx.text("За замовчуванням для рухів (отримувач/відповідальний)"),
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
            "Співробітники/Створення",
            controls.button_primary("Зберегти", on_click=AddWorkerState.on_save),
            left=controls.button_back(routes.ADMIN_WORKERS, label="Скасувати"),
            width="100%",
        ),
        _form_fields(AddWorkerState),
        on_mount=AddWorkerState.on_load,
    )


@require_login
def edit_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Співробітники/Редагування",
            controls.button_primary("Зберегти", on_click=EditWorkerState.on_save),
            left=controls.button_back(routes.ADMIN_WORKERS, label="Скасувати"),
            width="100%",
        ),
        rx.skeleton(_form_fields(EditWorkerState), loading=EditWorkerState.in_process, height="100%"),
    )


def view_page_content() -> rx.Component:
    return rx.vstack(
        rx.heading(ViewWorkerState.worker_fio, size="7", width="100%"),
        rx.hstack(rx.text("Посада:", weight="medium"), rx.text(ViewWorkerState.position), width="100%"),
        rx.hstack(rx.text("Телефон:", weight="medium"), rx.text(ViewWorkerState.phone_number), width="100%"),
        rx.hstack(rx.text("Ел. пошта:", weight="medium"), rx.text(ViewWorkerState.email), width="100%"),
        rx.hstack(
            rx.text("За замовчуванням для рухів:", weight="medium"),
            rx.text(rx.cond(ViewWorkerState.is_default, "Так", "Ні")),
            width="100%",
        ),
        history_block(ViewWorkerState),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def view_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Співробітники/Перегляд",
            rx.cond(
                ViewWorkerState.get_user_actions.contains(Action.WORKERS_DELETE),
                controls.delete_with_confirm(on_confirm=ViewWorkerState.on_click_delete),
            ),
            rx.cond(
                ViewWorkerState.get_user_actions.contains(Action.WORKERS_EDIT),
                controls.button_primary("Редагувати", on_click=ViewWorkerState.on_click_edit),
            ),
            left=controls.button_back(routes.ADMIN_WORKERS, label="Повернутись"),
            width="100%",
        ),
        rx.skeleton(view_page_content(), loading=ViewWorkerState.in_process, height="100%"),
    )
