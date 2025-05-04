from turtle import width
import reflex as rx

from TrifleSklad.administration.backend import AdministrationState

def roles():
    return rx.vstack(
        rx.heading("Роли", size="7"),
    )

def users():
    return rx.text("Users")

def sidebar():
    return rx.card(
        rx.vstack(
            rx.heading("Меню", size="6", color=rx.color("accent", 3), bg=rx.color("accent", 9), height="50px", text_align="center", line_height="50px"),
            rx.button(
                "Роли",
                size="3",
                radius="none",
                variant='soft',
                #on_click=rx.redirect(AdministrationState.Tabs.ROLES)
            ),
            rx.button(
                "Пользователи",
                size="3",
                radius="none",
                variant='soft',
                #on_click=rx.redirect(AdministrationState.Tabs.USERS)
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