import reflex as rx

from components import decor
from TrifleSklad import authorithation, administration, routes

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
                navbar_link("Администрирование", routes.ADMIN_WELCOME),
                navbar_link("Item 2", "#"),
                navbar_link("Item 3", "#"),

                align_items="center",
                height="100%",
                spacing="5",
            ),
            rx.menu.root(
                rx.menu.trigger(
                    rx.icon_button(
                        rx.icon("user"),
                        
                        size="2",
                        radius="full",
                    )
                ),
                rx.menu.content(
                    rx.menu.separator(),
                    rx.menu.item("Выйти"),
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

def auth_page() -> rx.Component:
    return authorithation.frontend.index()

def welcome_page() -> rx.Component:
    return rx.vstack(
        navbar(),
        rx.vstack(
            rx.heading("Приветствую в Trifle Склад!", size="9", color=rx.color("accent", 9)),
            rx.text(
                "Для начала работы, выберите нужный раздел в шапке страницы.",

                size="5",
            ),

            spacing="5",
            justify="center",
            align="center",

            min_height="75vh",
            width="100%",
        ),

        width="100%",
    )

def administration_page() -> rx.Component:
    return rx.vstack(
        navbar(),
        administration.frontend.index(),

        width="100%",
    )