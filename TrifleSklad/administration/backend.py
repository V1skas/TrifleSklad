import reflex as rx

class AdministrationState(rx.State):
    class Tabs:
        ROLES = "roles"
        USERS = "users"