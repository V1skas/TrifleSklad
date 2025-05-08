"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import reflex as rx

from rxconfig import config

from TrifleSklad import frontend, routes, state, administration

app = rx.App(
    theme=rx.theme(
            appearance="light",
            has_background=True,
            radius="large",
            accent_color="blue",
        )
)
app.add_page(frontend.welcome_page, route=routes.WELCOME, on_load=state.AppState.check_params)
app.add_page(frontend.auth_page, route=routes.LOGIN, on_load=state.AppState.check_params)

app.add_page(frontend.administration_page, route=routes.ADMIN_TAB, on_load=[state.AppState.check_params, administration.backend.AdministrationState.check_path])
app.add_page(frontend.administration_page, route=routes.ADMIN_TAB_PAGE, on_load=[state.AppState.check_params, administration.backend.AdministrationState.check_path])
app.add_page(frontend.administration_page, route=routes.ADMIN_TAB_PAGE_ID, on_load=[state.AppState.check_params, administration.backend.AdministrationState.check_path])