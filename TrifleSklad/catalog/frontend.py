import reflex as rx

from TrifleSklad.catalog.categories.backend import CategoriesState
from TrifleSklad.catalog.products.backend import ProductsState
from components.elements import sidebar, sidebar_link, workspace

from TrifleSklad import routes

from TrifleSklad.catalog.backend import CatalogState
import TrifleSklad.catalog.categories as categories
import TrifleSklad.catalog.products as products
import TrifleSklad.catalog.owners as owners
import TrifleSklad.catalog.storages as storages
import TrifleSklad.catalog.suppliers as suppliers
import TrifleSklad.catalog.payment_types as payment_types

def categories_tab() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            categories.frontend.index(),

            width="100%",
            height="100%",
        ),

        value=CatalogState.Tabs.CATERORIES,
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

def index():
    return rx.hstack(
        sidebar(
            sidebar_link("Категории ТМЦ", routes.CATALOG_CATEGORIES),
            sidebar_link("Каталог ТМЦ", routes.CATALOG_PRODUCTS),
            sidebar_link("Владельцы ТМЦ", routes.CATALOG_OWNERS),
            sidebar_link("Хранилища", routes.CATALOG_STORAGES),
            sidebar_link("Поставщики", routes.CATALOG_SUPPLIERS),
            sidebar_link("Типы оплаты", routes.CATALOG_PAYMENT_TYPES),
        ),
        workspace(
            categories_tab(),
            products_tab(),
            owners_tab(),
            storages_tab(),
            suppliers_tab(),
            payment_types_tab(),

            size="4",

            value=CatalogState.current_tab
        ),

        width="100%",
        height="100%",

        padding_left="1em",
        padding_right="1em",
    )
