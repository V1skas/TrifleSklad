import reflex as rx

from TrifleSklad.catalog.categories.backend import CategoriesState
from TrifleSklad.catalog.products.backend import ProductsState
from components.elements import sidebar, sidebar_link, workspace

from TrifleSklad import routes

from TrifleSklad.catalog.backend import CatalogState
import TrifleSklad.catalog.categories as categories
import TrifleSklad.catalog.products as products

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

def index():
    return rx.hstack(
        sidebar(
            sidebar_link("Категории ТМЦ", routes.CATALOG_CATEGORIES),
            sidebar_link("Каталог ТМЦ", routes.CATALOG_PRODUCTS),
        ),
        workspace(
            categories_tab(),
            products_tab(),

            size="4",

            value=CatalogState.current_tab
        ),

        width="100%",
        height="100%",

        padding_left="1em",
        padding_right="1em",
    )
