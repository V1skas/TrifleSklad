"""Welcome to Reflex! This file outlines the steps to create a basic app."""

import reflex as rx

from rxconfig import config
from TrifleSklad import frontend, routes, state
from TrifleSklad.views.templates.app_shell import app_shell_wrap, content_area_wrap, overlay_wrap
from TrifleSklad.states.payment_type import (
    AddPaymentTypeState,
    EditPaymentTypeState,
    ListPaymentTypeState,
    ViewPaymentTypeState,
)
from TrifleSklad.views import payment_type as payment_type_views
from TrifleSklad.states.nds_rate import (
    AddNdsRateState,
    EditNdsRateState,
    ListNdsRateState,
    ViewNdsRateState,
)
from TrifleSklad.views import nds_rate as nds_rate_views
from TrifleSklad.states.owner import (
    AddOwnerState,
    EditOwnerState,
    ListOwnerState,
    ViewOwnerState,
)
from TrifleSklad.views import owner as owner_views
from TrifleSklad.states.supplier import (
    AddSupplierState,
    EditSupplierState,
    ListSupplierState,
    ViewSupplierState,
)
from TrifleSklad.views import supplier as supplier_views
from TrifleSklad.states.storage import (
    AddStorageState,
    EditStorageState,
    ListStorageState,
    ViewStorageState,
)
from TrifleSklad.views import storage as storage_views
from TrifleSklad.states.client import (
    AddClientState,
    EditClientState,
    ListClientState,
    ViewClientState,
)
from TrifleSklad.views import client as client_views
from TrifleSklad.states.category import (
    AddCategoriesState,
    EditCategoriesState,
    ListCategoriesState,
    ViewCategoriesState,
)
from TrifleSklad.views import category as category_views
from TrifleSklad.states.product import (
    AddProductsState,
    EditProductsState,
    ListProductsState,
    ViewProductsState,
)
from TrifleSklad.views import product as product_views
from TrifleSklad.states.request import (
    AddRequestsState,
    EditRequestsState,
    ListRequestsState,
    ProcessRequestsState,
    ViewRequestsState,
)
from TrifleSklad.views import request as request_views
from TrifleSklad.states.worker import (
    AddWorkerState,
    EditWorkerState,
    ListWorkersState,
    ViewWorkerState,
)
from TrifleSklad.views import worker as worker_views
from TrifleSklad.states.role import (
    AddRoleState,
    EditRoleState,
    ListRoleState,
    ViewRoleState,
)
from TrifleSklad.views import role as role_views
from TrifleSklad.states.user import (
    AddUserState,
    EditUserState,
    ListUserState,
    ViewUserState,
)
from TrifleSklad.views import user as user_views
from TrifleSklad.states.write_off import (
    AddWriteOffState,
    EditWriteOffState,
    ListWriteOffState,
    ViewWriteOffState,
)
from TrifleSklad.views import write_off as write_off_views
from TrifleSklad.states.movements import (
    AddMovementsState,
    EditMovementsState,
    ListMovementsState,
    ViewMovementsState,
)
from TrifleSklad.views import movements as movements_views
from TrifleSklad.states.returns import (
    AddReturnsState,
    EditReturnsState,
    ListReturnsState,
    ViewReturnsState,
)
from TrifleSklad.views import returns as returns_views
from TrifleSklad.states.issue import (
    AddIssueState,
    EditIssueState,
    ListIssueState,
    ViewIssueState,
)
from TrifleSklad.views import issue as issue_views
from TrifleSklad.states.sale import (
    AddSaleState,
    EditSaleState,
    ListSaleState,
    ViewSaleState,
)
from TrifleSklad.views import sale as sale_views
from TrifleSklad.states.sale_returns import (
    AddSaleReturnsState,
    EditSaleReturnsState,
    ListSaleReturnsState,
    ViewSaleReturnsState,
)
from TrifleSklad.views import sale_returns as sale_returns_views
from TrifleSklad.states.client_issue import (
    AddClientIssueState,
    EditClientIssueState,
    ListClientIssueState,
    ViewClientIssueState,
)
from TrifleSklad.views import client_issue as client_issue_views
from TrifleSklad.states.admission import (
    AddAdmissionState,
    EditAdmissionState,
    ListAdmissionState,
    ViewAdmissionState,
)
from TrifleSklad.views import admission as admission_views
from TrifleSklad.states.stock_report import StockReportState
from TrifleSklad.views import stock_report as stock_report_views
from TrifleSklad.states.units_report import ListUnitsReportState, ViewUnitsReportState
from TrifleSklad.views import units_report as units_report_views
from TrifleSklad.states.catalog_movements_report import CatalogMovementsReportState
from TrifleSklad.views import catalog_movements_report as catalog_movements_report_views

