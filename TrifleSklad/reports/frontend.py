import reflex as rx

from components.elements import sidebar, sidebar_link, workspace

from TrifleSklad import routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.state import AppState
from TrifleSklad.reports.backend import ReportsState
import TrifleSklad.reports.stock as stock
import TrifleSklad.reports.units as units


def stock_tab() -> rx.Component:
    return rx.tabs.content(
        stock.frontend.index(),

        value=ReportsState.Tabs.STOCK,
    )


def units_tab() -> rx.Component:
    return rx.tabs.content(
        units.frontend.index(),

        value=ReportsState.Tabs.UNITS,
    )


def index():
    return rx.hstack(
        sidebar(
            rx.cond(
                AppState.get_user_actions.contains(ActionEnum.REPORTS_STOCK),
                sidebar_link("Наявність ТМЦ", routes.REPORTS_STOCK),
            ),
            rx.cond(
                AppState.get_user_actions.contains(ActionEnum.REPORTS_UNITS),
                sidebar_link("Одиниці ТМЦ", routes.REPORTS_UNITS),
            ),
        ),
        workspace(
            stock_tab(),
            units_tab(),

            size="4",

            value=ReportsState.current_tab,
        ),

        width="100%",
        height="100%",

        padding_left="1em",
        padding_right="1em",
    )
