from dataclasses import dataclass, field
from typing import List, Optional

from TrifleSklad import routes
from TrifleSklad.actions import Action as Actions


@dataclass
class MenuItem:
    label: str
    icon: str
    url: Optional[str] = None
    children: List["MenuItem"] = field(default_factory=list)
    required_action: Optional[Actions] = None
    # Пункт видимий, якщо є БУДЬ-ЯКЕ з перелічених прав (напр. «Заявки» доступні
    # і тим, хто лише створює заявки, і тим, хто їх переглядає списком).
    required_any: Optional[List[Actions]] = None
    # Якщо True — пункт показується лише на dashboard-сторінці свого розділу,
    # але прибраний із бічного меню.
    dashboard_only: bool = False


MAIN: List[MenuItem] = [
    MenuItem("Адміністрування", "shield-user", routes.ADMIN, children=[
        MenuItem("Співробітники", "users", routes.ADMIN_WORKERS, required_action=Actions.WORKERS_LIST),
        MenuItem("Ролі", "key-round", routes.ADMIN_ROLES, required_action=Actions.ROLES_LIST),
        MenuItem("Користувачі", "user-cog", routes.ADMIN_USERS, required_action=Actions.USERS_LIST),
    ]),
    MenuItem("Каталог", "book-marked", routes.CATALOG, children=[
        MenuItem("Категорії ТМЦ", "tags", routes.CATALOG_CATEGORIES, required_action=Actions.CATEGORIES_LIST),
        MenuItem("Каталог ТМЦ", "package", routes.CATALOG_PRODUCTS, required_action=Actions.PRODUCTS_LIST),
        MenuItem("Власники ТМЦ", "user-round", routes.CATALOG_OWNERS, required_action=Actions.OWNERS_LIST),
        MenuItem("Об'єкти підприємства", "warehouse", routes.CATALOG_STORAGES, required_action=Actions.STORAGE_LIST),
        MenuItem("Клієнти", "users", routes.CATALOG_CLIENTS, required_action=Actions.CLIENT_LIST),
        MenuItem("Постачальники", "truck", routes.CATALOG_SUPPLIERS, required_action=Actions.SUPPLIERS_LIST),
        MenuItem("Типи оплат", "credit-card", routes.CATALOG_PAYMENT_TYPES, required_action=Actions.PAYMENT_TYPE_LIST),
        MenuItem("Ставки ПДВ", "percent", routes.CATALOG_NDS_RATES, required_action=Actions.NDS_RATES_LIST),
    ]),
    # Групування за типом дії (старий дизайн мав плаский список — тут додано
    # угруповання «Видача»/«Повернення», щоб пункти одного типу дії стояли
    # разом; механіка згортання — та сама, що й для розділів верхнього рівня.
    MenuItem("Рух ТМЦ", "arrow-left-right", routes.MOVEMENT, children=[
        MenuItem("Постачання", "package-plus", routes.MOVEMENT_ADMISSIONS, required_action=Actions.ADMISSIONS_LIST),
        MenuItem("Списання", "package-minus", routes.MOVEMENT_WRITE_OFFS, required_action=Actions.WRITE_OFFS_LIST),
        MenuItem("Переміщення", "move", routes.MOVEMENT_MOVEMENTS, required_action=Actions.MOVEMENTS_LIST),
        MenuItem("Видача", "log-out", children=[
            MenuItem("Видачі", "log-out", routes.MOVEMENT_ISSUES, required_action=Actions.ISSUES_LIST),
            MenuItem("Видачі клієнту", "user-check", routes.MOVEMENT_CLIENT_ISSUES, required_action=Actions.CLIENT_ISSUES_LIST),
            MenuItem("Продажі", "shopping-cart", routes.MOVEMENT_SALES, required_action=Actions.SALES_LIST),
        ]),
        MenuItem("Повернення", "undo-2", children=[
            MenuItem("Повернення", "undo-2", routes.MOVEMENT_RETURNS, required_action=Actions.RETURNS_LIST),
            MenuItem("Повернення продажу", "rotate-ccw", routes.MOVEMENT_SALE_RETURNS, required_action=Actions.SALE_RETURNS_LIST),
        ]),
    ]),
    # «Заявки» технічно живуть як вкладка розділу «Каталог», але у навігації —
    # окремий верхньорівневий пункт з іншим набором прав (доступний і тим, хто
    # лише створює власні заявки, без права на перегляд списку каталогу).
    MenuItem("Заявки", "clipboard-list", routes.CATALOG_REQUESTS,
             required_any=[Actions.REQUESTS_LIST, Actions.REQUESTS_CREATE]),
    MenuItem("Звіти", "chart-bar", routes.REPORTS, children=[
        MenuItem("Наявність ТМЦ", "boxes", routes.REPORTS_STOCK, required_action=Actions.REPORTS_STOCK),
        MenuItem("Одиниці ТМЦ", "hash", routes.REPORTS_UNITS, required_action=Actions.REPORTS_UNITS),
        MenuItem("Рух по каталогу ТМЦ", "route", routes.REPORTS_CATALOG_MOVEMENTS, required_action=Actions.REPORTS_CATALOG_MOVEMENTS),
    ]),
]


def find_group_by_url(url: str) -> Optional[MenuItem]:
    """Знайти верхньорівневу групу за її dashboard-маршрутом. Використовується
    рендером section-dashboard-сторінок, щоб не дублювати дерево у view-файлі."""
    for it in MAIN:
        if it.url == url:
            return it
    return None