app = rx.App(
    # Тема налаштовується через rx.plugins.RadixThemesPlugin у rxconfig.py
    # (App(theme=...) депрекейтний з 0.9.0).
    html_lang="uk",
    # Глобальні перевизначення стилів Radix (assets/styles.css) — див. TS-44.
    stylesheets=["styles.css"],
    # Захист від авто-перекладу браузера, який ламає Radix-компоненти
    # (напр. rx.select) під час діффу DOM.
    html_custom_attrs={"translate": "no"},
    head_components=[
        rx.el.meta(name="google", content="notranslate"),
    ],
)

# Персистентний каркас (шапка + сайдбар) — живе над <Outlet/>, не пересоздається
# при навігації між сторінками (views/templates/app_shell.py).
app.extra_app_wraps[15, "AppShell"] = app_shell_wrap
app.extra_app_wraps[10, "ContentArea"] = content_area_wrap
# Перекриваємо штатний app_wrap оверлею (значок «немає звʼязку» + тостер) —
# він рендериться без z-index і губився під таблицями. Див. overlay_wrap.
app.app_wraps[5, "Overlay"] = overlay_wrap

app.add_page(frontend.index_page, route=routes.INDEX)
app.add_page(frontend.welcome_page, route=routes.WELCOME)
app.add_page(frontend.auth_page, route=routes.LOGIN, on_load=state.AppState.check_params)

# Заглушки коренів розділів — щоб клік по пункту навбару не впирався у 404.
app.add_page(frontend.admin_page, route=routes.ADMIN)
app.add_page(frontend.catalog_page, route=routes.CATALOG)
app.add_page(frontend.movement_page, route=routes.MOVEMENT)
app.add_page(frontend.reports_page, route=routes.REPORTS)

# Адміністрування повністю переїхало на постраничну реєстрацію.
app.add_page(worker_views.list_page, route=routes.ADMIN_WORKERS, on_load=ListWorkersState.on_load)
app.add_page(worker_views.add_page, route=routes.ADMIN_WORKERS_ADD, on_load=AddWorkerState.on_load)
app.add_page(worker_views.edit_page, route=routes.ADMIN_WORKERS_EDIT_ID + "[id]", on_load=EditWorkerState.on_load)
app.add_page(worker_views.view_page, route=routes.ADMIN_WORKERS_VIEW_ID + "[id]", on_load=ViewWorkerState.on_load)

app.add_page(role_views.list_page, route=routes.ADMIN_ROLES, on_load=ListRoleState.on_load)
app.add_page(role_views.add_page, route=routes.ADMIN_ROLES_ADD, on_load=AddRoleState.on_load)
app.add_page(role_views.edit_page, route=routes.ADMIN_ROLES_EDIT_ID + "[id]", on_load=EditRoleState.on_load)
app.add_page(role_views.view_page, route=routes.ADMIN_ROLES_VIEW_ID + "[id]", on_load=ViewRoleState.on_load)

