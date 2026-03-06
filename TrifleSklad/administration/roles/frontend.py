import reflex as rx

from typing import List, Tuple, Optional

from TrifleSklad import routes
from TrifleSklad.administration.roles.backend import RoleState, ListRoleState, EditRoleState, AddRoleState, ViewRoleState, RoleSelectorState
import TrifleSklad.administration.actions as actions

from TrifleSklad.models import Role, Action
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum

def item_preview() -> rx.Component:
    return rx.vstack(
        rx.heading(ViewRoleState.item.title, size="7", width="100%"),
        rx.text(ViewRoleState.item.description, width="100%"),
        rx.heading("Права", size="3", width="100%"),
        rx.scroll_area(
            rx.vstack(
                rx.cond(
                    ViewRoleState.has_actions,
                    rx.foreach(ViewRoleState.item.actions, list_action_item),
                    rx.center(rx.text("Нічого не обрано"), width="100%", size="3")
                ),

                spacing="1",

                width="100%",
                height="100%",
            ),


            spacing="1",
            width="100%",
        ),

        justify="end",

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
                        on_click=rx.redirect(routes.ADMIN_ROLES)
                    ),
                    rx.heading("Ролі/Перегляд", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.has_permission(ActionEnum.ROLES_DELETE),
                            rx.button(
                                "Видалити",
                                color_scheme="red",
                                variant="ghost",
                                size="3",
                                on_click=RoleState.delete_one(ViewRoleState.item.id)
                            ),                            
                        ),
                        rx.cond(AppState.has_permission(ActionEnum.ROLES_EDIT),
                            rx.button(
                                "Редагувати",
                                variant="ghost",
                                size="3",
                                on_click=rx.redirect(f"{routes.ADMIN_ROLES_EDIT_ID}{ViewRoleState.item.id}")
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

        value=RoleState.Pages.VIEW
    )

def table_row(item: Role) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(
            rx.link(
                item.title,
                href=f"{routes.ADMIN_ROLES_VIEW_ID}{item.id}",
            ),

            align="left"
        ),
    )

def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Назва", color=rx.color("accent", 2)),
            ),

            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(ListRoleState.items, table_row),
            width="100%"
        ),

        variant="surface",
        width="100%"
    )

