import reflex as rx

from components import decor

from TrifleSklad.states.app import AppState
from TrifleSklad.states.auth import AuthState
from TrifleSklad.views.templates import controls


def login_card() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.center(
                decor.logo(size="9", width="100%"),
                rx.divider(),
                rx.heading(
                    "Увійдіть у свій обліковий запис",

                    size="6",
                    as_="h2",
                    text_align="center",
                    width="100%",
                ),

                direction="column",
                spacing="5",
                width="100%",
            ),
            rx.form.root(
                rx.vstack(
                    controls.input_field(
                        rx.input.slot(rx.icon("user")),

                        value=AuthState.login,
                        on_change=AuthState.set_login,

                        placeholder="Логін",
                        size="3",
                        width="100%",
                    ),
                    controls.input_field(
                        rx.input.slot(rx.icon("lock")),

                        value=AuthState.password,
                        on_change=AuthState.set_password,

                        placeholder="Пароль",
                        type="password",
                        size="3",
                        width="100%",
                    ),
                    # type="submit" без on_click — сабміт форми спрацьовує і по
                    # кліку, і по Enter у будь-якому полі (один виклик).
                    rx.button("Увійти", type="submit", size="3", width="100%"),

                    spacing="3",
                    width="100%",
                ),
                # on_submit викликає той самий метод, що й кнопка; дані форми не
                # обробляються — логін/пароль уже в стані (self.login/password).
                on_submit=AuthState.auth_handler,
                reset_on_submit=False,
                width="100%",
            ),
            rx.cond(
                AuthState.login_error,
                rx.callout(
                    AuthState.login_error_text,

                    icon="triangle-alert",
                    role="alert",
                    color_scheme="red",
                    width="100%",
                ),
            ),
        ),

        max_width="28em",
        size="4",
        width="100%",
    )


def index() -> rx.Component:
    return rx.center(
        login_card(),

        height="100vh",
        direction="column",
        spacing="5",
    )


def require_login(page: rx.app.ComponentCallable) -> rx.app.ComponentCallable:
    """Декоратор, що вимагає автентифікації перед рендером сторінки.

    Якщо користувач не автентифікований — редиректить на сторінку логіну.
    """

    def protected_page():
        return rx.cond(
            AppState.is_authenticated,  # type: ignore
            page(),
            rx.center(
                rx.hstack(
                    rx.spinner(size="3"),
                    rx.text("Завантаження...", size="3", on_mount=AppState.require_auth),  # type: ignore
                ),
                height="100vh",
            ),
        )

    protected_page.__name__ = page.__name__
    return protected_page
