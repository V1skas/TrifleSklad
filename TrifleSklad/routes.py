INDEX = "/"
LOGIN = "/login"
WELCOME = "/welcome"

ADMIN_TAB = "/admin/[tab]/"
ADMIN_TAB_PAGE = "/admin/[tab]/[page]/"
ADMIN_TAB_PAGE_ID = "/admin/[tab]/[page]/[id]/"

ADMIN = "/admin"

ADMIN_WORKERS = "/admin/workers/"
ADMIN_WORKERS_VIEW_ID = "/admin/workers/view/"
ADMIN_WORKERS_EDIT_ID = "/admin/workers/edit/"
ADMIN_WORKERS_ADD = "/admin/workers/add/"

ADMIN_ROLES = "/admin/roles/"
ADMIN_ROLES_VIEW_ID = "/admin/roles/view/"
ADMIN_ROLES_EDIT_ID = "/admin/roles/edit/"
ADMIN_ROLES_ADD = "/admin/roles/add/"

ADMIN_USERS = "/admin/users"
ADMIN_USERS_VIEW_ID = "/admin/users/view/"
ADMIN_USERS_EDIT_ID = "/admin/users/edit/"
ADMIN_USERS_ADD = "/admin/users/add/"

CATALOG_TAB = "/catalog/[tab]/"
CATALOG_TAB_PAGE = "/catalog/[tab]/[page]/"
CATALOG_TAB_PAGE_ID = "/catalog/[tab]/[page]/[id]/"

CATALOG = "/catalog"

CATALOG_CATEGORIES = "/catalog/categories/"
CATALOG_CATEGORIES_VIEW_ID = "/catalog/categories/view/"
CATALOG_CATEGORIES_EDIT_ID = "/catalog/categories/edit/"
CATALOG_CATEGORIES_ADD = "/catalog/categories/add/"

CATALOG_PRODUCTS = "/catalog/products/"
CATALOG_PRODUCTS_VIEW_ID = "/catalog/products/view/"
CATALOG_PRODUCTS_EDIT_ID = "/catalog/products/edit/"
CATALOG_PRODUCTS_ADD = "/catalog/products/add/"

CATALOG_OWNERS = "/catalog/owners/"
CATALOG_OWNERS_VIEW_ID = "/catalog/owners/view/"
CATALOG_OWNERS_EDIT_ID = "/catalog/owners/edit/"
CATALOG_OWNERS_ADD = "/catalog/owners/add/"

CATALOG_SUPPLIERS = "/catalog/suppliers/"
CATALOG_SUPPLIERS_VIEW_ID = "/catalog/suppliers/view/"
CATALOG_SUPPLIERS_EDIT_ID = "/catalog/suppliers/edit/"
CATALOG_SUPPLIERS_ADD = "/catalog/suppliers/add/"

CATALOG_STORAGES = "/catalog/storages/"
CATALOG_STORAGES_VIEW_ID = "/catalog/storages/view/"
CATALOG_STORAGES_EDIT_ID = "/catalog/storages/edit/"
CATALOG_STORAGES_ADD = "/catalog/storages/add/"

CATALOG_PAYMENT_TYPES = "/catalog/payment_types/"
CATALOG_PAYMENT_TYPES_VIEW_ID = "/catalog/payment_types/view/"
CATALOG_PAYMENT_TYPES_EDIT_ID = "/catalog/payment_types/edit/"
CATALOG_PAYMENT_TYPES_ADD = "/catalog/payment_types/add/"

CATALOG_NDS_RATES = "/catalog/nds_rates/"
CATALOG_NDS_RATES_VIEW_ID = "/catalog/nds_rates/view/"
CATALOG_NDS_RATES_EDIT_ID = "/catalog/nds_rates/edit/"
CATALOG_NDS_RATES_ADD = "/catalog/nds_rates/add/"

