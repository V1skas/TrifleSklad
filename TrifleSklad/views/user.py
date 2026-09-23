import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.models import Action, Role, User
from TrifleSklad.states.user import AddUserState, EditUserState, ListUserState, ViewUserState
from TrifleSklad.views.actions_picker import actions_picker
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.role_selector import role_selector
from TrifleSklad.views.templates import controls
from TrifleSklad.views.templates.history import history_block
from TrifleSklad.views.templates.layouts import field_row, header_subpage, page_wrapper, titled_section


def _list_role_item(item: Role) -> rx.Component:
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


def _table_row(item: User) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(item.login, align="left"),
        rx.table.cell(item.worker.fio, align="left"),
        rx.table.cell(item.worker.position, align="left"),
        on_click=rx.redirect(routes.ADMIN_USERS_VIEW_ID + item.login),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )


def _table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Логін", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Співробітник", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Посада", color=rx.color("accent", 2)),
            ),
            background_color=rx.color("accent", 9),
        ),
        rx.table.body(rx.foreach(ListUserState.items, _table_row)),
        variant="surface",
        width="100%",
    )


def list_page_content() -> rx.Component:
    return rx.cond(ListUserState.has_items, _table(), controls.empty_placeholder())


@require_login
def list_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Користувачі",
            rx.cond(
                ListUserState.get_user_actions.contains(ActionEnum.USERS_CREATE),
                controls.button_primary("Створити", on_click=ListUserState.on_click_add),
            ),
            width="100%",
        ),
        rx.skeleton(list_page_content(), loading=ListUserState.in_progress, height="100%"),
        on_mount=ListUserState.on_load,
    )


def _roles_dialog(state) -> rx.Component:
    return rx.dialog.root(
        rx.hstack(
            rx.heading("Надані ролі:", size="3"),
            rx.spacer(),
            rx.dialog.trigger(rx.button("Обрати ролі", size="2", type="button")),
            align="center",
            width="100%",
        ),
        rx.dialog.content(
            role_selector(
                rx.hstack(
                    rx.dialog.close(controls.dialog_cancel_button("Скасувати")),
                    rx.spacer(),
                    rx.dialog.close(controls.dialog_confirm_button("Зберегти", on_click=state.apply_roles)),
                    width="100%",
                ),
                height="90vh",
            ),
            padding="0",
            on_open_auto_focus=state.open_roles,
        ),
    )


def _actions_dialog(state) -> rx.Component:
    return rx.dialog.root(
        rx.hstack(
            rx.heading("Персональні дозволи:", size="3"),
            rx.spacer(),
            rx.dialog.trigger(rx.button("Обрати дозволи", size="2", type="button")),
            align="center",
            width="100%",
        ),
        rx.dialog.content(
            actions_picker(
                rx.hstack(
                    rx.dialog.close(controls.dialog_cancel_button("Скасувати")),
                    rx.spacer(),
                    rx.dialog.close(controls.dialog_confirm_button("Зберегти", on_click=state.apply_actions)),
                    width="100%",
                ),
                height="90vh",
            ),
            padding="0",
            on_open_auto_focus=state.open_actions,
        ),
    )


def _worker_select(value, on_change, workers) -> rx.Component:
    return rx.select.root(
        rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
        rx.select.content(rx.foreach(workers, lambda w: rx.select.item(w[0], value=w[1])), width="100%"),
        value=value,
        on_change=on_change,
        width="100%",
    )


