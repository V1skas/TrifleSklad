from typing import List, Optional

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action as SystemAction
from TrifleSklad.declared.submenu import MAIN
from TrifleSklad.models import AuthToken, User
from TrifleSklad.services.auth import AuthService


def route_param(state: rx.State, name: str, default: str = "") -> str:
    """Path-параметр маршруту (наприклад `[id]`, `[tab]`, `[page]`).

    `router.page.params` депрекейтний з Reflex 0.8.1 (буде видалений у 1.0).
    Читаємо через приватний `router._page.params` — це те саме джерело,
    звідки бере дані застарілий публічний геттер, але без deprecation
    warning. З'явиться нормальний публічний API — заміна в одному місці.

    Модульна функція (а не тільки метод `AppState`), бо частина state-класів
    (перехідний період міграції) ще успадковує `rx.State` напряму.
    """
    try:
        return str(state.router._page.params.get(name, default))
    except Exception:
        return default


class AppState(rx.State):
    _auth_service: AuthService = AuthService()

    fio: Optional[str] = None
    user: Optional[User] = None
    user_actions: List[str] = []

    # Cookie живе 30 днів; реальне закінчення сесії контролює серверний
    # AuthToken.expires_at (ковзне вікно з SESSION_TIMEOUT_MINUTES).
    auth_token_value: str = rx.Cookie(name="auth_token", max_age=60 * 60 * 24 * 30, same_site="lax", path="/")
    auth_token: Optional[AuthToken] = None
    # Кеш версії прав користувача — для звірки з актуальною версією у БД
    # (миттєве застосування зміни прав/ролі без релогіну).
    permissions_version_seen: int = 0

    # UI-стан персистентного каркасу (шапка + розділова бічна панель, не
    # пересоздаётся при навигации — см. views/templates/app_shell.py). Сама
    # бічна панель — старий вигляд (фіксована ширина, як у дореформеному
    # TrifleSklad), але підгрупи всередині неї (напр. «Видача»/«Повернення»
    # у розділі «Рух ТМЦ») згортаються тим самим механізмом expanded_groups.
    expanded_groups: List[str] = []

    def check_params(self):
        pass

    def _route_param(self, name: str, default: str = "") -> str:
        return route_param(self, name, default)

    @rx.event
    def toggle_group(self, group_key: str):
        if group_key in self.expanded_groups:
            self.expanded_groups = [g for g in self.expanded_groups if g != group_key]
        else:
            self.expanded_groups = self.expanded_groups + [group_key]

    @rx.var
    def get_user_actions(self) -> List[str]:
        return self.user_actions

    @rx.var
    def is_authenticated(self) -> bool:
        return self.auth_token is not None

    @rx.event
    def require_auth(self):
        if not self.auth_token_value:
            return rx.redirect(routes.LOGIN)

        # На кожному виклику тягнемо токен з БД — get_auth_token попутно:
        #   * чистить протерміновані токени;
        #   * перевіряє expires_at цього токена;
        #   * продовжує ковзне вікно (touch).
        # None означає: токен невалідний або протермінований — розлогуємось.
        token = self._auth_service.get_auth_token(self.auth_token_value)
        if token is None:
            return self.logout()

        first_load = self.auth_token is None
        self.auth_token = token

        if first_load or self.user is None:
            if token.user is None:
                return self.logout()
            self.user = token.user
            self.user_actions = self._auth_service.get_list_user_actions(self.user.login)
            self.fio = self._auth_service.get_fio(self.user.login)
            self.permissions_version_seen = self.user.permissions_version or 0
            return

        # Перевірка бампу версії прав — щоб зміни адміна застосовувалися без релогіну.
        current_version = self._auth_service.get_user_permissions_version(self.user.login)
        if current_version != self.permissions_version_seen:
            self.user_actions = self._auth_service.get_list_user_actions(self.user.login)
            self.fio = self._auth_service.get_fio(self.user.login)
            self.permissions_version_seen = current_version

    @rx.event
    def logout(self):
        if self.auth_token is not None:
            self._auth_service.logout(self.auth_token)
        self.reset()  # Очищає весь стейт (у т.ч. cookie-var auth_token_value)
        return rx.redirect(routes.LOGIN)

    def has_permission(self, action: SystemAction) -> bool:
        if self.auth_token is None:
            return False
        return action.value in self.user_actions

    def has_section_access(self, section: str) -> bool:
        return any(action.startswith(f"{section}:") for action in self.user_actions)

    def _ensure_session(self) -> bool:
        """Гарантує, що auth_token/user/user_actions встановлені з ДІЙСНОЇ
        cookie-сесії, і повертає True — сесія дійсна; False — сесії немає або
        токен протермінований.

        Викликається з гвардів on_load (`access_guard`), тому працює і на
        підстанах (List/Add/Edit/View): auth_token/user/... — успадковані від
        AppState var'и, і присвоєння `self.x = ...` на підстані делегується у
        вузол AppState (Reflex `__setattr__` → `setattr(self.parent_state, ...)`),
        тож шапка (AppState.is_authenticated) бачить зміну.

        Свіже перезавантаження сторінки скидає стан у пам'яті (auth_token=None),
        але cookie лишається — тут ми відновлюємо сесію з неї, щоб залогінений
        користувач не «випадав» на /login. Якщо сесія вже відновлена в цьому
        стані — короткочасно виходимо без зайвого запиту до БД (перевірка
        протермінування/бампу версії — на require_auth при повторному вході)."""
        if self.auth_token is not None and self.user is not None:
            return True
        if not self.auth_token_value:
            return False
        token = self._auth_service.get_auth_token(self.auth_token_value)
        if token is None or token.user is None:
            self.auth_token = None
            return False
        self.auth_token = token
        self.user = token.user
        self.user_actions = self._auth_service.get_list_user_actions(self.user.login)
        self.fio = self._auth_service.get_fio(self.user.login)
        self.permissions_version_seen = self.user.permissions_version or 0
        return True

    def access_guard(self, action: SystemAction):
        """Єдиний гвард сторінкових on_load. Повертає подію редіректу або None:
          * немає дійсної сесії (не залогінені / протермінований токен) → /login
            (а НЕ /welcome — раніше гвард сліпо кидав на /welcome, і при
            автовиході/першому заході без логіну користувач опинявся не там або
            «застрягав»; ще й гоничись із require_auth, що кидав на /login);
          * сесія є, але немає права на цю сторінку → /welcome + тост;
          * доступ дозволено → None.

        Робить перевірку самодостатньою (сам відновлює сесію з cookie), тому не
        залежить від того, чи встиг спрацювати require_auth зі спінера — це й
        усуває гонитву редіректів."""
        if not self._ensure_session():
            return rx.redirect(routes.LOGIN)
        if not self.has_permission(action):
            return [
                rx.redirect(routes.WELCOME),
                rx.toast.error("У Вас немає доступу до цієї сторінки!"),
            ]
        return None

    def access_guard_any(self, *actions: SystemAction):
        """Як `access_guard`, але сторінка доступна за наявності БУДЬ-ЯКОГО з
        перелічених прав (напр. «Заявки» — REQUESTS_LIST або REQUESTS_CREATE)."""
        if not self._ensure_session():
            return rx.redirect(routes.LOGIN)
        if not any(self.has_permission(a) for a in actions):
            return [
                rx.redirect(routes.WELCOME),
                rx.toast.error("У Вас немає доступу до цієї сторінки!"),
            ]
        return None

    @rx.var
    def active_group_url(self) -> str:
        """URL найдовшого (найбільш специфічного) пункту верхнього меню, чий
        `url` є префіксом поточного шляху. Визначає, яку бічну панель розділу
        показати (старий дизайн: своя панель на кожен розділ). Довший префікс
        виграє навмисно — це відсіює «Заявки» (лист без дітей і без панелі)
        від «Каталогу» (з панеллю), хоча заявки технічно й лежать під
        `/catalog/...`."""
        path = self.router.url.path or ""
        best_base = ""
        for item in MAIN:
            if item.url and path.startswith(item.url) and len(item.url) > len(best_base):
                best_base = item.url
        return best_base

    @rx.var
    def has_section_sidebar(self) -> bool:
        url = self.active_group_url
        for item in MAIN:
            if item.url == url:
                return len(item.children) > 0
        return False