CATALOG_REQUESTS = "/catalog/requests/"
CATALOG_REQUESTS_VIEW_ID = "/catalog/requests/view/"
CATALOG_REQUESTS_EDIT_ID = "/catalog/requests/edit/"
CATALOG_REQUESTS_ADD = "/catalog/requests/add/"
CATALOG_REQUESTS_PROCESS_ID = "/catalog/requests/process/"

MOVEMENT_TAB = "/movement/[tab]/"
MOVEMENT_TAB_PAGE = "/movement/[tab]/[page]/"
MOVEMENT_TAB_PAGE_ID = "/movement/[tab]/[page]/[id]/"

MOVEMENT = "/movement"

MOVEMENT_ADMISSIONS = "/movement/admissions/"
MOVEMENT_ADMISSIONS_VIEW_ID = "/movement/admissions/view/"
MOVEMENT_ADMISSIONS_EDIT_ID = "/movement/admissions/edit/"
MOVEMENT_ADMISSIONS_ADD = "/movement/admissions/add/"

MOVEMENT_WRITE_OFFS = "/movement/write_offs/"
MOVEMENT_WRITE_OFFS_VIEW_ID = "/movement/write_offs/view/"
MOVEMENT_WRITE_OFFS_EDIT_ID = "/movement/write_offs/edit/"
MOVEMENT_WRITE_OFFS_ADD = "/movement/write_offs/add/"

MOVEMENT_MOVEMENTS = "/movement/movements/"
MOVEMENT_MOVEMENTS_VIEW_ID = "/movement/movements/view/"
MOVEMENT_MOVEMENTS_EDIT_ID = "/movement/movements/edit/"
MOVEMENT_MOVEMENTS_ADD = "/movement/movements/add/"

MOVEMENT_ISSUES = "/movement/issues/"
MOVEMENT_ISSUES_VIEW_ID = "/movement/issues/view/"
MOVEMENT_ISSUES_EDIT_ID = "/movement/issues/edit/"
MOVEMENT_ISSUES_ADD = "/movement/issues/add/"

MOVEMENT_SALES = "/movement/sales/"
MOVEMENT_SALES_VIEW_ID = "/movement/sales/view/"
MOVEMENT_SALES_EDIT_ID = "/movement/sales/edit/"
MOVEMENT_SALES_ADD = "/movement/sales/add/"

MOVEMENT_RETURNS = "/movement/returns/"
MOVEMENT_RETURNS_VIEW_ID = "/movement/returns/view/"
MOVEMENT_RETURNS_EDIT_ID = "/movement/returns/edit/"
MOVEMENT_RETURNS_ADD = "/movement/returns/add/"

REPORTS_TAB = "/reports/[tab]/"
REPORTS_TAB_PAGE = "/reports/[tab]/[page]/"
REPORTS_TAB_PAGE_ID = "/reports/[tab]/[page]/[id]/"

REPORTS = "/reports"

REPORTS_STOCK = "/reports/stock/"

REPORTS_UNITS = "/reports/units/"
REPORTS_UNITS_VIEW_ID = "/reports/units/view/"


# Нумерація рухів наскрізна, але кожен тип живе у власній підсекції.
# Хелпер будує посилання на перегляд руху з потрібного розділу за його типом.
from TrifleSklad.declared import MovementsType  # noqa: E402

_MOVEMENT_VIEW_ROUTES = {
    MovementsType.ADMISSION: MOVEMENT_ADMISSIONS_VIEW_ID,
    MovementsType.WRITE_OFF: MOVEMENT_WRITE_OFFS_VIEW_ID,
    MovementsType.MOVEMENT: MOVEMENT_MOVEMENTS_VIEW_ID,
    MovementsType.ISSUE: MOVEMENT_ISSUES_VIEW_ID,
    MovementsType.SALE: MOVEMENT_SALES_VIEW_ID,
    MovementsType.RETURN: MOVEMENT_RETURNS_VIEW_ID,
}


def movement_view_url(movement_type: int, movement_id: int) -> str:
    base = _MOVEMENT_VIEW_ROUTES.get(movement_type, "")
    return f"{base}{movement_id}" if base else ""