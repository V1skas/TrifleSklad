import reflex as rx

from TrifleSklad.routes import WELCOME
from TrifleSklad.services.auth import AuthService
from TrifleSklad.states.app import AppState


class AuthState(rx.State):
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
            result = AuthService().auth(self.login, self.password)
            if result is None:
                self.flag_err = True
                self.text_err = "Невірний логін або пароль."
                self.password = ""
                return None

            user, auth_token = result

            app_state = await self.get_state(AppState)
            app_state.user = user
            app_state.auth_token = auth_token
            app_state.auth_token_value = auth_token.token
            app_state.user_actions = AuthService().get_list_user_actions(user.login)
            app_state.fio = AuthService().get_fio(user.login)
            app_state.permissions_version_seen = user.permissions_version or 0

            return [rx.redirect(WELCOME), AuthState.reset_all()]
        except Exception as e:
            print(f"[AuthState][auth_handler][ERROR] {e}")
            self.flag_err = True
            self.text_err = "Помилка при обробці запиту. Зверніться до адміністратора."
            self.password = ""
