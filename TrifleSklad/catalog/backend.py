from pydantic import Tag
import reflex as rx

from TrifleSklad import routes
from TrifleSklad.state import AppState

from TrifleSklad.catalog.categories.backend import CategoriesState
from TrifleSklad.catalog.products.backend import ProductsState
from TrifleSklad.catalog.owners.backend import OwnerState
from TrifleSklad.catalog.storages.backend import StorageState
from TrifleSklad.catalog.suppliers.backend import SupplierState
from TrifleSklad.catalog.payment_types.backend import PaymentTypeState

class CatalogState(AppState):
    class Tabs:
        CATERORIES = "categories"
        PRODUCTS = "products"
        OWNERS = "owners"
        STORAGES = "storages"
        SUPPLIERS = "suppliers"
        PAYMENT_TYPES = "payment_types"

    __tabs_events = {
        Tabs.CATERORIES: CategoriesState.on_load,
        Tabs.PRODUCTS: ProductsState.on_load,
        Tabs.OWNERS: OwnerState.on_load,
        Tabs.STORAGES: StorageState.on_load,
        Tabs.SUPPLIERS: SupplierState.on_load,
        Tabs.PAYMENT_TYPES: PaymentTypeState.on_load,
    }

    current_tab: str = ""

    def _check_path(self):
        tab = self.router.page.params.get("tab", "")

        if tab != "":
            if tab not in [self.Tabs.CATERORIES, self.Tabs.PRODUCTS, self.Tabs.PAYMENT_TYPES,
                           self.Tabs.OWNERS, self.Tabs.STORAGES, self.Tabs.SUPPLIERS]:
                return rx.redirect(routes.WELCOME)

            self.current_tab = tab
            return None

    @rx.event
    def on_load(self):
        result = self._check_path()
        if result is not None:
            return result
        return self.__tabs_events.get(self.current_tab, lambda: print("Not handled event"))()
