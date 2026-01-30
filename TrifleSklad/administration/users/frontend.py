import reflex as rx

from TrifleSklad import routes
from TrifleSklad.administration.users.backend import *
from TrifleSklad.models import User, Role, Action, Worker
from TrifleSklad.dao import WorkerDAO

import TrifleSklad.administration.roles as roles
import TrifleSklad.administration.actions as actions

def list_role_item(item: Tuple[int, Role]) -> rx.Component:
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

def list_action_item(item: Tuple[int, Action]) -> rx.Component:
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

def item_preview(item: Tuple[int, User]) -> rx.Component:
    return rx.vstack(
        rx.heading(item[1].login, size="7", width="100%"),
        rx.text(item[1].worker.fio, width="100%"),
        rx.heading("Назначенные роли:", size="3", width="100%"),
        rx.scroll_area(
            rx.vstack(
                rx.cond(
                    UserState.has_selected_roles,
                    rx.foreach(UserState.selected_roles, list_role_item),
                    rx.center(rx.text("Ничего не выбрано"), width="100%", size="3")
                ),

                spacing="1",

                width="100%",
                height="100%",
            ),

            spacing="1",
            width="100%",
        ),
        rx.heading("Персональные права:", size="3", width="100%"),
        rx.scroll_area(
            rx.vstack(
                rx.cond(
                    UserState.has_selected_actions,
                    rx.foreach(UserState.selected_actions, list_action_item),
                    rx.center(rx.text("Ничего не выбрано"), width="100%", size="3")
                ),

                spacing="1",

                width="100%",
                height="100%",
            ),


            spacing="1",
            width="100%",
        ),
        rx.spacer(),
        rx.hstack(
            rx.button(
                "Редактировать",

                on_click=rx.redirect(f"{routes.ADMIN_USERS_EDIT_ID}{item[1].login}")
            ),
            rx.spacer(),
            rx.button(
                "Удалить",
                color_scheme="red",

                on_click=UserState.delete_one
            ),

            width="100%",
        ),

        spacing="3",

        height="100%",
        width="100%"
    )

def item_preview_tab_content() -> rx.Component:
    return rx.tabs.content(
        item_preview(UserState.get_selected_item),

        value=UserState.Pages.VIEW
    )

def table_row(item: Tuple[int, User]) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(
            rx.link(
                item[1].login,
                href=f"{routes.ADMIN_USERS_VIEW_ID}{item[1].login}",
            ),

            align="left"
        ),
        rx.table.cell(
            item[1].worker.fio,
            align="left"
        ),
        rx.table.cell(
            item[1].worker.position,
            align="left"
        ),
    )

def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Логин", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Сотрудник", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Должность", color=rx.color("accent", 2)),
            ),

            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(UserState.get_items, table_row),

            height="100px",
            width="100%"
        ),

        variant="surface",
        height="100%",
        width="100%"
    )

def list_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            rx.hstack(
                rx.heading("Пользователи", size="6"),
                rx.spacer(),
                rx.button(
                    "Добавить",
                    on_click=rx.redirect(routes.ADMIN_USERS_ADD)
                ),

                width="100%"
            ),
            rx.cond(UserState.has_items,
                table(),
                rx.text("Записей нет.")
            ),

            width="100%",
            height="100%",
        ),

        value=UserState.Pages.LIST,
    )

def add_form() -> rx.Component:
    return rx.card(
        rx.form(
            rx.vstack(
                rx.text("Логин:"),
                rx.input(id="login", required=True, size="3", is_disabled=True),
                rx.text("Пароль:"),
                rx.input(id="password", size="3"),
                rx.text("Сотрудник:"),
                rx.select(
                    [k.fio for k in WorkerDAO.get_all()],
                    
                    name="worker",
                    placeholder="Выберите сотрудника",
                    required=True
                ),
                rx.heading("Назначенные роли:", size="3", width="100%"),
                rx.scroll_area(
                    rx.vstack(
                        rx.cond(
                            UserState.has_selected_roles,
                            rx.foreach(UserState.selected_roles, list_role_item),
                            rx.center(rx.text("Ничего не выбрано", color="gray"), width="100%", size="3")
                        ),

                        spacing="1",

                        width="100%",
                        height="100%",
                    ),


                    spacing="1",
                    width="100%",
                    max_height="90%",
                ),
                rx.dialog.root(
                    rx.dialog.trigger(
                        rx.button("Выбрать роли", size="2", width="12em",)
                    ),
                    rx.dialog.content(
                        roles.frontend.selector(
                            rx.hstack(
                                rx.dialog.close(rx.button("Отмена", variant="surface", size="3"),),
                                rx.spacer(),
                                rx.dialog.close(rx.button("Готово",
                                                        size="3",
                                                        on_click=[UserState.set_selected_roles(roles.backend.RoleSelectorState.get_id_selected_items)]),),

                                width="100%",
                            ),

                            height="50em",
                        ),

                        padding="0",

                        on_open_auto_focus=[roles.backend.RoleSelectorState.on_load(UserState.selected_roles)]
                    ),
                ),
                rx.heading("Персональные права:", size="3", width="100%"),
                rx.scroll_area(
                    rx.vstack(
                        rx.cond(
                            UserState.has_selected_actions,
                            rx.foreach(UserState.selected_actions, list_action_item),
                            rx.center(rx.text("Ничего не выбрано", color="gray"), width="100%", size="3")
                        ),

                        spacing="1",

                        width="100%",
                        height="100%",
                    ),


                    spacing="1",
                    width="100%",
                    max_height="90%",
                ),
                rx.dialog.root(
                    rx.dialog.trigger(
                        rx.button("Выбрать права", size="2", width="12em",)
                    ),
                    rx.dialog.content(
                        actions.frontend.index(
                            rx.hstack(
                                rx.dialog.close(rx.button("Отмена", variant="surface", size="3"),),
                                rx.spacer(),
                                rx.dialog.close(rx.button("Готово",
                                                        size="3",
                                                        on_click=[UserState.set_selected_actions(actions.backend.ActionsState.get_id_selected_items)]),),

                                width="100%",
                            ),

                            height="50em",
                        ),

                        padding="0",

                        on_open_auto_focus=[actions.backend.ActionsState.on_load(UserState.selected_actions)]
                    ),
                ),
                rx.hstack(
                    rx.button("Отмена", type="reset", color_scheme="red", on_click=rx.redirect(routes.ADMIN_USERS)),
                    rx.button("Сохранить", color_scheme="green", type="submit"),

                    justify="end"
                ),

                align="stretch"
            ),

            on_submit=UserState.add_one,
        ),

        height="100%",
        width="100%"
    )

