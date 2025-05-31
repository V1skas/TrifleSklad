import reflex as rx

from TrifleSklad import routes
from TrifleSklad.administration.roles.backend import *
import TrifleSklad.administration.actions as actions

from TrifleSklad.models import Role, Action

def item_preview(item: Tuple[int, Role]) -> rx.Component:
    return rx.vstack(
        rx.heading(item[1].title, size="7", width="100%"),
        rx.text(item[1].description, width="100%"),
        rx.heading("Права", size="3", width="100%"),
        rx.scroll_area(
            rx.vstack(
                rx.cond(
                    RoleState.has_selected_actions,
                    rx.foreach(RoleState.selected_actions, list_action_item),
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

                on_click=rx.redirect(f"{routes.ADMIN_ROLES_EDIT_ID}{item[1].id}")
            ),
            rx.spacer(),
            rx.button(
                "Удалить",
                color_scheme="red",

                on_click=RoleState.delete_one
            ),

            width="100%",
        ),

        justify="end",

        spacing="3",

        height="100%",
        width="100%"
    )

def item_preview_tab_content() -> rx.Component:
    return rx.tabs.content(
        item_preview(RoleState.get_selected_item),

        value=RoleState.Pages.VIEW
    )

def table_row(item: Tuple[int, Role]) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(
            rx.link(
                item[1].title,
                href=f"{routes.ADMIN_ROLES_VIEW_ID}{item[1].id}",
            ),

            align="left"
        ),
    )

def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Название", color=rx.color("accent", 2)),
            ),

            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(RoleState.get_items, table_row),

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
                rx.heading("Роли", size="6"),
                rx.spacer(),
                rx.button(
                    "Добавить",
                    on_click=rx.redirect(routes.CATALOG_PRODUCTS_ADD)
                ),

                width="100%"
            ),
            rx.cond(RoleState.has_items,
                table(),
                rx.text("Записей нет.")
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
        rx.form(
            rx.vstack(
                rx.text("Название:"),
                rx.input(id="title", required=True, size="3"),
                rx.text("Описание:"),
                rx.text_area(id="description", size="3"),
                rx.text("Права:"),
                rx.scroll_area(
                    rx.vstack(
                        rx.cond(
                            RoleState.has_selected_actions,
                            rx.foreach(RoleState.selected_actions, list_action_item),
                            rx.center(rx.text("Ничего не выбрано"), width="100%", size="3")
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
                                                        on_click=[RoleState.set_selected_actions(ActionsState.get_id_selected_items)]),),

                                width="100%",
                            ),

                            height="50em",
                        ),

                        padding="0",

                        on_open_auto_focus=[actions.backend.ActionsState.on_load(RoleState.selected_actions)]
                    ),
                ),
                rx.hstack(
                    rx.button("Отмена", type="reset", color_scheme="red", on_click=rx.redirect(routes.ADMIN_ROLES)),
                    rx.button("Сохранить", color_scheme="green", type="submit"),

                    justify="end"
                ),

                align="stretch"
            ),

            on_submit=RoleState.add_one,
        ),

        height="100%",
        width="100%"
    )

def edit_form(item: Tuple[int, Role]) -> rx.Component:
    return rx.card(
        rx.form(
            rx.vstack(
                rx.text("Название:"),
                rx.input(id="title", required=True, default_value=item[1].title),
                rx.text("Описание:"),
                rx.text_area(id="description", default_value=item[1].description, is_optional=True),
                rx.text("Права:"),
                rx.scroll_area(
                    rx.vstack(
                        rx.cond(
                            RoleState.has_selected_actions,
                            rx.foreach(RoleState.selected_actions, list_action_item),
                            rx.center(rx.text("Ничего не выбрано"), width="100%", size="3")
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
                                                        on_click=[RoleState.set_selected_actions(ActionsState.get_id_selected_items)]),),

                                width="100%",
                            ),

                            height="50em",
                        ),

                        padding="0",

                        on_open_auto_focus=[actions.backend.ActionsState.on_load(RoleState.selected_actions)]
                    ),
                ),
                rx.hstack(
                    rx.button("Отмена", type="reset", color_scheme="red",
                              on_click=rx.redirect(f"{routes.ADMIN_ROLES_VIEW_ID}{item[1].id}")),
                    rx.button("Сохранить", color_scheme="green", type="submit"),

                    justify="end"
                ),

                align="stretch"
            ),

            on_submit=RoleState.edit_one,
        ),

        height="100%",
        width="100%"
    )

def add_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading("Добавление роли", size="7", width="100%", margin_bottom="0.5em"),
        add_form(),

        value=RoleState.Pages.ADD
    )

def edit_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading("Редактирование роли", size="7", width="100%", margin_bottom="0.5em"),
        edit_form(RoleState.get_selected_item),

        value=RoleState.Pages.EDIT
    )

def index() -> rx.Component:
    return rx.tabs.root(
        list_tab_content(),
        add_tab_content(),
        edit_tab_content(),
        item_preview_tab_content(),

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
