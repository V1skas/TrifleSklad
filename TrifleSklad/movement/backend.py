import reflex as rx

from TrifleSklad import routes
from TrifleSklad.state import AppState

from TrifleSklad.movement.admissions.backend import AdmissionState
from TrifleSklad.movement.write_off.backend import WriteOffState
from TrifleSklad.movement.movements.backend import MovementsState
from TrifleSklad.movement.issues.backend import IssueState
from TrifleSklad.movement.sale.backend import SaleState
from TrifleSklad.movement.returns.backend import ReturnsState

class MovementState(AppState):
    class Tabs:
        ADMISSIONS = "admissions"
        WRITE_OFFS = "write_offs"
        MOVEMENTS = "movements"
        ISSUES = "issues"
        SALES = "sales"
        RETURNS = "returns"

    __tabs_events = {
        Tabs.ADMISSIONS: AdmissionState.on_load,
        Tabs.WRITE_OFFS: WriteOffState.on_load,
        Tabs.MOVEMENTS: MovementsState.on_load,
        Tabs.ISSUES: IssueState.on_load,
        Tabs.SALES: SaleState.on_load,
        Tabs.RETURNS: ReturnsState.on_load,
    }

    current_tab: str = ""

    def _check_path(self):
        tab = self.router.page.params.get("tab", "")

        if tab != "":
            if tab not in [self.Tabs.ADMISSIONS, self.Tabs.WRITE_OFFS, self.Tabs.MOVEMENTS, self.Tabs.ISSUES, self.Tabs.SALES, self.Tabs.RETURNS]:
                return rx.redirect(routes.WELCOME)

            self.current_tab = tab
            return None

    @rx.event
    def on_load(self):
        if (not self.has_section_access("admissions")
            and not self.has_section_access("write_offs")
            and not self.has_section_access("movements")
            and not self.has_section_access("issues")
            and not self.has_section_access("sales")
            and not self.has_section_access("returns")):
            return rx.redirect(routes.WELCOME)
        self.current_tab = ""
        result = self._check_path()
        if result is not None:
            return result
        return self.__tabs_events.get(self.current_tab, lambda: None)()
