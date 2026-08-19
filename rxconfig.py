import os

import reflex as rx

# Для локального запуску — SQLite (за замовчуванням). У Docker/compose рядок
# підключення приходить через змінну оточення DB_URL.
DB_URL = os.environ.get("DB_URL", "sqlite:///reflex.db")

config = rx.Config(
    app_name="TrifleSklad",
    db_url=DB_URL,
    # api_url/deploy_url навмисно НЕ задаються — Reflex сам піднімає бекенд і
    # фронтенд на дефолтних портах, без прив'язки збірки фронтенду до
    # конкретної зовнішньої адреси. (Механіка API_URL/DEPLOY_URL з оточення
    # була потрібна лише для запуску фронтенду за nginx — тут не використовується.)
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