def add_page_content() -> rx.Component:
    return rx.vstack(
        titled_section(
            "Інформація",
            rx.text("*Логін:"),
            controls.input_field(value=AddUserState.login, on_change=AddUserState.set_login, width="100%"),
            rx.text("*Пароль:"),
            controls.input_field(value=AddUserState.password, on_change=AddUserState.set_password, width="100%"),
            rx.text("*Співробітник:"),
            _worker_select(AddUserState.id_worker, AddUserState.set_id_worker, AddUserState.list_workers),
        ),
        titled_section(
            "Права доступу",
            _roles_dialog(AddUserState),
            rx.scroll_area(
                rx.vstack(
                    rx.cond(
                        AddUserState.has_roles,
                        rx.foreach(AddUserState.item.roles, _list_role_item),
                        rx.center(rx.text("Нічого не обрано", color="gray"), width="100%", size="3"),
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
                # вмістом (мало обрано — мало місця), але не безмежно.
                height="fit-content",
                max_height="30em",
            ),
            _actions_dialog(AddUserState),
            rx.scroll_area(
                rx.vstack(
                    rx.cond(
                        AddUserState.has_actions,
                        rx.foreach(AddUserState.item.actions, _list_action_item),
                        rx.center(rx.text("Нічого не обрано", color="gray"), width="100%", size="3"),
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
        align="stretch",
        spacing="3",
        width="100%",
    )


@require_login
def add_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Користувачі/Додавання",
            controls.button_primary("Зберегти", on_click=AddUserState.on_save),
            left=controls.button_back(routes.ADMIN_USERS, label="Скасувати"),
            width="100%",
        ),
        add_page_content(),
        on_mount=AddUserState.on_load,
    )


def edit_page_content() -> rx.Component:
    return rx.vstack(
        titled_section(
            "Інформація",
            rx.text("Логін:"),
            controls.input_field(value=EditUserState.item.login, disabled=True, width="100%"),
            rx.text("Пароль (залиште порожнім, щоб не змінювати):"),
            controls.input_field(value=EditUserState.password, on_change=EditUserState.set_password, width="100%"),
            rx.text("*Співробітник:"),
            _worker_select(EditUserState.id_worker, EditUserState.set_id_worker, EditUserState.list_workers),
        ),
        titled_section(
            "Права доступу",
            _roles_dialog(EditUserState),
            rx.scroll_area(
                rx.vstack(
                    rx.cond(
                        EditUserState.has_roles,
                        rx.foreach(EditUserState.item.roles, _list_role_item),
                        rx.center(rx.text("Нічого не обрано", color="gray"), width="100%", size="3"),
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
            _actions_dialog(EditUserState),
            rx.scroll_area(
                rx.vstack(
                    rx.cond(
                        EditUserState.has_actions,
                        rx.foreach(EditUserState.item.actions, _list_action_item),
                        rx.center(rx.text("Нічого не обрано", color="gray"), width="100%", size="3"),
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
        align="stretch",
        spacing="3",
        width="100%",
    )


@require_login
def edit_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Користувачі/Редагування",
            controls.button_primary("Зберегти", on_click=EditUserState.on_save),
            left=controls.button_back(routes.ADMIN_USERS, label="Скасувати"),
            width="100%",
        ),
        rx.skeleton(edit_page_content(), loading=EditUserState.in_process, height="100%"),
    )


def view_page_content() -> rx.Component:
    return rx.vstack(
        titled_section(
            "Інформація",
            field_row("Логін", ViewUserState.item.login),
            field_row("Співробітник", ViewUserState.item.worker.fio),
        ),
        titled_section(
            "Права доступу",
            rx.text("Призначені ролі", weight="medium"),
            rx.scroll_area(
                rx.vstack(
                    rx.cond(
                        ViewUserState.has_roles,
                        rx.foreach(ViewUserState.item.roles, _list_role_item),
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
            rx.text("Персональні дозволи", weight="medium"),
            rx.scroll_area(
                rx.vstack(
                    rx.cond(
                        ViewUserState.has_actions,
                        rx.foreach(ViewUserState.item.actions, _list_action_item),
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
        history_block(ViewUserState),
        spacing="3",
        align="stretch",
        width="100%",
    )


@require_login
def view_page() -> rx.Component:
    return page_wrapper(
        header_subpage(
            "Користувачі/Перегляд",
            rx.cond(
                ViewUserState.get_user_actions.contains(ActionEnum.USERS_DELETE),
                controls.delete_with_confirm(on_confirm=ViewUserState.on_click_delete),
            ),
            rx.cond(
                ViewUserState.get_user_actions.contains(ActionEnum.USERS_EDIT),
                controls.button_primary("Редагувати", on_click=ViewUserState.on_click_edit),
            ),
            left=controls.button_back(routes.ADMIN_USERS, label="Повернутись"),
            width="100%",
        ),
        rx.skeleton(view_page_content(), loading=ViewUserState.in_process, height="100%"),
    )
