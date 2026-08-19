import reflex as rx

from TrifleSklad import routes
from TrifleSklad.declared.submenu import find_group_by_url
from TrifleSklad.views import auth as auth_views
from TrifleSklad.views.auth import require_login
from TrifleSklad.views.dashboard import main_dashboard_content, section_dashboard_content


def auth_page() -> rx.Component:
    return auth_views.index()


def index_page() -> rx.Component:
    return rx.fragment(on_mount=rx.redirect(routes.WELCOME))


@require_login
def welcome_page() -> rx.Component:
    # Шапка й сайдбар — персистентний каркас (views/templates/app_shell.py),
    # тут лишається лише контент сторінки.
    return main_dashboard_content()


def _section_page(url: str):
    # Заглушка кореневої сторінки розділу — щоб клік по пункту навбару не
    # впирався у 404 (сама сторінка розділу відкривається з бічної панелі).
    group = find_group_by_url(url)

    @require_login
    def page() -> rx.Component:
        return section_dashboard_content(group)

    return page


admin_page = _section_page(routes.ADMIN)
catalog_page = _section_page(routes.CATALOG)
movement_page = _section_page(routes.MOVEMENT)
reports_page = _section_page(routes.REPORTS)
