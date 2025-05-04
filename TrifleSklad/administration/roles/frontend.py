import reflex as rx

from TrifleSklad.administration.roles.backend import *

def item_preview(item: Role):
    return rx.vstack(
        rx.heading(item.title),
        rx.text(item.description),
        rx.button("Редактировать", on_click=[RoleState.set_select_item(item), RoleState.set_current_page(RoleState.Pages.EDIT)]),
        height="100%",
        width="100%"
    )

def table_row(item: Role) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(
            rx.dialog.root(
                rx.dialog.trigger(
                    rx.link(item.title)
                ),
                rx.dialog.content(
                    item_preview(item)
                ),
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
            rx.foreach(RoleState.items, table_row),
            height="100px",
            width="100%"
        ),
        variant="surface",
        height="300px",
        width="100%"
    )

def view_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            rx.heading("Роли пользователей", size="7", width="100%"),
            rx.cond(RoleState.has_items,
                table(),
                rx.text("Записей нет.")
            ),
        ),
        value=RoleState.Pages.VIEW,
    )

def add_form() -> rx.Component:
    return rx.card(
        rx.form(
            rx.vstack(
                rx.text("Название"),
                rx.input(id="title", required=True),
                rx.text("Описание"),
                rx.input(id="description"),
                rx.hstack(
                    rx.button("Отмена", type="reset", color_scheme="red", on_click=RoleState.set_current_page(RoleState.Pages.VIEW)),
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

def edit_form(role: Optional[Role]) -> rx.Component:
    return rx.card(
        rx.form(
            rx.vstack(
                rx.text("Название"),
                rx.input(id="title", required=True, default_value=role.title),
                rx.text("Описание"),
                rx.input(id="description", default_value=role.description),
                rx.hstack(
                    rx.button("Отмена", type="reset", color_scheme="red", on_click=RoleState.set_current_page(RoleState.Pages.VIEW)),
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
        rx.heading("Добавление роли", size="7", width="100%"),
        add_form(),
        value=RoleState.Pages.ADD
    )

def edit_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.heading("Редактирование роли", size="7", width="100%"),
        edit_form(RoleState.selected_item),
        value=RoleState.Pages.EDIT
    )

def index():
    return rx.tabs.root(
        view_tab_content(),
        add_tab_content(),
        edit_tab_content(),
        value=RoleState.get_current_page,
        default_value=RoleState.Pages.VIEW,
        height="100%",
        width="100%"
    )