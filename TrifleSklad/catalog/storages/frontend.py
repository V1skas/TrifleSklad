import reflex as rx

from TrifleSklad import routes
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum

from TrifleSklad.models import Storage

from TrifleSklad.catalog.storages.backend import ViewStorageState, AddStorageState, EditStorageState, ListStorageState, StorageState

def item_preview() -> rx.Component:
    return rx.vstack(
        rx.heading(ViewStorageState.title, size="7", width="100%"),
        rx.hstack(rx.text("Тип:"), rx.text(ViewStorageState.storage_type), width="100%"),
        rx.hstack(rx.text("Опис:"), rx.text(ViewStorageState.description, is_optional=True), width="100%"),
        rx.hstack(rx.text("Адреса:"), rx.text(ViewStorageState.address), width="100%"),
        rx.hstack(rx.text("Відповідальний:"), rx.text(ViewStorageState.responsible), width="100%"),
        rx.hstack(
            rx.text("За замовчуванням для рухів:"),
            rx.text(rx.cond(ViewStorageState.is_default, "Так", "Ні")),
            width="100%",
        ),

        spacing="3",
        height="100%",
        width="100%",
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
                        on_click=rx.redirect(routes.CATALOG_STORAGES)
                    ),
                    rx.heading("Об'єкти підприємства/Перегляд", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.STORAGE_DELETE),
                            rx.button(
                                "Видалити",
                                color_scheme="red",
                                variant="ghost",
                                size="3",
                                on_click=StorageState.delete_one(ViewStorageState.item.id)
                            ),                            
                        ),
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.STORAGE_EDIT),
                            rx.button(
                                "Редагувати",
                                variant="ghost",
                                size="3",
                                on_click=rx.redirect(f"{routes.CATALOG_STORAGES_EDIT_ID}{ViewStorageState.item.id}")
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

            width="100%"
        ),
        value=StorageState.Pages.VIEW
    )

def table_row(item: Storage) -> rx.Component:
    return rx.table.row(
        rx.table.row_header_cell(
            item.title,
            align="left"
        ),
        rx.table.cell(StorageState.get_titles_type_storages_dict_as_dict[item.type]),
        rx.table.cell(item.address),
        rx.table.cell(item.responsible.fio),
        on_click=rx.redirect(f"{routes.CATALOG_STORAGES_VIEW_ID}{item.id}"),
        cursor="pointer",
        _hover={"background_color": rx.color("accent", 3)},
    )

def table() -> rx.Component:
    return rx.table.root(
        rx.table.header(
            rx.table.row(
                rx.table.column_header_cell("Назва", align="left", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Тип", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Адреса", color=rx.color("accent", 2)),
                rx.table.column_header_cell("Відповідальний", color=rx.color("accent", 2)),
            ),

            background_color=rx.color("accent", 9),
        ),
        rx.table.body(
            rx.foreach(
                ListStorageState.filtered_items,
                table_row
            )
        ),

        variant="surface",
        width="100%"
    )

def table_tab_content() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            rx.box(
                rx.hstack(
                    rx.heading("Об'єкти підприємства", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.STORAGE_CREATE),
                            rx.button(
                                "Додати",
                                variant="ghost",
                                size="3",
                                on_click=rx.redirect(routes.CATALOG_STORAGES_ADD)
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
            rx.hstack(
                rx.input(
                    placeholder="Пошук за назвою",
                    value=ListStorageState.filter_title,
                    on_change=ListStorageState.on_change_filter_title,
                    flex="1",
                    min_width="0",
                ),
                rx.input(
                    placeholder="Пошук за адресою",
                    value=ListStorageState.filter_address,
                    on_change=ListStorageState.on_change_filter_address,
                    flex="1",
                    min_width="0",
                ),
                rx.select.root(
                    rx.select.trigger(placeholder="Усі типи"),
                    rx.select.content(
                        rx.select.item("Усі типи", value="all"),
                        rx.foreach(
                            ListStorageState.storage_type_options,
                            lambda o: rx.select.item(o[0], value=o[1]),
                        ),
                    ),
                    value=ListStorageState.filter_type,
                    on_change=ListStorageState.on_change_filter_type,
                    width="14em",
                    flex_shrink="0",
                ),
                spacing="3",
                width="100%",
                align="center",
            ),
            rx.cond(ListStorageState.has_items,
                table(),
                rx.text("Записів немає")
            ),

            width="100%",
            height="100%",
        ),

        value=StorageState.Pages.LIST
    )

def add_form() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text("*Назва", size="4", width="100%"),
            rx.input(
                name="title",
                required=True,
                value=AddStorageState.title,
                on_change=AddStorageState.on_change_title,
                width="100%"
            ),
            rx.text("*Тип", size="4", width="100%"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%"
                ),
                rx.select.content(
                    rx.foreach(
                        StorageState.get_titles_type_storages_dict,
                        lambda st_type: rx.select.item(st_type[1], value=st_type[0])
                    ),
                    width="100%",
                ),

                name="type",
                required=True,

                value=AddStorageState.storage_type_id,
                on_change=AddStorageState.on_change_type,
            ),
            rx.text("Опис", size="4", width="100%"),
            rx.text_area(
                name="description",
                is_optional=True,
                value=AddStorageState.description,
                on_change=AddStorageState.on_change_description,
                width="100%"
            ),
            rx.text("Адреса", size="4", width="100%"),
            rx.input(
                name="address",
                required=True,
                value=AddStorageState.address,
                on_change=AddStorageState.on_change_address,
                width="100%"
            ),
            rx.text("*Відповідальний", size="4", width="100%"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%"
                ),
                rx.select.content(
                    rx.foreach(
                        AddStorageState.list_workers,
                        lambda worker: rx.select.item(worker[1], value=worker[0])
                    ),
                    width="100%",
                ),

                name="id_worker",
                required=True,

                value=AddStorageState.id_responsible,
                on_change=AddStorageState.on_change_responsible,
            ),
            rx.hstack(
                rx.switch(checked=AddStorageState.is_default, on_change=AddStorageState.on_change_is_default),
                rx.text("За замовчуванням для рухів (на цей тип)"),
                align="center", spacing="2",
            ),

            spacing="3",
            width="100%"
        ),

        width="100%",
        height="100%",
    )