app.add_page(user_views.list_page, route=routes.ADMIN_USERS, on_load=ListUserState.on_load)
app.add_page(user_views.add_page, route=routes.ADMIN_USERS_ADD, on_load=AddUserState.on_load)
app.add_page(user_views.edit_page, route=routes.ADMIN_USERS_EDIT_ID + "[id]", on_load=EditUserState.on_load)
app.add_page(user_views.view_page, route=routes.ADMIN_USERS_VIEW_ID + "[id]", on_load=ViewUserState.on_load)

# Каталог повністю переїхав на постраничну реєстрацію (dao/service/state/view
# на кожну сутність) — табовий диспетчер /catalog/[tab]/... більше не потрібен.
app.add_page(payment_type_views.list_page, route=routes.CATALOG_PAYMENT_TYPES, on_load=ListPaymentTypeState.on_load)
app.add_page(payment_type_views.add_page, route=routes.CATALOG_PAYMENT_TYPES_ADD, on_load=AddPaymentTypeState.on_load)
app.add_page(payment_type_views.edit_page, route=routes.CATALOG_PAYMENT_TYPES_EDIT_ID + "[id]", on_load=EditPaymentTypeState.on_load)
app.add_page(payment_type_views.view_page, route=routes.CATALOG_PAYMENT_TYPES_VIEW_ID + "[id]", on_load=ViewPaymentTypeState.on_load)

app.add_page(nds_rate_views.list_page, route=routes.CATALOG_NDS_RATES, on_load=ListNdsRateState.on_load)
app.add_page(nds_rate_views.add_page, route=routes.CATALOG_NDS_RATES_ADD, on_load=AddNdsRateState.on_load)
app.add_page(nds_rate_views.edit_page, route=routes.CATALOG_NDS_RATES_EDIT_ID + "[id]", on_load=EditNdsRateState.on_load)
app.add_page(nds_rate_views.view_page, route=routes.CATALOG_NDS_RATES_VIEW_ID + "[id]", on_load=ViewNdsRateState.on_load)

app.add_page(owner_views.list_page, route=routes.CATALOG_OWNERS, on_load=ListOwnerState.on_load)
app.add_page(owner_views.add_page, route=routes.CATALOG_OWNERS_ADD, on_load=AddOwnerState.on_load)
app.add_page(owner_views.edit_page, route=routes.CATALOG_OWNERS_EDIT_ID + "[id]", on_load=EditOwnerState.on_load)
app.add_page(owner_views.view_page, route=routes.CATALOG_OWNERS_VIEW_ID + "[id]", on_load=ViewOwnerState.on_load)

app.add_page(supplier_views.list_page, route=routes.CATALOG_SUPPLIERS, on_load=ListSupplierState.on_load)
app.add_page(supplier_views.add_page, route=routes.CATALOG_SUPPLIERS_ADD, on_load=AddSupplierState.on_load)
app.add_page(supplier_views.edit_page, route=routes.CATALOG_SUPPLIERS_EDIT_ID + "[id]", on_load=EditSupplierState.on_load)
app.add_page(supplier_views.view_page, route=routes.CATALOG_SUPPLIERS_VIEW_ID + "[id]", on_load=ViewSupplierState.on_load)

app.add_page(storage_views.list_page, route=routes.CATALOG_STORAGES, on_load=ListStorageState.on_load)
app.add_page(storage_views.add_page, route=routes.CATALOG_STORAGES_ADD, on_load=AddStorageState.on_load)
app.add_page(storage_views.edit_page, route=routes.CATALOG_STORAGES_EDIT_ID + "[id]", on_load=EditStorageState.on_load)
app.add_page(storage_views.view_page, route=routes.CATALOG_STORAGES_VIEW_ID + "[id]", on_load=ViewStorageState.on_load)

app.add_page(client_views.list_page, route=routes.CATALOG_CLIENTS, on_load=ListClientState.on_load)
app.add_page(client_views.add_page, route=routes.CATALOG_CLIENTS_ADD, on_load=AddClientState.on_load)
app.add_page(client_views.edit_page, route=routes.CATALOG_CLIENTS_EDIT_ID + "[id]", on_load=EditClientState.on_load)
app.add_page(client_views.view_page, route=routes.CATALOG_CLIENTS_VIEW_ID + "[id]", on_load=ViewClientState.on_load)

