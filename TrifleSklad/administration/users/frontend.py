import reflex as rx

from typing import Tuple

from TrifleSklad import routes
from TrifleSklad.administration.users.backend import ViewUserState, AddUserState, EditUserState, ListUserState, UserState
from TrifleSklad.models import User, Role, Action, Worker
from TrifleSklad.dao import WorkerDAO

import TrifleSklad.administration.roles as roles
import TrifleSklad.administration.actions as actions

from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum

def list_role_item(item: Role) -> rx.Component:
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

def list_action_item(item: Action) -> rx.Component:
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

def item_preview() -> rx.Component:
    return rx.vstack(
        rx.heading(ViewUserState.item.login, size="7", width="100%"),
        rx.text(ViewUserState.item.worker.fio, width="100%"),
        rx.heading("Призначені ролі:", size="3", width="100%"),
        rx.scroll_area(
            rx.vstack(
                rx.cond(
                    ViewUserState.has_roles,
                    rx.foreach(ViewUserState.item.roles, list_role_item),
                    rx.center(rx.text("Нічого не обрано"), width="100%", size="3")
                ),

                spacing="1",

                width="100%",
                height="100%",
            ),

            spacing="1",
            width="100%",
        ),
        rx.heading("Персональні дозволи:", size="3", width="100%"),
        rx.scroll_area(
            rx.vstack(
                rx.cond(
                    ViewUserState.has_actions,
                    rx.foreach(ViewUserState.item.actions, list_action_item),
                    rx.center(rx.text("Нічого не обрано"), width="100%", size="3")
                ),

                spacing="1",

                width="100%",
                height="100%",
            ),


            spacing="1",
            width="100%",
        ),

        spacing="3",

        height="100%",
        width="100%"
    )

def item_preview_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            rx.box(
                rx.hstack(
                    rx.button(
                        "Повернутись",
                        variant="ghost",
                        size="3",
                        on_click=rx.redirect(routes.ADMIN_USERS)
                    ),
                    rx.heading("Користувачі/Перегляд", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.has_permission(ActionEnum.USERS_DELETE),
                            rx.button(
                                "Видалити",
                                color_scheme="red",
                                variant="ghost",
                                size="3",
                                on_click=UserState.delete_one(ViewUserState.item.login)
                            ),                            
                        ),
                        rx.cond(AppState.has_permission(ActionEnum.USERS_EDIT),
                            rx.button(
                                "Редагувати",
                                variant="ghost",
                                size="3",
                                on_click=rx.redirect(f"{routes.ADMIN_USERS_EDIT_ID}{ViewUserState.item.login}")
                            ),                          
                        ),

                        spacing="6",
                    ),

                    align="center",
                    justify="between",
                    padding="0.5em",
                    width="100%"
                ),

                width="100%",

                style={
                    "border_bottom": f"1px solid {rx.color('accent', 9)}",
                }
            ),
            item_preview(),

            width="100%",
        ),

        value=UserState.Pages.VIEW
    )

def table_row(item: User) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(
            rx.link(
                item.login,
                href=f"{routes.ADMIN_USERS_VIEW_ID}{item.login}",
            ),

            align="left"
        ),
        rx.table.cell(
            item.worker.fio,
            align="left"
        ),
        rx.table.cell(
            item.worker.position,
            align="left"
        ),
    )

def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Логін", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Співробітник", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Посада", color=rx.color("accent", 2)),
            ),

            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(ListUserState.items, table_row),

            width="100%"
        ),

        variant="surface",
        height="100%",
        width="100%"
    )

