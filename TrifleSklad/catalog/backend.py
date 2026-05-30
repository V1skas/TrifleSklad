import reflex as rx

from TrifleSklad import routes
from TrifleSklad.state import AppState

from TrifleSklad.catalog.categories.backend import CategoriesState
from TrifleSklad.catalog.products.backend import ProductsState
from TrifleSklad.catalog.owners.backend import OwnerState
from TrifleSklad.catalog.storages.backend import StorageState
from TrifleSklad.catalog.suppliers.backend import SupplierState
from TrifleSklad.catalog.payment_types.backend import PaymentTypeState
from TrifleSklad.catalog.nds_rates.backend import NdsRateState

class CatalogState(AppState):
    class Tabs:
        CATEGORIES = "categories"
        PRODUCTS = "products"
        OWNERS = "owners"
        STORAGES = "storages"
        SUPPLIERS = "suppliers"
        PAYMENT_TYPES = "payment_types"
        NDS_RATES = "nds_rates"

    __tabs_events = {
        Tabs.CATEGORIES: CategoriesState.on_load,
        Tabs.PRODUCTS: ProductsState.on_load,
        Tabs.OWNERS: OwnerState.on_load,
        Tabs.STORAGES: StorageState.on_load,
        Tabs.SUPPLIERS: SupplierState.on_load,
        Tabs.PAYMENT_TYPES: PaymentTypeState.on_load,
        Tabs.NDS_RATES: NdsRateState.on_load,
    }

    current_tab: str = ""

    def _check_path(self):
        tab = self.router.page.params.get("tab", "")

        if tab != "":
            if tab not in [self.Tabs.CATEGORIES, self.Tabs.PRODUCTS, self.Tabs.PAYMENT_TYPES,
                           self.Tabs.OWNERS, self.Tabs.STORAGES, self.Tabs.SUPPLIERS,
                           self.Tabs.NDS_RATES]:
                return rx.redirect(routes.WELCOME)

            self.current_tab = tab
            return None

    @rx.event
    def on_load(self):
        if (not self.has_section_access("categories")
            and not self.has_section_access("products")
            and not self.has_section_access("suppliers")
            and not self.has_section_access("owners")
            and not self.has_section_access("storage")
            and not self.has_section_access("payment_types")
            and not self.has_section_access("nds_rates")):
            return rx.redirect(routes.WELCOME)
        self.current_tab = ""
        result = self._check_path()
        if result is not None:
            return result
        return self.__tabs_events.get(self.current_tab, lambda: print("Not handled event"))()