app.add_page(category_views.list_page, route=routes.CATALOG_CATEGORIES, on_load=ListCategoriesState.on_load)
app.add_page(category_views.add_page, route=routes.CATALOG_CATEGORIES_ADD, on_load=AddCategoriesState.on_load)
app.add_page(category_views.edit_page, route=routes.CATALOG_CATEGORIES_EDIT_ID + "[id]", on_load=EditCategoriesState.on_load)
app.add_page(category_views.view_page, route=routes.CATALOG_CATEGORIES_VIEW_ID + "[id]", on_load=ViewCategoriesState.on_load)

app.add_page(product_views.list_page, route=routes.CATALOG_PRODUCTS, on_load=ListProductsState.on_load)
app.add_page(product_views.add_page, route=routes.CATALOG_PRODUCTS_ADD, on_load=AddProductsState.on_load)
app.add_page(product_views.edit_page, route=routes.CATALOG_PRODUCTS_EDIT_ID + "[id]", on_load=EditProductsState.on_load)
app.add_page(product_views.view_page, route=routes.CATALOG_PRODUCTS_VIEW_ID + "[id]", on_load=ViewProductsState.on_load)

app.add_page(request_views.list_page, route=routes.CATALOG_REQUESTS, on_load=ListRequestsState.on_load)
app.add_page(request_views.add_page, route=routes.CATALOG_REQUESTS_ADD, on_load=AddRequestsState.on_load)
app.add_page(request_views.edit_page, route=routes.CATALOG_REQUESTS_EDIT_ID + "[id]", on_load=EditRequestsState.on_load)
app.add_page(request_views.view_page, route=routes.CATALOG_REQUESTS_VIEW_ID + "[id]", on_load=ViewRequestsState.on_load)
app.add_page(request_views.process_page, route=routes.CATALOG_REQUESTS_PROCESS_ID + "[id]", on_load=ProcessRequestsState.on_load)

app.add_page(write_off_views.list_page, route=routes.MOVEMENT_WRITE_OFFS, on_load=ListWriteOffState.on_load)
app.add_page(write_off_views.add_page, route=routes.MOVEMENT_WRITE_OFFS_ADD, on_load=AddWriteOffState.on_load)
app.add_page(write_off_views.edit_page, route=routes.MOVEMENT_WRITE_OFFS_EDIT_ID + "[id]", on_load=EditWriteOffState.on_load)
app.add_page(write_off_views.view_page, route=routes.MOVEMENT_WRITE_OFFS_VIEW_ID + "[id]", on_load=ViewWriteOffState.on_load)

app.add_page(movements_views.list_page, route=routes.MOVEMENT_MOVEMENTS, on_load=ListMovementsState.on_load)
app.add_page(movements_views.add_page, route=routes.MOVEMENT_MOVEMENTS_ADD, on_load=AddMovementsState.on_load)
app.add_page(movements_views.edit_page, route=routes.MOVEMENT_MOVEMENTS_EDIT_ID + "[id]", on_load=EditMovementsState.on_load)
app.add_page(movements_views.view_page, route=routes.MOVEMENT_MOVEMENTS_VIEW_ID + "[id]", on_load=ViewMovementsState.on_load)

app.add_page(returns_views.list_page, route=routes.MOVEMENT_RETURNS, on_load=ListReturnsState.on_load)
app.add_page(returns_views.add_page, route=routes.MOVEMENT_RETURNS_ADD, on_load=AddReturnsState.on_load)
app.add_page(returns_views.edit_page, route=routes.MOVEMENT_RETURNS_EDIT_ID + "[id]", on_load=EditReturnsState.on_load)
app.add_page(returns_views.view_page, route=routes.MOVEMENT_RETURNS_VIEW_ID + "[id]", on_load=ViewReturnsState.on_load)

