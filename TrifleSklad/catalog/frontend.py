import reflex as rx

from TrifleSklad.catalog.categories.backend import CategoriesState
from components.elements import sidebar, sidebar_link, workspace

from TrifleSklad import routes

from TrifleSklad.catalog.backend import CatalogState
import TrifleSklad.catalog.categories as categories

def categories_tab() -> rx.Component:
    return rx.tabs.content(
        rx.vstack(
            categories.frontend.index(),

            width="100%",
            height="100%",
        ),

        value=CatalogState.Tabs.CATERORIES,
    )

def index():
    return rx.hstack(
        sidebar(
            sidebar_link("Категории ТМЦ", routes.CATALOG_CATEGORIES),
            sidebar_link("Каталог ТМЦ", "#"),
        ),
        workspace(
            categories_tab(),

            size="4",

            value=CatalogState.current_tab
        ),

        width="100%",
        height="100%",

        padding_left="1em",
        padding_right="1em",
    )
