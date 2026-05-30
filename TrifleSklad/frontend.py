import reflex as rx

from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.state import AppState

from components import decor
from TrifleSklad import authorithation, administration, routes, catalog, movement

from TrifleSklad.authorithation.frontend import require_login

def navbar_link(text: str, url: str) -> rx.Component:
    return rx.link(
        rx.button(
            text,

            variant="ghost",
            color=rx.color("accent", 11),

            border_radius="0",

            _hover={
                "color": rx.color("accent", 12),
                "transform": "translateY(-1px)",
                "transition": "all 0.1s ease-in-out",
                "border_bottom": f"4px solid {rx.color('accent', 9)}",
            },

            height="100%",
            size="4",
        ),

        href=url,

        height="70%",
    )

def navbar() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.link(
                rx.hstack(
                    decor.logo(),

                    align_items="center",
                    padding="1em",
                    spacing="1",
                ),
                href=routes.WELCOME,
            ),
            rx.hstack(
                rx.cond(
                    AppState.get_user_actions.contains(ActionEnum.WORKERS_LIST) | AppState.get_user_actions.contains(ActionEnum.ROLES_LIST) | AppState.get_user_actions.contains(ActionEnum.USERS_LIST),
                    navbar_link("Адміністрування", routes.ADMIN),
                ),
                rx.cond(
                    AppState.get_user_actions.contains(ActionEnum.CATEGORIES_LIST) | AppState.get_user_actions.contains(ActionEnum.PRODUCTS_LIST) | AppState.get_user_actions.contains(ActionEnum.STORAGE_LIST) | AppState.get_user_actions.contains(ActionEnum.OWNERS_LIST) | AppState.get_user_actions.contains(ActionEnum.SUPPLIERS_LIST) | AppState.get_user_actions.contains(ActionEnum.PAYMENT_TYPE_LIST) | AppState.get_user_actions.contains(ActionEnum.NDS_RATES_LIST),
                    navbar_link("Каталог", routes.CATALOG),                
                ),
                #navbar_link("Рух ТМЦ", routes.MOVEMENT),

                align_items="center",
                height="100%",
                spacing="5",
            ),
            rx.menu.root(
                rx.menu.trigger(
                    rx.button(
                        rx.icon("user"),
                        rx.text(AppState.fio, size="3"),

                        variant="ghost",
                        color=rx.color("accent", 11),

                        border_radius="0",

                        _hover={
                            "color": rx.color("accent", 12),
                            "transform": "translateY(-1px)",
                            "transition": "all 0.1s ease-in-out",
                            "border_bottom": f"4px solid {rx.color('accent', 9)}",
                        },

                        size="4",
                        height="75%",
                    ),
                ),
                rx.menu.content(
                    rx.menu.separator(),
                    rx.menu.item("Вийти", on_click=AppState.logout),
                ),

                justify="end",
                padding="1em",
            ),

            justify="between",
            align_items="center",
            height="100%",
        ),

        border_bottom=f"1px solid {rx.color('accent', 9)}",

        padding_right="1em",

        width="100%",
        height="75px",
    )

def sidebar(*buttons):
    return rx.box(
        rx.vstack(
            rx.heading("Меню", size="6", color=rx.color("accent", 3), bg=rx.color("accent", 9), height="40px", text_align="center", line_height="40px"),
            *buttons,

            spacing="0",
            align_items="stretch",
            width="100%",
        ),

        border_radius="1em 1em 5px 5px",
        background_color=rx.color("gray", 4),
        overflow="hidden",

        padding="0",

        size="4",

        width="23em",
    )

def workspace(*tabs, **prop):
    return rx.tabs.root(
        *tabs,

        width="100%",
        height="100%",

        **prop
    )

def auth_page() -> rx.Component:
    return authorithation.frontend.index()

@require_login
def welcome_page() -> rx.Component:
    return rx.vstack(
        navbar(),
        rx.vstack(
            rx.heading("Ласкаво просимо до Trifle Склад!", size="9", color=rx.color("accent", 9)),
            rx.text(
                "Для початку роботи, оберіть потрібний розділ у шапці сторінки.",

                size="5",
            ),

            spacing="5",
            justify="center",
            align="center",

            min_height="75vh",
            width="100%",
        ),

        width="100vw",
    )

@require_login
def administration_page() -> rx.Component:
    return rx.vstack(
        navbar(),
        administration.frontend.index(),

        width="100vw",
    )

@require_login
def catalog_page() -> rx.Component:
    return rx.vstack(
        navbar(),
        catalog.frontend.index(),

        width="100vw",
    )

@require_login
def movement_page() -> rx.Component:
    return rx.vstack(
        navbar(),
        movement.frontend.index(),

        width="100vw",
    )