app.add_page(issue_views.list_page, route=routes.MOVEMENT_ISSUES, on_load=ListIssueState.on_load)
app.add_page(issue_views.add_page, route=routes.MOVEMENT_ISSUES_ADD, on_load=AddIssueState.on_load)
app.add_page(issue_views.edit_page, route=routes.MOVEMENT_ISSUES_EDIT_ID + "[id]", on_load=EditIssueState.on_load)
app.add_page(issue_views.view_page, route=routes.MOVEMENT_ISSUES_VIEW_ID + "[id]", on_load=ViewIssueState.on_load)

app.add_page(sale_views.list_page, route=routes.MOVEMENT_SALES, on_load=ListSaleState.on_load)
app.add_page(sale_views.add_page, route=routes.MOVEMENT_SALES_ADD, on_load=AddSaleState.on_load)
app.add_page(sale_views.edit_page, route=routes.MOVEMENT_SALES_EDIT_ID + "[id]", on_load=EditSaleState.on_load)
app.add_page(sale_views.view_page, route=routes.MOVEMENT_SALES_VIEW_ID + "[id]", on_load=ViewSaleState.on_load)

app.add_page(sale_returns_views.list_page, route=routes.MOVEMENT_SALE_RETURNS, on_load=ListSaleReturnsState.on_load)
app.add_page(sale_returns_views.add_page, route=routes.MOVEMENT_SALE_RETURNS_ADD, on_load=AddSaleReturnsState.on_load)
app.add_page(sale_returns_views.add_page, route=routes.MOVEMENT_SALE_RETURNS_ADD + "[id]", on_load=AddSaleReturnsState.on_load)
app.add_page(sale_returns_views.edit_page, route=routes.MOVEMENT_SALE_RETURNS_EDIT_ID + "[id]", on_load=EditSaleReturnsState.on_load)
app.add_page(sale_returns_views.view_page, route=routes.MOVEMENT_SALE_RETURNS_VIEW_ID + "[id]", on_load=ViewSaleReturnsState.on_load)

app.add_page(client_issue_views.list_page, route=routes.MOVEMENT_CLIENT_ISSUES, on_load=ListClientIssueState.on_load)
app.add_page(client_issue_views.add_page, route=routes.MOVEMENT_CLIENT_ISSUES_ADD, on_load=AddClientIssueState.on_load)
app.add_page(client_issue_views.edit_page, route=routes.MOVEMENT_CLIENT_ISSUES_EDIT_ID + "[id]", on_load=EditClientIssueState.on_load)
app.add_page(client_issue_views.view_page, route=routes.MOVEMENT_CLIENT_ISSUES_VIEW_ID + "[id]", on_load=ViewClientIssueState.on_load)

app.add_page(admission_views.list_page, route=routes.MOVEMENT_ADMISSIONS, on_load=ListAdmissionState.on_load)
app.add_page(admission_views.add_page, route=routes.MOVEMENT_ADMISSIONS_ADD, on_load=AddAdmissionState.on_load)
app.add_page(admission_views.edit_page, route=routes.MOVEMENT_ADMISSIONS_EDIT_ID + "[id]", on_load=EditAdmissionState.on_load)
app.add_page(admission_views.view_page, route=routes.MOVEMENT_ADMISSIONS_VIEW_ID + "[id]", on_load=ViewAdmissionState.on_load)

app.add_page(stock_report_views.page, route=routes.REPORTS_STOCK, on_load=StockReportState.on_load)
app.add_page(units_report_views.list_page, route=routes.REPORTS_UNITS, on_load=ListUnitsReportState.on_load)
app.add_page(units_report_views.view_page, route=routes.REPORTS_UNITS_VIEW_ID + "[id]", on_load=ViewUnitsReportState.on_load)
app.add_page(catalog_movements_report_views.page, route=routes.REPORTS_CATALOG_MOVEMENTS, on_load=CatalogMovementsReportState.on_load)
