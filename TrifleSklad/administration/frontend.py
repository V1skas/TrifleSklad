from turtle import width
import reflex as rx

from TrifleSklad import routes
from TrifleSklad.administration.backend import AdministrationState

def roles():
    return rx.vstack(
        rx.heading("Роли", size="7"),
    )

def users():
    return rx.text("Users")

def sidebar_link(text: str, url: str):
    return rx.link(
        rx.button(
            text,

            radius="none",
            variant="soft",
            color=rx.color("accent", 11),

            border_radius="0",

            _hover={
                "color": rx.color("accent", 12),
                "transform": "translateX(5px)",
                "transition": "all 0.1s ease-in-out",
                "border_left": f"4px solid {rx.color('accent', 9)}",
            },

            size="3",

            width="100%",
        ),

        href=url,
    )

def sidebar():
    return rx.card(
        rx.vstack(
            rx.heading("Меню", size="6", color=rx.color("accent", 3), bg=rx.color("accent", 9), height="50px", text_align="center", line_height="50px"),
            sidebar_link("Роли", routes.ADMIN),
            sidebar_link("Пользователи", routes.ADMIN),
            rx.box(
                background_color=rx.color("accent", 9),
                height="1em",
            ),

            spacing="0",
            align_items="stretch",
            width="100%",
        ),
        
        padding="0",
        margin_left="1em",

        size="4",

        width="23em",
    )

def workspace():
    return rx.tabs.root(
        rx.tabs.content(
            roles(),

            value=AdministrationState.Tabs.ROLES,
        ),
        rx.tabs.content(
            users(),

            value=AdministrationState.Tabs.USERS,
        ),

        value=AdministrationState.Tabs.ROLES,
        width="100%",
        height="100%",
    )

def index():
    return rx.hstack(
        sidebar(),
        workspace(),

        width="100%",
        height="100%",
    )