import reflex as rx

from typing import Optional, Dict, List

from TrifleSklad import routes

from TrifleSklad.models import User, AuthToken
from TrifleSklad.dao import UserDAO, AuthTokenDAO

class AppState(rx.State):
    """The app state."""

    user: Optional[User] = None
    user_actions: List[str] = []
    auth_token: Optional[str] = rx.LocalStorage(name="auth_token")

    @rx.var
    def is_authenticated(self) -> bool:
        return self.user is not None
    
    @rx.event
    def check_params(self):
        print(self.router.page.path)
        print(self.router.page.params)

    @rx.event
    def check_user_actions(self, action: str) -> bool:
        if self.user is None:
            return False
        return action in self.user_actions

    @rx.event
    def logout(self):
        AuthTokenDAO.delete_one(self.auth_token)
        self.reset()
        return rx.redirect(routes.LOGIN)

    @rx.var
    def check_auth(self) -> bool:
        if self.auth_token is None:
            return False

        if self.user is None:
            token = AuthTokenDAO.get_by_token_user_actions(self.auth_token)
            if token is None:
                self.logout()
                return False
            self.user = token.user
            if self.user is not None:
                self.user_actions = UserDAO.get_user_actions_by_id(self.user.login)
            else:
                self.logout()
                return False
        return True

    @rx.event
    def check_actions(self, action: str) -> bool:
        if self.user is None:
            return False
        return action in self.user_actions

    @rx.event
    def redir(self):
        if not self.is_hydrated:
            return AppState.redir()

        if not self.is_authenticated:
            return rx.redirect(routes.LOGIN)

        return None