import reflex as rx

from typing import List

from TrifleSklad.catalog.categories.backend import CategoriesState
from TrifleSklad.catalog.products.backend import ProductsState
from components.elements import sidebar, sidebar_link, workspace

from TrifleSklad import routes
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum

from TrifleSklad.catalog.backend import CatalogState
import TrifleSklad.catalog.categories as categories
import TrifleSklad.catalog.products as products
import TrifleSklad.catalog.owners as owners
import TrifleSklad.catalog.storages as storages
import TrifleSklad.catalog.suppliers as suppliers
import TrifleSklad.catalog.payment_types as payment_types
import TrifleSklad.catalog.nds_rates as nds_rates
import TrifleSklad.catalog.requests as requests

def categories_tab() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            categories.frontend.index(),

            width="100%",
            height="100%",
        ),

        value=CatalogState.Tabs.CATEGORIES,
    )

def products_tab() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            products.frontend.index(),

            width="100%",
            height="100%",
        ),

        value=CatalogState.Tabs.PRODUCTS,
    )

def owners_tab() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            owners.frontend.index(),

            width="100%",
            height="100%",
        ),

        value=CatalogState.Tabs.OWNERS,
    )

def storages_tab() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            storages.frontend.index(),

            width="100%",
            height="100%",
        ),

        value=CatalogState.Tabs.STORAGES,
    )

def suppliers_tab() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            suppliers.frontend.index(),

            width="100%",
            height="100%",
        ),

        value=CatalogState.Tabs.SUPPLIERS,
    )

def payment_types_tab() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            payment_types.frontend.index(),

            width="100%",
            height="100%",
        ),

        value=CatalogState.Tabs.PAYMENT_TYPES,
    )

def nds_rates_tab() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            nds_rates.frontend.index(),

            width="100%",
            height="100%",
        ),

        value=CatalogState.Tabs.NDS_RATES,
    )

def requests_tab() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            requests.frontend.index(),

            width="100%",
            height="100%",
        ),

        value=CatalogState.Tabs.REQUESTS,
    )

def index():
    return rx.hstack(
        rx.cond(
            CatalogState.current_tab != CatalogState.Tabs.REQUESTS,
            sidebar(
                rx.cond(
                    AppState.get_user_actions.contains(ActionEnum.CATEGORIES_LIST),
                    sidebar_link("Категорії ТМЦ", routes.CATALOG_CATEGORIES),
                    ),
                rx.cond(
                    AppState.get_user_actions.contains(ActionEnum.PRODUCTS_LIST),
                    sidebar_link("Каталог ТМЦ", routes.CATALOG_PRODUCTS),
                ),
                rx.cond(
                    AppState.get_user_actions.contains(ActionEnum.OWNERS_LIST),
                    sidebar_link("Власники ТМЦ", routes.CATALOG_OWNERS),
                ),
                rx.cond(
                    AppState.get_user_actions.contains(ActionEnum.STORAGE_LIST),
                    sidebar_link("Об'єкти підприємства", routes.CATALOG_STORAGES),
                ),
                rx.cond(
                    AppState.get_user_actions.contains(ActionEnum.SUPPLIERS_LIST),
                    sidebar_link("Постачальники", routes.CATALOG_SUPPLIERS),
                ),
                rx.cond(
                    AppState.get_user_actions.contains(ActionEnum.PAYMENT_TYPE_LIST),
                    sidebar_link("Типи оплат", routes.CATALOG_PAYMENT_TYPES),
                ),
                rx.cond(
                    AppState.get_user_actions.contains(ActionEnum.NDS_RATES_LIST),
                    sidebar_link("Ставки ПДВ", routes.CATALOG_NDS_RATES),
                ),
            ),
        ),
        workspace(
            categories_tab(),
            products_tab(),
            owners_tab(),
            storages_tab(),
            suppliers_tab(),
            payment_types_tab(),
            nds_rates_tab(),
            requests_tab(),

            size="4",

            value=CatalogState.current_tab
        ),

        width="100%",
        height="100%",

        padding_left="1em",
        padding_right="1em",
    )
