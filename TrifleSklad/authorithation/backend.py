from typing import Optional, Dict, List

import reflex as rx
import hashlib
from sqlalchemy.exc import SQLAlchemyError

from utils import generations

from TrifleSklad.models import User, AuthToken
from TrifleSklad.dao import UserDAO, AuthTokenDAO
from TrifleSklad.state import AppState
from TrifleSklad.routes import WELCOME

class AuthorizationState(rx.State):
    login: str = ""
    password: str = ""
    flag_err: bool = False
    text_err: str = ""

    @rx.var
    def login_error(self) -> bool:
        return self.flag_err
    
    @rx.var
    def login_error_text(self) -> str:
        return self.text_err
    
    @rx.event
    def reset_all(self):
        self.login = ""
        self.password = ""
        self.reset_error()
    
    @rx.event
    def reset_error(self):
        self.flag_err = False
        self.text_err = ""

    @rx.event
    def set_login(self, value: str):
        self.login = value
        self.reset_error()

    @rx.event
    def set_password(self, value: str):
        self.password = value
        self.reset_error()

    @rx.event
    async def auth_handler(self):
        try:
            user: Optional[User] = UserDAO.get_user_by_id_with_relationships(self.login)
            if user is None:
                self.flag_err = True
                self.text_err = "Невірний логін або пароль."
                self.password = ""
                return None
            
            hasher = hashlib.sha256()
            salted_password = (self.password + user.salt).encode('utf-8')
            hasher.update(salted_password)
            calculated_hash = hasher.hexdigest()

            if calculated_hash != user.password_hash:
                self.flag_err = True
                self.text_err = "Невірний логін або пароль."
                self.password = ""
                return None

            app_state = await self.get_state(AppState)

            app_state.user = user
            app_state.user_actions = UserDAO.get_user_actions_by_id(user.login)
            app_state.fio = UserDAO.get_user_fio_by_login(user.login)

            auth_token: str = generations.generate_auth_token()
            AuthTokenDAO.add_one(AuthToken(token=auth_token, id_user=user.login))
            app_state.auth_token = auth_token

            return [rx.redirect(WELCOME), AuthorizationState.reset_all()]
            
        except SQLAlchemyError as e:
            self.flag_err = True
            self.text_err = "Помилка при обробці запиту. Зверніться до адміністратора."
            self.password = ""
            print(f"[AuthorizationState][ERROR] {e}")

    