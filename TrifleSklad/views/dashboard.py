import reflex as rx

from TrifleSklad.declared.submenu import MenuItem


def section_dashboard_content(group: MenuItem) -> rx.Component:
    """Заглушка кореневої сторінки розділу (`/admin`, `/catalog`, `/movement`,
    `/reports`) — щоб клік по пункту навбару, що веде на групу, не впирався
    у 404. Конкретні підсторінки розділу відкриваються з бічної панелі
    зліва (вона показується автоматично для цих маршрутів)."""
    return rx.vstack(
        rx.heading(group.label, size="8", color=rx.color("accent", 9), text_align="center"),
        rx.text("Оберіть потрібний пункт у меню зліва.", size="4", color="gray", text_align="center"),
        spacing="4",
        justify="center",
        align="center",
        min_height="60vh",
        width="100%",
    )


def main_dashboard_content() -> rx.Component:
    """Головна сторінка — старий вигляд (`git show
    dev:TrifleSklad/frontend.py::welcome_page`): просто вітання, без плиток
    розділів (вони дублювали б навігацію у верхньому навбарі)."""
    return rx.vstack(
        rx.heading("Ласкаво просимо до Trifle Склад!", size="9", color=rx.color("accent", 9)),
        rx.text(
            "Для початку роботи, оберіть потрібний розділ у шапці сторінки.",
            size="5",
        ),
        spacing="5",
        justify="center",
        align="center",
        min_height="75vh",
        width="100%",
    )
