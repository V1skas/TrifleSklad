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
            sidebar_link("Роли", routes.ADMIN_ROLES),
            sidebar_link("Пользователи", routes.ADMIN_USERS),
            rx.dialog.root(
                rx.dialog.trigger(
                    sidebar_link("Действия", "#"),
                ),
                rx.dialog.content(
                    actions.frontend.index(height="50em"),

                    padding="0",
                ),

                on_open_change=actions.backend.ActionsState.on_load([]),
            ),
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
    )

def index():
    return rx.hstack(
        sidebar(),
        workspace(),

        width="100%",
        height="100%",
    )