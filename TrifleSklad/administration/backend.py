import reflex as rx

from TrifleSklad import routes
from TrifleSklad.state import AppState

from TrifleSklad.administration.roles.backend import RoleState
from TrifleSklad.administration.workers.backend import WorkersState
from TrifleSklad.administration.users.backend import UserState

class AdministrationState(AppState):
    class Tabs:
        WORKERS = "workers"
        ROLES = "roles"
        USERS = "users"

    __tabs_events = {
        Tabs.ROLES: RoleState.on_load,
        Tabs.WORKERS: WorkersState.on_load,
        Tabs.USERS: UserState.on_load,
    }

    current_tab: str = ""

    def _check_path(self):
        tab = self.router.page.params.get("tab", "")

        if tab != "":
            if tab not in [self.Tabs.ROLES, self.Tabs.USERS, self.Tabs.WORKERS]:
                return rx.redirect(routes.WELCOME)
            
            self.current_tab = tab
            return None
        
    @rx.event
    def on_load(self):
        result = self._check_path()
        if result is not None:
            return result
        return self.__tabs_events.get(self.current_tab, lambda: print("Not handled event"))()
