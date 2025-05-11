import reflex as rx

from TrifleSklad import routes
from TrifleSklad.state import AppState

from TrifleSklad.administration.roles.backend import RoleState

class AdministrationState(AppState):
    class Tabs:
        WELCOME = "welcome"
        ROLES = "roles"
        USERS = "users"

    __tabs_events = {
        Tabs.ROLES: RoleState.on_load,
    }

    current_tab: str = ""

    def _check_path(self):
        print("AdministrationState._check_path")
        tab = self.router.page.params.get("tab", "")

        if tab != "":
            if tab not in [self.Tabs.ROLES, self.Tabs.USERS, self.Tabs.WELCOME]:
                return rx.redirect(routes.ADMIN_WELCOME)
            
            self.current_tab = tab
        else:
            return rx.redirect(routes.ADMIN_WELCOME)
        
    @rx.event
    def on_load(self):
        print("AdministrationState.on_load")
        self._check_path()
        print(f"Current tab: {self.current_tab}\n")
        return self.__tabs_events.get(self.current_tab, lambda: print("Not handled event"))()