def list_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            rx.box(
                rx.hstack(
                    rx.heading("Користувачі", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.has_permission(ActionEnum.USERS_CREATE),
                            rx.button(
                                "Додати",
                                variant="ghost",
                                size="3",
                                on_click=rx.redirect(routes.ADMIN_USERS_ADD)
                            ),                          
                        ),

                        spacing="6",
                    ),

                    align="center",
                    justify="between",
                    padding="0.5em",
                    width="100%"
                ),

                width="100%",

                style={
                    "border_bottom": f"1px solid {rx.color('accent', 9)}",
                }
            ),
            rx.cond(ListUserState.has_items,
                table(),
                rx.text("Записів немає")
            ),

            width="100%",
            height="100%",
        ),

        value=UserState.Pages.LIST,
    )

def add_form() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text("*Логін:"),
            rx.input(id="login", required=True, size="3", is_disabled=True, value=AddUserState.item.login, on_change=AddUserState.on_change_login),
            rx.text("*Пароль:"),
            rx.input(id="password", size="3", required=True, value=AddUserState.item.password_hash, on_change=AddUserState.on_change_password),
            rx.text("*Співробітник:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%"
                ),
                rx.select.content(
                    rx.foreach(
                        AddUserState.list_workers,
                        lambda worker: rx.select.item(worker[0], value=worker[1])
                    ),
                    width="100%",
                ),

                name="id_worker",
                required=True,

                value=AddUserState.id_worker,
                on_change=AddUserState.on_change_worker,
            ),
            rx.heading("Надані ролі:", size="3", width="100%"),
            rx.scroll_area(
                rx.vstack(
                    rx.cond(
                        AddUserState.has_roles,
                        rx.foreach(AddUserState.item.roles, list_role_item),
                        rx.center(rx.text("Нічого не обрано", color="gray"), width="100%", size="3")
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
                    rx.button("Надані ролі", size="2", width="12em",)
                ),
                rx.dialog.content(
                    roles.frontend.selector(
                        rx.hstack(
                            rx.dialog.close(rx.button("Скасувати", variant="surface", size="3"),),
                            rx.spacer(),
                            rx.dialog.close(rx.button("Зберегти",
                                                    size="3",
                                                    on_click=AddUserState.on_change_roles)),

                            width="100%",
                        ),

                        height="50em",
                    ),

                    padding="0",

                    on_open_auto_focus=AddUserState.on_open_roles
                ),
            ),
            rx.heading("Персональні дозволи:", size="3", width="100%"),
            rx.scroll_area(
                rx.vstack(
                    rx.cond(
                        AddUserState.has_actions,
                        rx.foreach(AddUserState.item.actions, list_action_item),
                        rx.center(rx.text("Нічого не обрано", color="gray"), width="100%", size="3")
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
                    rx.button("Обрати дозволи", size="2", width="12em",)
                ),
                rx.dialog.content(
                    actions.frontend.index(
                        rx.hstack(
                            rx.dialog.close(rx.button("Скасуквати", variant="surface", size="3"),),
                            rx.spacer(),
                            rx.dialog.close(rx.button("Зберегти",
                                                    size="3",
                                                    on_click=AddUserState.on_change_actions)),

                            width="100%",
                        ),

                        height="50em",
                    ),

                    padding="0",

                    on_open_auto_focus=AddUserState.on_open_actions
                ),
            ),

            align="stretch"
        ),

        height="100%",
        width="100%",
    )

