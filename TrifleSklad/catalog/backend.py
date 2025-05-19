from pydantic import Tag
import reflex as rx

from TrifleSklad import routes
from TrifleSklad.state import AppState

from TrifleSklad.catalog.categories.backend import CategoriesState

class CatalogState(AppState):
    class Tabs:
        CATERORIES = "categories"
        CATALOG = "catalog"

    __tabs_events = {
        Tabs.CATERORIES: CategoriesState.on_load
    }

    current_tab: str = ""

    def _check_path(self):
        tab = self.router.page.params.get("tab", "")

        if tab != "":
            if tab not in [self.Tabs.CATERORIES, self.Tabs.CATALOG]:
                return rx.redirect(routes.WELCOME)

            self.current_tab = tab
            return None

    @rx.event
    def on_load(self):
        result = self._check_path()
        if result is not None:
            return result
        return self.__tabs_events.get(self.current_tab, lambda: print("Not handled event"))()
