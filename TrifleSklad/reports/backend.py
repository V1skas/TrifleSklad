import reflex as rx

from TrifleSklad import routes
from TrifleSklad.state import AppState

from TrifleSklad.reports.stock.backend import StockReportState


class ReportsState(AppState):
    class Tabs:
        STOCK = "stock"

    __tabs_events = {
        Tabs.STOCK: StockReportState.on_load,
    }

    current_tab: str = ""

    def _check_path(self):
        tab = self.router.page.params.get("tab", "")

        if tab != "":
            if tab not in [self.Tabs.STOCK]:
                return rx.redirect(routes.WELCOME)

            self.current_tab = tab
            return None

    @rx.event
    def on_load(self):
        if not self.has_section_access("reports"):
            return rx.redirect(routes.WELCOME)
        self.current_tab = ""
        result = self._check_path()
        if result is not None:
            return result
        return self.__tabs_events.get(self.current_tab, lambda: None)()
