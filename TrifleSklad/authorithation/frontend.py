import reflex as rx

from TrifleSklad import routes

from TrifleSklad.authorithation.backend import AuthorizationState

def login_card() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.center(
                rx.center(
                    rx.heading("Trifle", size="9", color=rx.color("accent", 1), background_color=rx.color("accent", 9), padding="0.1em"),
                    rx.heading("Склад", size="9", color=rx.color("accent", 9), background_color="transparent", padding="0.1em"),

                    width="100%"
                ),
                rx.divider(),
                rx.heading(
                    "Войдите в Ваш аккаунт",

                    size="6",
                    as_="h2",
                    text_align="center",
                    width="100%",
                ),

                direction="column",
                spacing="5",
                width="100%",
            ),
            rx.form(
                rx.vstack(
                    rx.input(
                        rx.input.slot(rx.icon("user")),

                        id="login",
                        placeholder="Логин",
                        size="3",
                        width="100%",
                    ),
                    rx.input(
                        rx.input.slot(rx.icon("lock")),

                        id="password",
                        placeholder="Пароль",
                        type="password",
                        size="3",
                        width="100%",
                    ),
                    rx.button("Войти", type="submit", size="3", width="100%"),

                    spacing="3",
                    width="100%",
                ),

                reset_on_submit=True,
                spacing="5",
                on_submit=AuthorizationState.auth_handler,
            ),
            rx.cond(AuthorizationState.login_error,
                    rx.callout(
                        AuthorizationState.login_error_text,
                        
                        icon="triangle_alert",
                        role="alert",
                        color_scheme="red",
                        width="100%",
                    ),
            )
        ),

        max_width="28em",
        size="4",
        width="100%",
    )


def require_login(page: rx.app.ComponentCallable) -> rx.app.ComponentCallable:
    def protected_page():
        return rx.fragment(
            rx.cond(
                AuthorizationState.is_authenticated,
                page(),
                rx.center(
                    rx.text("Загрузка...", on_mount=rx.redirect(routes.LOGIN)),
                ),
            )
        )

    protected_page.__name__ = page.__name__
    return protected_page

def index() -> rx.Component:
    return rx.center(
            login_card(),

            height="100vh",
            direction="column",
            spacing="5",
    )