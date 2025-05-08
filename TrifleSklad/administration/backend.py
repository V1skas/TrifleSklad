import reflex as rx

from TrifleSklad import routes

class AdministrationState(rx.State):
    class Tabs:
        WELCOME = "welcome"
        ROLES = "roles"
        USERS = "users"

    current_tab: str = ""

    def set_current_tab(self, new_tab: str):
        self.current_tab = new_tab

    @rx.var
    def get_current_tab(self) -> str:
        return self.current_tab


    @rx.event
    def check_path(self):
        if self.router.page.params.get("tab", "") != "":
            self.set_current_tab(self.router.page.params.get("tab", ""))

            if self.current_tab not in [self.Tabs.ROLES, self.Tabs.USERS, self.Tabs.WELCOME]:
                return rx.redirect(routes.ADMIN_WELCOME)
        else:
            return rx.redirect(routes.ADMIN_WELCOME)

    @rx.event
    def on_mount(self):
        return self.check_path()