def edit_form() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text("Логін:"),
            rx.input(id="login", required=True, size="3", value=EditUserState.item.login),
            rx.text("Пароль:"),
            rx.input(id="password", size="3", required=True, value=EditUserState.password, on_change=EditUserState.on_change_password),
            rx.text("*Співробітник:"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%"
                ),
                rx.select.content(
                    rx.foreach(
                        EditUserState.list_workers,
                        lambda worker: rx.select.item(worker[0], value=worker[1])
                    ),
                    width="100%",
                ),

                name="id_worker",
                required=True,

                value=EditUserState.id_worker,
                on_change=EditUserState.on_change_worker,
            ),
            rx.heading("Призначені ролі:", size="3", width="100%"),
            rx.scroll_area(
                rx.vstack(
                    rx.cond(
                        EditUserState.has_roles,
                        rx.foreach(EditUserState.item.roles, list_role_item),
                        rx.center(rx.text("Нічого не обрано", color="gray"), width="100%", size="3")
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
                    rx.button("Обрати ролі", size="2", width="12em",)
                ),
                rx.dialog.content(
                    roles.frontend.selector(
                        rx.hstack(
                            rx.dialog.close(rx.button("Скасувати", variant="surface", size="3"),),
                            rx.spacer(),
                            rx.dialog.close(rx.button("Зберегти",
                                                    size="3",
                                                    on_click=EditUserState.on_change_roles),),

                            width="100%",
                        ),

                        height="50em",
                    ),

                    padding="0",

                    on_open_auto_focus=EditUserState.on_open_roles
                ),
            ),
            rx.heading("Персональні дозволи:", size="3", width="100%"),
            rx.scroll_area(
                rx.vstack(
                    rx.cond(
                        EditUserState.has_actions,
                        rx.foreach(EditUserState.item.actions, list_action_item),
                        rx.center(rx.text("Нічого не обрано", color="gray"), width="100%", size="3")
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
                    rx.button("Обрати дозволи", size="2", width="12em",)
                ),
                rx.dialog.content(
                    actions.frontend.index(
                        rx.hstack(
                            rx.dialog.close(rx.button("Скасувати", variant="surface", size="3"),),
                            rx.spacer(),
                            rx.dialog.close(rx.button("Зберегти",
                                                    size="3",
                                                    on_click=EditUserState.on_change_actions),),

                            width="100%",
                        ),

                        height="50em",
                    ),

                    padding="0",

                    on_open_auto_focus=EditUserState.on_open_actions
                ),
            ),

            align="stretch"
        ),

        height="100%",
        width="100%"
    )

def add_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            rx.box(
                rx.hstack(
                    rx.button(
                        "Скасувати",
                        variant="ghost",
                        size="3",
                        on_click=rx.redirect(routes.ADMIN_USERS)
                    ),
                    rx.heading("Користувачі/Додавання", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.has_permission(ActionEnum.USERS_CREATE),
                            rx.button(
                                "Зберегти",
                                variant="ghost",
                                size="3",
                                on_click=AddUserState.add_one
                            ),                          
                        ),

                        spacing="6",
                    ),

                    align="center",
                    justify="between",
                    padding="0.5em",
                    width="100%"
                ),

                width="100%",

                style={
                    "border_bottom": f"1px solid {rx.color('accent', 9)}",
                }
            ),
            add_form(),
        ),

        value=UserState.Pages.ADD
    )

def edit_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            rx.box(
                rx.hstack(
                    rx.button(
                        "Скасувати",
                        variant="ghost",
                        size="3",
                        on_click=rx.redirect(routes.ADMIN_USERS)
                    ),
                    rx.heading("Користувачі/Редагування", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.has_permission(ActionEnum.USERS_EDIT),
                            rx.button(
                                "Зберегти",
                                variant="ghost",
                                size="3",
                                on_click=EditUserState.edit_one
                            ),                          
                        ),

                        spacing="6",
                    ),

                    align="center",
                    justify="between",
                    padding="0.5em",
                    width="100%"
                ),

                width="100%",

                style={
                    "border_bottom": f"1px solid {rx.color('accent', 9)}",
                }
            ),
            edit_form(),
        ),

        value=UserState.Pages.EDIT
    )

def index() -> rx.Component:
    return rx.tabs.root(
        rx.cond(AppState.has_permission(ActionEnum.USERS_LIST), list_tab_content()),
        rx.cond(AppState.has_permission(ActionEnum.USERS_LIST), add_tab_content()),
        rx.cond(AppState.has_permission(ActionEnum.USERS_LIST), edit_tab_content()),
        rx.cond(AppState.has_permission(ActionEnum.USERS_LIST), item_preview_tab_content()),

        value=UserState.current_page,
 
        height="100%",
        width="100%"
    )