def edit_form() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text("*Назва", size="4", width="100%"),
            rx.input(
                name="title",
                required=True,
                value=EditStorageState.title,
                on_change=EditStorageState.on_change_title,
                width="100%"
            ),
            rx.text("*Тип", size="4", width="100%"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%"
                ),
                rx.select.content(
                    rx.foreach(
                        StorageState.get_titles_type_storages_dict,
                        lambda st_type: rx.select.item(st_type[1], value=st_type[0])
                    ),
                    width="100%",
                ),

                name="type",
                required=True,

                value=EditStorageState.storage_type_id,
                on_change=EditStorageState.on_change_type,
            ),
            rx.text("Опис", size="4", width="100%"),
            rx.text_area(
                name="description",
                is_optional=True,
                value=EditStorageState.description,
                on_change=EditStorageState.on_change_description,
                width="100%"
            ),
            rx.text("Адреса", size="4", width="100%"),
            rx.input(
                name="address",
                required=True,
                value=EditStorageState.address,
                on_change=EditStorageState.on_change_address,
                width="100%"
            ),
            rx.text("*Відповідальний", size="4", width="100%"),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Оберіть зі списку",
                    width="100%"
                ),
                rx.select.content(
                    rx.foreach(
                        EditStorageState.list_workers,
                        lambda worker: rx.select.item(worker[1], value=worker[0])
                    ),
                    width="100%",
                ),

                name="id_worker",
                required=True,

                value=EditStorageState.id_responsible,
                on_change=EditStorageState.on_change_responsible,
            ),
            rx.hstack(
                rx.switch(checked=EditStorageState.is_default, on_change=EditStorageState.on_change_is_default),
                rx.text("За замовчуванням для рухів (на цей тип)"),
                align="center", spacing="2",
            ),

            spacing="3",
            width="100%"
        ),

        width="100%",
        height="100%",
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
                        on_click=rx.redirect(routes.CATALOG_STORAGES)
                    ),
                    rx.heading("Об'єкти підприємства/Додавання", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.STORAGE_CREATE),
                            rx.button(
                                "Зберегти",
                                variant="ghost",
                                size="3",
                                on_click=AddStorageState.add_one
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

            width="100%"
        ),

        value=StorageState.Pages.ADD
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
                        on_click=rx.redirect(routes.CATALOG_STORAGES)
                    ),
                    rx.heading("Об'єкти підприємства/Редагування", size="7", color=rx.color("accent", 9)),
                    rx.hstack(
                        rx.cond(AppState.get_user_actions.contains(ActionEnum.STORAGE_EDIT),
                            rx.button(
                                "Зберегти",
                                variant="ghost",
                                size="3",
                                on_click=EditStorageState.edit_one
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

            width="100%"
        ),

        value=StorageState.Pages.EDIT
    )

def index() -> rx.Component:
    return rx.tabs.root(
        rx.cond(AppState.get_user_actions.contains(ActionEnum.STORAGE_LIST),
            table_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.STORAGE_CREATE),
            add_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.STORAGE_EDIT),
            edit_tab_content()),
        rx.cond(AppState.get_user_actions.contains(ActionEnum.STORAGE_VIEW),
            item_preview_tab_content()),

        value=StorageState.current_page,

        orientation="horizontal",
        width="100%"
    )