import reflex as rx

from components.elements import sidebar, sidebar_link, workspace

from TrifleSklad import routes
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.administration.backend import AdministrationState

import TrifleSklad.administration.users as users
import TrifleSklad.administration.roles as roles
import TrifleSklad.administration.workers as workers

def workers_tab():
    return rx.tabs.content(
        rx.vstack(
            workers.frontend.index(),

            width="100%",
            height="100%",
        ),

        value=AdministrationState.Tabs.WORKERS,
    )

def roles_tab():
    return rx.tabs.content(
        rx.vstack(
            roles.frontend.index(),

            width="100%",
            height="100%",
        ),

        value=AdministrationState.Tabs.ROLES,
    )

def users_tab():
    return rx.tabs.content(
        rx.vstack(
            users.frontend.index(),

            width="100%",
            height="100%",
        ),

        value=AdministrationState.Tabs.USERS,
    )

def index():
    return rx.hstack(
        sidebar(
            rx.cond(
                AppState.get_user_actions.contains(ActionEnum.WORKERS_LIST),
                sidebar_link("Співробітники", routes.ADMIN_WORKERS),
            ),
            rx.cond(
                AppState.get_user_actions.contains(ActionEnum.ROLES_LIST),
                sidebar_link("Ролі", routes.ADMIN_ROLES),
            ),
            rx.cond(
                AppState.get_user_actions.contains(ActionEnum.USERS_LIST),
                sidebar_link("Користувачі", routes.ADMIN_USERS),
            ),
        ),
        workspace(
            workers_tab(),
            roles_tab(),
            users_tab(),

            size="4",

            value=AdministrationState.current_tab,
        ),

        width="100%",
        height="100%",

        padding_left="1em",
        padding_right="1em",
    )