def edit_form(item: Tuple[int, User]) -> rx.Component:
    return rx.card(
        rx.form(
            rx.vstack(
                rx.text("Логин:"),
                rx.input(id="login", default_value=item[1].login, required=True, size="3"),
                rx.text("Пароль:"),
                rx.input(id="password", size="3"),
                rx.text("Сотрудник:"),
                rx.select(
                    [k.fio for k in WorkerDAO.get_all()],

                    name="worker",
                    default_value=item[1].worker.fio,
                    placeholder="Выберите сотрудника",
                    required=True
                ),
                rx.heading("Назначенные роли:", size="3", width="100%"),
                rx.scroll_area(
                    rx.vstack(
                        rx.cond(
                            UserState.has_selected_roles,
                            rx.foreach(UserState.selected_roles, list_role_item),
                            rx.center(rx.text("Ничего не выбрано", color="gray"), width="100%", size="3")
                        ),

                        spacing="1",

                        width="100%",
                        height="100%",
                    ),


                    spacing="1",
                    width="100%",
                ),
                rx.dialog.root(
                    rx.dialog.trigger(
                        rx.button("Выбрать роли", size="2", width="12em",)
                    ),
                    rx.dialog.content(
                        roles.frontend.selector(
                            rx.hstack(
                                rx.dialog.close(rx.button("Отмена", variant="surface", size="3"),),
                                rx.spacer(),
                                rx.dialog.close(rx.button("Готово",
                                                        size="3",
                                                        on_click=[UserState.set_selected_roles(roles.backend.RoleSelectorState.get_id_selected_items)]),),

                                width="100%",
                            ),

                            height="50em",
                        ),

                        padding="0",

                        on_open_auto_focus=[roles.backend.RoleSelectorState.on_load(UserState.selected_roles)]
                    ),
                ),
                rx.heading("Персональные права:", size="3", width="100%"),
                rx.scroll_area(
                    rx.vstack(
                        rx.cond(
                            UserState.has_selected_actions,
                            rx.foreach(UserState.selected_actions, list_action_item),
                            rx.center(rx.text("Ничего не выбрано", color="gray"), width="100%", size="3")
                        ),

                        spacing="1",

                        width="100%",
                        height="100%",
                    ),


                    spacing="1",
                    width="100%",
                ),
                rx.dialog.root(
                    rx.dialog.trigger(
                        rx.button("Выбрать права", size="2", width="12em",)
                    ),
                    rx.dialog.content(
                        actions.frontend.index(
                            rx.hstack(
                                rx.dialog.close(rx.button("Отмена", variant="surface", size="3"),),
                                rx.spacer(),
                                rx.dialog.close(rx.button("Готово",
                                                        size="3",
                                                        on_click=[UserState.set_selected_actions(actions.backend.ActionsState.get_id_selected_items)]),),

                                width="100%",
                            ),

                            height="50em",
                        ),

                        padding="0",

                        on_open_auto_focus=[actions.backend.ActionsState.on_load(UserState.selected_actions)]
                    ),
                ),
                rx.hstack(
                    rx.button("Отмена", type="reset", color_scheme="red", on_click=rx.redirect(f"{routes.ADMIN_USERS_VIEW_ID}{item[1].login}")),
                    rx.button("Сохранить", color_scheme="green", type="submit"),

                    justify="end"
                ),

                align="stretch"
            ),

            on_submit=UserState.edit_one,
        ),

        height="100%",
        width="100%"
    )

def add_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading("Добавление пользователя", size="7", width="100%", margin_bottom="0.5em"),
        add_form(),

        value=UserState.Pages.ADD
    )

def edit_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading("Редактирование пользователя", size="7", width="100%", margin_bottom="0.5em"),
        edit_form(UserState.get_selected_item),

        value=UserState.Pages.EDIT
    )

def index() -> rx.Component:
    return rx.tabs.root(
        list_tab_content(),
        add_tab_content(),
        edit_tab_content(),
        item_preview_tab_content(),

        value=UserState.current_page,
 
        height="100%",
        width="100%"
    )