from typing import Optional, Dict, List

import reflex as rx
import hashlib
from sqlalchemy.exc import SQLAlchemyError

from TrifleSklad.models import User
from TrifleSklad.dao import UserDAO
from TrifleSklad.state import AppState
from TrifleSklad.routes import INDEX

class AuthorizationState(rx.State):
    flag_err: bool = False
    text_err: str = ""

    @rx.var
    def login_error(self) -> bool:
        return self.flag_err
    
    @rx.var
    def login_error_text(self) -> str:
        return self.text_err

    @rx.event
    def auth_handler(self, form_data: Dict):
        try:
            user: Optional[User] = UserDAO.get_user_by_id_with_relationships(form_data["login"])
            if user is None:
                self.flag_err = True
                self.text_err = "Неверный логин или пароль."
                return
            
            hasher = hashlib.sha256()
            salted_password = (form_data["password"] + user.salt).encode('utf-8')
            hasher.update(salted_password)
            calculated_hash = hasher.hexdigest()

            if calculated_hash != user.hash:
                self.flag_err = True
                self.text_err = "Неверный логин или пароль."
                return
            
            AppState.user = user
            AppState.user_actions = UserDAO.get_user_actions_by_id(user.login)
            return rx.redirect(INDEX)
            
        except SQLAlchemyError as e:
            self.error_message = f"Ошибка при получении пользователя. Обратитесь к администратору."
            print(f"[AuthorizationState][ERROR] {e}")

    