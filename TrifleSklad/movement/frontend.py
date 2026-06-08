import reflex as rx

from components.elements import sidebar, sidebar_link, workspace

from TrifleSklad import routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.state import AppState
from TrifleSklad.movement.backend import MovementState
import TrifleSklad.movement.admissions as admissions
import TrifleSklad.movement.write_off as write_off
import TrifleSklad.movement.movements as movements
import TrifleSklad.movement.issues as issues
import TrifleSklad.movement.sale as sale
import TrifleSklad.movement.returns as returns

def admissions_tab() -> rx.Component:
    return rx.tabs.content(
        admissions.frontend.index(),

        value=MovementState.Tabs.ADMISSIONS,
    )

def write_offs_tab() -> rx.Component:
    return rx.tabs.content(
        write_off.frontend.index(),

        value=MovementState.Tabs.WRITE_OFFS,
    )

def movements_tab() -> rx.Component:
    return rx.tabs.content(
        movements.frontend.index(),

        value=MovementState.Tabs.MOVEMENTS,
    )

def issues_tab() -> rx.Component:
    return rx.tabs.content(
        issues.frontend.index(),

        value=MovementState.Tabs.ISSUES,
    )

def sales_tab() -> rx.Component:
    return rx.tabs.content(
        sale.frontend.index(),

        value=MovementState.Tabs.SALES,
    )

def returns_tab() -> rx.Component:
    return rx.tabs.content(
        returns.frontend.index(),

        value=MovementState.Tabs.RETURNS,
    )

def index():
    return rx.hstack(
        sidebar(
            rx.cond(
                AppState.get_user_actions.contains(ActionEnum.ADMISSIONS_LIST),
                sidebar_link("Постачання", routes.MOVEMENT_ADMISSIONS),
            ),
            rx.cond(
                AppState.get_user_actions.contains(ActionEnum.WRITE_OFFS_LIST),
                sidebar_link("Списання", routes.MOVEMENT_WRITE_OFFS),
            ),
            rx.cond(
                AppState.get_user_actions.contains(ActionEnum.MOVEMENTS_LIST),
                sidebar_link("Переміщення", routes.MOVEMENT_MOVEMENTS),
            ),
            rx.cond(
                AppState.get_user_actions.contains(ActionEnum.ISSUES_LIST),
                sidebar_link("Видачі", routes.MOVEMENT_ISSUES),
            ),
            rx.cond(
                AppState.get_user_actions.contains(ActionEnum.SALES_LIST),
                sidebar_link("Продажі", routes.MOVEMENT_SALES),
            ),
            rx.cond(
                AppState.get_user_actions.contains(ActionEnum.RETURNS_LIST),
                sidebar_link("Повернення", routes.MOVEMENT_RETURNS),
            ),
        ),
        workspace(
            admissions_tab(),
            write_offs_tab(),
            movements_tab(),
            issues_tab(),
            sales_tab(),
            returns_tab(),

            size="4",

            value=MovementState.current_tab
        ),

        width="100%",
        height="100%",

        padding_left="1em",
        padding_right="1em",
    )
