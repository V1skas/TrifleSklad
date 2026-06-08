import reflex as rx
from typing import Optional, List
from TrifleSklad import routes
from TrifleSklad.models import User
from TrifleSklad.dao import UserDAO, AuthTokenDAO
from TrifleSklad.actions import Action as SystemAction

class AppState(rx.State):
    fio: Optional[str] = None
    user: Optional[User] = None
    user_actions: List[str] = []
    
    auth_token: str = rx.LocalStorage(name="auth_token")

    def check_params(self):
        pass
        
    @rx.var
    def get_user_actions(self) -> List[str]:
        return self.user_actions

    @rx.var
    def is_authenticated(self) -> bool:
        return self.user is not None

    @rx.event
    def require_auth(self):
        if not self.auth_token:
            return rx.redirect(routes.LOGIN)

        if self.user is None:
            token = AuthTokenDAO.get_by_token_user_actions(self.auth_token)
            if token is None or token.user is None:
                return self.logout()
            
            self.user = token.user

            self.user_actions = UserDAO.get_user_actions_by_id(self.user.login) 
            self.fio = UserDAO.get_user_fio_by_login(self.user.login)

    @rx.event
    def logout(self):
        if self.auth_token:
            AuthTokenDAO.delete_one(self.auth_token)
        self.reset() # Очищает весь стейт
        return rx.redirect(routes.LOGIN)

    def has_permission(self, action: SystemAction) -> bool:
        if not self.user:
            return False
        return action.value in self.user_actions
    
    def has_section_access(self, section: str) -> bool:
        return any(action.startswith(f"{section}:") for action in self.user_actions)
