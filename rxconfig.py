import os

import reflex as rx

# Для локального запуску — SQLite (за замовчуванням). У Docker/compose рядок
# підключення приходить через змінну оточення DB_URL.
DB_URL = os.environ.get("DB_URL", "sqlite:///reflex.db")

API_URL = os.environ.get("API_URL", "http://localhost:8000")
DEPLOY_URL = os.environ.get("DEPLOY_URL", "http://localhost:3000")

config = rx.Config(
    app_name="TrifleSklad",
    db_url=DB_URL,
    api_url=API_URL,
    deploy_url=DEPLOY_URL,
    # У Reflex 0.9 auto-setters вимкнені за замовчуванням (на відміну від 0.7.4,
    # де вони діяли неявно) — усі `set_*` тепер мають бути оголошені явно.
    # Явний прапорець `state_auto_setters=False` сам став депрекейтним (це вже
    # єдина поведінка, опцію приберуть) — тому НЕ виставляємо його тут.
    show_built_with_reflex=False,
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        rx.plugins.RadixThemesPlugin(
            theme=rx.theme(
                appearance="light",
                has_background=True,
                radius="large",
                accent_color="blue",
            )
        ),
    ],
)
