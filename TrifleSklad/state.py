import reflex as rx

from typing import Optional, Dict, List

from TrifleSklad.models import User

class AppState(rx.State):
    """The app state."""

    user: Optional[User] = None
    user_actions: List[str] = []

    @rx.var
    def is_authenticated(self) -> bool:
        return self.user is not None

    @rx.event
    def check_user_actions(self, action: str) -> bool:
        if self.user is None:
            return False
        return action in self.user_actions