def list_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            rx.box(
                rx.hstack(
                    rx.heading("Ролі", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.has_permission(ActionEnum.ROLES_CREATE),
                            rx.button(
                                "Додати",
                                variant="ghost",
                                size="3",
                                on_click=rx.redirect(routes.ADMIN_ROLES_ADD)
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
            rx.cond(ListRoleState.has_items,
                table(),
                rx.text("Записів немає")
            ),

            width="100%",
            height="100%",
        ),

        value=RoleState.Pages.LIST,
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

def add_form() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text("*Назва:"),
            rx.input(id="title", required=True, size="3", value=AddRoleState.item.title, on_change=AddRoleState.change_title),
            rx.text("Опис:"),
            rx.text_area(id="description", size="3", value=AddRoleState.item.description, on_change=AddRoleState.change_description),
            rx.text("*Права:"),
            rx.scroll_area(
                rx.vstack(
                    rx.cond(
                        AddRoleState.has_selected_actions,
                        rx.foreach(AddRoleState.item.actions, list_action_item),
                        rx.center(rx.text("Нічого не обрано"), width="100%", size="3")
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
                    rx.button("Вибрати права", size="2", width="12em",)
                ),
                rx.dialog.content(
                    actions.frontend.index(
                        rx.hstack(
                            rx.dialog.close(rx.button("Скасувати", variant="surface", size="3"),),
                            rx.spacer(),
                            rx.dialog.close(rx.button("Готово",
                                                    size="3",
                                                    on_click=AddRoleState.change_actions),),

                            width="100%",
                        ),

                        height="50em",
                    ),

                    padding="0",

                    on_open_auto_focus=AddRoleState.open_actions
                ),
            ),

            align="stretch"
        ),

        height="100%",
        width="100%"
    )

def edit_form() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.text("*Назва:"),
            rx.input(id="title", required=True, size="3", value=EditRoleState.item.title, on_change=EditRoleState.change_title),
            rx.text("Опис:"),
            rx.text_area(id="description", size="3", value=EditRoleState.item.description, on_change=EditRoleState.change_description),
            rx.text("*Права:"),
            rx.scroll_area(
                rx.vstack(
                    rx.cond(
                        EditRoleState.has_selected_actions,
                        rx.foreach(EditRoleState.item.actions, list_action_item),
                        rx.center(rx.text("Нічого не обрано"), width="100%", size="3")
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
                    rx.button("Вибрати права", size="2", width="12em",)
                ),
                rx.dialog.content(
                    actions.frontend.index(
                        rx.hstack(
                            rx.dialog.close(rx.button("Скасувати", variant="surface", size="3"),),
                            rx.spacer(),
                            rx.dialog.close(rx.button("Готово",
                                                    size="3",
                                                    on_click=[EditRoleState.change_actions]),),

                            width="100%",
                        ),

                        height="50em",
                    ),

                    padding="0",

                    on_open_auto_focus=EditRoleState.open_actions
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
                        on_click=rx.redirect(routes.ADMIN_ROLES)
                    ),
                    rx.heading("Ролі/Додавання", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.has_permission(ActionEnum.ROLES_CREATE),
                            rx.button(
                                "Зберегти",
                                variant="ghost",
                                size="3",
                                on_click=AddRoleState.add_one
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

            width="100%",
        ),

        value=RoleState.Pages.ADD
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
                        on_click=rx.redirect(routes.ADMIN_ROLES)
                    ),
                    rx.heading("Ролі/Редагування", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.has_permission(ActionEnum.ROLES_EDIT),
                            rx.button(
                                "Зберегти",
                                variant="ghost",
                                size="3",
                                on_click=EditRoleState.edit_one
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

            width="100%",
        ),

        value=RoleState.Pages.EDIT
    )

def index() -> rx.Component:
    return rx.tabs.root(
        rx.cond(AppState.has_permission(ActionEnum.ROLES_LIST),
            list_tab_content()),
        rx.cond(AppState.has_permission(ActionEnum.ROLES_CREATE),
            add_tab_content()),
        rx.cond(AppState.has_permission(ActionEnum.ROLES_EDIT),
            edit_tab_content()),
        rx.cond(AppState.has_permission(ActionEnum.ROLES_VIEW),
            item_preview_tab_content()),

        value=RoleState.current_page,

        height="100%",
        width="100%"
    )

def selector_item(item: Tuple[int, Role]) -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.heading(item[1].title, size="3", user_select="none"),
            rx.text(item[1].description, size="1", user_select="none"),

            spacing="0",
            width="100%",
        ),

        background_color=rx.color("accent", 2),
        border_color=rx.color("accent", 4),
        border_width="1px",

        padding="calc(0.7em + 2px)",

        width="100%",

        _hover={
            "background_color": rx.color("accent", 6),
            "border_color": rx.color("accent", 8),
            "border_width": "1px",
            "padding": "calc(0.7em + 2px)",
        },
        _active={
            "background_color": rx.color("accent", 8),
            "border_color": rx.color("accent", 8),
            "border_width": "3px",
            "padding": "0.7em",
        },

        on_click=RoleSelectorState.select_item(item[0]),
    )

def selector_item_selected(item: Tuple[int, Role]) -> rx.Component:
    return rx.card(
        rx.hstack(
            rx.icon("circle-check-big", color=rx.color("accent", 9), height="100%"),

            rx.vstack(
                rx.heading(item[1].title, color=rx.color("accent", 9), size="3", user_select="none"),
                rx.text(item[1].description, size="1", user_select="none"),

                flex="1",
                spacing="0",
                height="100%",
            ),

            align="center",
            width="100%",
        ),

        background_color=rx.color("accent", 4),
        border_color=rx.color("accent", 9),
        border_width="2px",

        padding="calc(0.7em + 1px)",

        width="100%",

        _hover={
            "background_color": rx.color("accent", 6),
            "border_color": rx.color("accent", 8),
            "border_width": "2px",
            "padding": "calc(0.7em + 1px)",
        },
        _active={
            "background_color": rx.color("accent", 8),
            "border_color": rx.color("accent", 8),
            "border_width": "3px",
            "padding": "0.7em",
        },

        on_click=RoleSelectorState.select_item(item[0]),
    )

def selector_list() -> rx.Component:
    return rx.scroll_area(
        rx.vstack(
            rx.foreach(RoleSelectorState.get_selected_items, selector_item_selected),
            rx.foreach(RoleSelectorState.get_unselected_items, selector_item),

            spacing="1",
        ),

        width="100%",
        height="100%",
    )

def selector(*child, **prop) -> rx.Component:
    return rx.vstack(
        rx.heading("Выбор ролей:", size="8", color=rx.color("accent", 2), background_color=rx.color("accent", 9), width="100%", padding="0.5em"),
        rx.vstack(
            rx.input(
                rx.input.slot(rx.icon("search")),

                placeholder="Поиск",
                value=RoleSelectorState.filter,

                width="100%",
                size="3",

                on_change=RoleSelectorState.set_filter,
            ),
            rx.card(
                selector_list(),

                width="100%",
                height="100%",
            ),
            *child,

            padding="1em",
            width="100%",
            height="100%",
        ),

        **prop,
    )
