import reflex as rx

from components.elements import sidebar, sidebar_link, workspace

from TrifleSklad import routes
from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.state import AppState
from TrifleSklad.reports.backend import ReportsState
import TrifleSklad.reports.stock as stock


def stock_tab() -> rx.Component:
    return rx.tabs.content(
        stock.frontend.index(),

        value=ReportsState.Tabs.STOCK,
    )


def index():
    return rx.hstack(
        sidebar(
            rx.cond(
                AppState.get_user_actions.contains(ActionEnum.REPORTS_STOCK),
                sidebar_link("Наявність ТМЦ", routes.REPORTS_STOCK),
            ),
        ),
        workspace(
            stock_tab(),

            size="4",

            value=ReportsState.current_tab,
        ),

        width="100%",
        height="100%",

        padding_left="1em",
        padding_right="1em",
    )
