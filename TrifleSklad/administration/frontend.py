from turtle import width
import reflex as rx

from TrifleSklad import routes
from TrifleSklad.administration.backend import AdministrationState

import TrifleSklad.administration.actions as actions
import TrifleSklad.administration.roles as roles

def roles_tab():
    return rx.vstack(
        roles.frontend.index(),

        width="100%",
        height="100%",
    )

def users_tab():
    return rx.vstack(
        rx.heading("Пользователи", size="7"),
    )

def sidebar_link(text: str, url: str, border_radious: str = "0") -> rx.Component:
    return rx.link(
        rx.button(
            text,

            radius="none",
            variant="soft",
            color=rx.color("accent", 11),

            border_radius="0",

            background_color=rx.color("accent", 3),

            _hover={
                "color": rx.color("accent", 12),
                "background_color": rx.color("accent", 4),
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
    return rx.box(
        rx.vstack(
            rx.heading("Меню", size="6", color=rx.color("accent", 3), bg=rx.color("accent", 9), height="40px", text_align="center", line_height="40px"),
            sidebar_link("Роли", routes.ADMIN_ROLES),
            sidebar_link("Пользователи", routes.ADMIN_USERS),

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

def workspace(**prop):
    return rx.tabs.root(
        rx.tabs.content(
            roles_tab(),

            value=AdministrationState.Tabs.ROLES,
        ),
        rx.tabs.content(
            users_tab(),

            value=AdministrationState.Tabs.USERS,
        ),
        rx.tabs.content(
            rx.text("Welcome"),

            value=AdministrationState.Tabs.WELCOME,
        ),

        value=AdministrationState.current_tab,

        width="100%",
        height="100%",

        **prop
    )

def index():
    return rx.hstack(
        sidebar(),
        workspace(),

        width="100%",
        height="100%",

        padding_left="1em",
        padding_right="1em",
    )