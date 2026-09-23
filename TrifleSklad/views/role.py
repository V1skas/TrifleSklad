import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.models import Action, Role
from TrifleSklad.states.role import (
    AddRoleState,
    EditRoleState,
    ListRoleState,
    ViewRoleState,
)
from TrifleSklad.views.actions_picker import actions_picker
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.templates import controls
from TrifleSklad.views.templates.history import history_block
from TrifleSklad.views.templates.layouts import field_row, header_subpage, page_wrapper, titled_section


def _list_action_item(item: Action) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.heading(item.title, size="3", user_select="none"),
            rx.text(item.description, size="1", user_select="none"),
            spacing="0",
            width="100%",
        ),
        background_color=rx.color("accent", 2),
        border_color=rx.color("accent", 4),
        border_width="1px",
        width="100%",
    )


def _table_row(item: Role) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(item.title, align="left"),
        on_click=rx.redirect(routes.ADMIN_ROLES_VIEW_ID + item.id.to_string()),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def _table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(rx.table.column_header_cell("Назва", color=rx.color("accent", 2))),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(rx.foreach(ListRoleState.items, _table_row)),
        variant="surface",
        width="100%",
    )


def list_page_content() -> rx.Component:
    return rx.cond(ListRoleState.has_items, _table(), controls.empty_placeholder())


@require_login
def list_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Ролі",
            rx.cond(
                ListRoleState.get_user_actions.contains(ActionEnum.ROLES_CREATE),
                controls.button_primary("Створити", on_click=ListRoleState.on_click_add),
            ),
            width="100%",
        ),
        rx.skeleton(list_page_content(), loading=ListRoleState.in_progress, height="100%"),
        on_mount=ListRoleState.on_load,
    )


def _actions_dialog(state) -> rx.Component:
    return rx.dialog.root(
        rx.hstack(
            rx.text("*Права:"),
            rx.spacer(),
            rx.dialog.trigger(rx.button("Вибрати права", size="2", type="button")),
            align="center",
            width="100%",
        ),
        rx.dialog.content(
            actions_picker(
                rx.hstack(
                    rx.dialog.close(controls.dialog_cancel_button("Скасувати")),
                    rx.spacer(),
                    rx.dialog.close(controls.dialog_confirm_button("Готово", on_click=state.apply_actions)),
                    width="100%",
                ),
                height="90vh",
            ),
            padding="0",
            on_open_auto_focus=state.open_actions,
        ),
    )


def _form_fields(state) -> rx.Component:
    return rx.vstack(
        titled_section(
            "Інформація",
            rx.text("*Назва:"),
            controls.input_field(value=state.item.title, on_change=state.set_title, width="100%"),
            rx.text("Опис:"),
            controls.text_area_field(value=state.description, on_change=state.set_description, width="100%"),
        ),
        titled_section(
            "Права",
            _actions_dialog(state),
            rx.scroll_area(
                rx.vstack(
                    rx.cond(
                        state.has_selected_actions,
                        rx.foreach(state.item.actions, _list_action_item),
                        rx.center(rx.text("Нічого не обрано"), width="100%", size="3"),
                    ),
                    spacing="1",
                    width="100%",
                    # Overlay-скролбар (macOS) інакше малюється поверх правого
                    # краю карток — див. те саме в page_wrapper (layouts.py).
                    padding_right="0.75em",
                ),
                spacing="1",
                width="100%",
                # height="fit-content" + max_height — картка росте разом із
                # вмістом (мало прав — мало місця), але не безмежно: за межею
                # увімкається прокрутка.
                height="fit-content",
                max_height="30em",
            ),
        ),
        align="stretch",
        spacing="3",
        width="100%",
    )


@require_login
def add_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Ролі/Додавання",
            controls.button_primary("Зберегти", on_click=AddRoleState.on_save),
            left=controls.button_back(routes.ADMIN_ROLES, label="Скасувати"),
            width="100%",
        ),
        _form_fields(AddRoleState),
        on_mount=AddRoleState.on_load,
    )


@require_login
def edit_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Ролі/Редагування",
            controls.button_primary("Зберегти", on_click=EditRoleState.on_save),
            left=controls.button_back(routes.ADMIN_ROLES, label="Скасувати"),
            width="100%",
        ),
        rx.skeleton(_form_fields(EditRoleState), loading=EditRoleState.in_process, height="100%"),
    )


def view_page_content() -> rx.Component:
    return rx.vstack(
        titled_section(
            "Інформація",
            field_row("Назва", ViewRoleState.item.title),
            field_row("Опис", ViewRoleState.description),
        ),
        titled_section(
            "Права",
            rx.scroll_area(
                rx.vstack(
                    rx.cond(
                        ViewRoleState.has_actions,
                        rx.foreach(ViewRoleState.item.actions, _list_action_item),
                        rx.center(rx.text("Нічого не обрано"), width="100%", size="3"),
                    ),
                    spacing="1",
                    width="100%",
                    padding_right="0.75em",
                ),
                spacing="1",
                width="100%",
                height="fit-content",
                max_height="30em",
            ),
        ),
        history_block(ViewRoleState),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def view_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Ролі/Перегляд",
            rx.cond(
                ViewRoleState.get_user_actions.contains(ActionEnum.ROLES_DELETE),
                controls.delete_with_confirm(on_confirm=ViewRoleState.on_click_delete),
            ),
            rx.cond(
                ViewRoleState.get_user_actions.contains(ActionEnum.ROLES_EDIT),
                controls.button_primary("Редагувати", on_click=ViewRoleState.on_click_edit),
            ),
            left=controls.button_back(routes.ADMIN_ROLES, label="Повернутись"),
            width="100%",
        ),
        rx.skeleton(view_page_content(), loading=ViewRoleState.in_process, height="100%"),
    )
