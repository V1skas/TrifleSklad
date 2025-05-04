"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import reflex as rx

from rxconfig import config

from TrifleSklad import frontend, routes

app = rx.App(
    theme=rx.theme(
            appearance="light",
            has_background=True,
            radius="large",
            accent_color="blue",
        )
)
app.add_page(frontend.welcome_page, route=routes.WELCOME)
app.add_page(frontend.auth_page, route=routes.LOGIN)
app.add_page(frontend.administration_page, route=routes.ADMIN)