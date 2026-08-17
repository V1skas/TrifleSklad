from typing import Dict, List, Tuple

import reflex as rx

from TrifleSklad.dao_legacy import ProductCatalogDAO, ProductDAO
from TrifleSklad.models import Product


# Сентинел «без вибору» для select-ів (Radix забороняє порожнє value у item).
ALL = "all"


class ProductsSelectorState(rx.State):
    # Обрані одиниці (повні об'єкти) — лишаються видимими завжди, незалежно від
    # фільтрів. Доступні (необрані) одиниці підвантажуються порціями з сервера.
    selected: List[Product] = []
    available: List[Product] = []

    # Параметри місця/власника та одиниці, які треба виключити (вже у русі).
    filter_by_owner: int = -1
    filter_by_storage: int = -1
    exclude_products: List[int] = []

    # Каскад вибору: категорія → позиція каталогу. Список одиниць з'являється
    # лише після вибору конкретної позиції каталогу.
    category_options: List[Tuple[str, str]] = []
    catalog_options: List[Tuple[str, str]] = []
    filter_category: str = ALL          # id категорії або ALL
    filter_catalog: str = ALL           # id позиції каталогу або ALL
    filter_accounting: str = ALL        # ALL / "included" / "excluded"

    # Метадані обраної позиції каталогу (для міри / прогресу / валідації).
    sel_divisible: bool = False
    sel_capacity: int = 0
    sel_no_fixed_capacity: bool = False
    sel_unit: str = ""

    # Загальна доступна кількість обраної позиції каталогу на місці/власнику
    # (одиниць і сумарного залишку) — довідково в діалозі, незалежно від того,
    # скільки з них уже обрано/показано на поточній сторінці.
    total_units: int = 0
    total_measure: int = 0

    # Масовий вибір: кількість штук та обсяг у одиницях виміру (лише подільне).
    mass_count: str = ""
    mass_measure: str = ""

    # Намір розділення решти при наборі за мірою: id одиниці → обсяг дочірньої
    # одиниці. Передається назовні; реальний split — на збереженні руху.
    split_intent: Dict[int, int] = {}

    # Пошук (лише за s/n / id — назву не шукаємо, позиція вже обрана).
    filter_search: str = ""

    # Пагінація підвантаження за вимогою.
    _offset: int = 0
    _limit: int = 30
    has_more: bool = False

    # Прапорці завантаження (для скелетону: первинне/після фільтра — is_loading,
    # довантаження наступної порції — is_loading_more).
    is_loading: bool = False
    is_loading_more: bool = False

    def clear(self) -> None:
        self.selected = []
        self.available = []
        self.filter_by_owner = -1
        self.filter_by_storage = -1
        self.exclude_products = []
        self.category_options = []
        self.catalog_options = []
        self.filter_category = ALL
        self.filter_catalog = ALL
        self.filter_accounting = ALL
        self.sel_divisible = False
        self.sel_capacity = 0
        self.sel_unit = ""
        self.total_units = 0
        self.total_measure = 0
        self.mass_count = ""
        self.mass_measure = ""
        self.split_intent = {}
        self.filter_search = ""
        self._offset = 0
        self.has_more = False
        self.is_loading = False
        self.is_loading_more = False

    def reset_items(self) -> None:
        """Скидає переліки ТМЦ і пагінацію (без скидання фільтрів/місця). Потрібно
        перед перезавантаженням діалогу — щоб під час проміжної дельти-скелетону
        не лишалися застарілі дані."""
        self.selected = []
        self.available = []
        self.split_intent = {}
        self._offset = 0
        self.has_more = False

    # Dynamic variables
    # ======================
    @rx.var
    def catalog_chosen(self) -> bool:
        return self.filter_catalog != ALL and self.filter_catalog != ""

    @rx.var
    def has_items(self) -> bool:
        if len(self.available) > 0:
            return True
        catalog_id = self._catalog_id_value()
        if catalog_id == -1:
            return len(self.selected) > 0
        return any(
            item.product_catalog is not None
            and item.product_catalog.id == catalog_id
            for item in self.selected
        )

    @rx.var
    def get_selected_items(self) -> List[Tuple[int, Product]]:
        # Без обраної позиції каталогу показуємо всі обрані одиниці; з обраною —
        # лише її. Повний перелік selected завжди лишається для повернення назовні.
        catalog_id = self._catalog_id_value()
        if catalog_id == -1:
            return [(item.id, item) for item in self.selected]
        return [
            (item.id, item)
            for item in self.selected
            if item.product_catalog is not None
            and item.product_catalog.id == catalog_id
        ]

    @rx.var
    def get_available_items(self) -> List[Tuple[int, Product]]:
        return [(item.id, item) for item in self.available]

    @rx.var
    def selected_total_units(self) -> int:
        return len(self.selected)

    @rx.var
    def total_available_label(self) -> str:
        # Довідково: скільки всього доступно цієї позиції каталогу на обраному
        # місці/власнику (незалежно від того, скільки вже обрано в діалозі).
        if not self.catalog_chosen:
            return ""
        if self.sel_divisible:
            return f"Всього доступно: {self.total_units} од. ({self.total_measure} {self.sel_unit})"
        return f"Всього доступно: {self.total_units} од."

    @rx.var
    def selected_summary(self) -> List[Tuple[str, str]]:
        # Групуємо обране за позицією каталогу (selected може містити одиниці
        # різних позицій з різними одиницями виміру, тож єдина сума неможлива).
        totals: Dict[int, float] = {}
        titles: Dict[int, str] = {}
        units: Dict[int, str] = {}
        divisible: Dict[int, bool] = {}
        for p in self.selected:
            if p.product_catalog is None:
                continue
            cid = p.product_catalog.id
            titles[cid] = p.product_catalog.title
            units[cid] = p.product_catalog.unit or ""
            divisible[cid] = p.product_catalog.divisible
            totals[cid] = totals.get(cid, 0) + self.split_intent.get(p.id, p.count)
        result = []
        for cid, title in titles.items():
            qty = totals[cid]
            qty_str = f"{qty:g}" if divisible[cid] else str(int(qty))
            result.append((title, f"{qty_str} {units[cid]}".strip()))
        return sorted(result, key=lambda t: t[0])
    # ======================

    # Backend only
    # ======================
    def _catalog_id_value(self) -> int:
        if self.filter_catalog == ALL or self.filter_catalog == "":
            return -1
        try:
            return int(self.filter_catalog)
        except ValueError:
            return -1

    def _category_id_value(self) -> int:
        if self.filter_category == ALL or self.filter_category == "":
            return -1
        try:
            return int(self.filter_category)
        except ValueError:
            return -1

    def _excluded_ids(self) -> List[int]:
        # Виключаємо вже додані до руху одиниці та вже обрані в діалозі (будь-якої
        # позиції каталогу).
        return list(self.exclude_products) + [p.id for p in self.selected]

    def _selected_count_for_current_catalog(self) -> int:
        catalog_id = self._catalog_id_value()
        return sum(
            1
            for p in self.selected
            if p.product_catalog is not None and p.product_catalog.id == catalog_id
        )

    def _selected_measure_for_current_catalog(self) -> int:
        # Сумарний обсяг (у одиницях виміру) обраних одиниць поточної позиції:
        # для одиниць із наміром розділення (набір за мірою) рахуємо лише обсяг
        # дочірньої одиниці, для решти — повний залишок.
        catalog_id = self._catalog_id_value()
        total = 0
        for p in self.selected:
            if p.product_catalog is not None and p.product_catalog.id == catalog_id:
                total += self.split_intent.get(p.id, p.count)
        return total

    def _sync_mass_fields(self) -> None:
        # Поля масового вибору відображають поточний стан обраного поточної позиції:
        # кількість штук та (для подільного) сумарний обсяг у одиницях виміру.
        self.mass_count = str(self._selected_count_for_current_catalog())
        self.mass_measure = (
            str(self._selected_measure_for_current_catalog())
            if self.sel_divisible
            else ""
        )

    def _load_catalog_meta(self) -> None:
        catalog_id = self._catalog_id_value()
        if catalog_id == -1:
            self.sel_divisible = False
            self.sel_capacity = 0
            self.sel_unit = ""
            return
        catalog = ProductCatalogDAO.get_by_id(catalog_id)
        if catalog is None:
            self.sel_divisible = False
            self.sel_capacity = 0
            self.sel_no_fixed_capacity = False
            self.sel_unit = ""
            return
        self.sel_divisible = catalog.divisible
        self.sel_capacity = catalog.capacity
        self.sel_no_fixed_capacity = bool(catalog.no_fixed_capacity)
        self.sel_unit = catalog.unit

    def _load_catalog_totals(self) -> None:
        catalog_id = self._catalog_id_value()
        if catalog_id == -1:
            self.total_units = 0
            self.total_measure = 0
            return
        self.total_units, self.total_measure = ProductDAO.get_stock_totals_by_owner_storage(
            self.filter_by_owner, self.filter_by_storage, catalog_id, list(self.exclude_products)
        )

    def _load_page(self, reset: bool) -> None:
        # Список доступний одразу: без обраної позиції — усі ТМЦ місця/власника,
        # звужені за категорією та текстовим пошуком.
        if reset:
            self._offset = 0
            self.available = []
        items, has_more = ProductDAO.get_filtered_paginated_by_owner_storage(
            owner_id=self.filter_by_owner,
            storage_id=self.filter_by_storage,
            exclude_ids=self._excluded_ids(),
            search=self.filter_search,
            catalog_id=self._catalog_id_value(),
            category_id=self._category_id_value(),
            accounting=self.filter_accounting,
            offset=self._offset,
            limit=self._limit,
        )
        if reset:
            self.available = items
        else:
            self.available = self.available + items
        self._offset += len(items)
        self.has_more = has_more

    def _reload_catalog_options(self) -> None:
        self.catalog_options = [
            (title, str(cid))
            for cid, title in ProductDAO.get_catalog_options_by_owner_storage(
                self.filter_by_owner, self.filter_by_storage, self._category_id_value()
            )
        ]

    def set_filter(
        self,
        owner: int = -1,
        storage: int = -1,
        products: List[int] = [],
    ) -> None:
        """Ініціалізація діалогу: задає місце/власника, перелік виключень,
        завантажує опції категорій/каталогу та повний список одиниць. Усі
        фільтри доступні одразу, каскад не блокує."""
        self.filter_by_owner = owner
        self.filter_by_storage = storage
        self.exclude_products = products
        self.filter_search = ""
        self.filter_category = ALL
        self.filter_catalog = ALL
        self.filter_accounting = ALL
        self.sel_divisible = False
        self.sel_capacity = 0
        self.sel_unit = ""
        self.total_units = 0
        self.total_measure = 0
        self.mass_count = ""
        self.mass_measure = ""
        self.category_options = [
            (title, str(cid))
            for cid, title in ProductDAO.get_categories_by_owner_storage(owner, storage)
        ]
        self._reload_catalog_options()
        self._offset = 0
        self.has_more = False
        self._load_page(reset=True)
    # ======================

    # Action handlers
    # ======================
    @rx.event
    def load_more(self):
        # Захист від гонок: одне прокручування не має підтягнути кілька сторінок.
        if self.is_loading_more or not self.has_more or self.is_loading:
            return
        self.is_loading_more = True
        yield
        self._load_page(reset=False)
        self.is_loading_more = False

    @rx.event
    def apply_filters(self):
        self.is_loading = True
        yield
        self._load_page(reset=True)
        self.is_loading = False

    @rx.event
    def reset_filters(self):
        self.filter_category = ALL
        self.filter_catalog = ALL
        self.filter_accounting = ALL
        self.filter_search = ""
        self.mass_count = ""
        self.mass_measure = ""
        self.sel_divisible = False
        self.sel_capacity = 0
        self.sel_unit = ""
        self.total_units = 0
        self.total_measure = 0
        self._reload_catalog_options()
        self.is_loading = True
        yield
        self._load_page(reset=True)
        self.is_loading = False

    @rx.event
    def change_filter_category(self, value: str):
        self.filter_category = value
        # Скидаємо обрану позицію каталогу; список звужуємо до категорії.
        self.filter_catalog = ALL
        self.sel_divisible = False
        self.sel_capacity = 0
        self.sel_unit = ""
        self.mass_count = ""
        self.mass_measure = ""
        self._reload_catalog_options()
        self.is_loading = True
        yield
        self._load_page(reset=True)
        self.is_loading = False

    @rx.event
    def change_filter_catalog(self, value: str):
        # Текстовий пошук не скидаємо — доступний одразу й переживає зміну позиції.
        self.filter_catalog = value
        self._load_catalog_meta()
        self._load_catalog_totals()
        self._sync_mass_fields()
        self.is_loading = True
        yield
        self._load_page(reset=True)
        self.is_loading = False

    @rx.event
    def change_filter_search(self, value: str):
        self.filter_search = value
        return ProductsSelectorState.apply_filters

    @rx.event
    def change_filter_accounting(self, value: str):
        self.filter_accounting = value
        self.is_loading = True
        yield
        self._load_page(reset=True)
        self.is_loading = False

    @rx.event
    def set_mass_count(self, value: str):
        self.mass_count = value

    @rx.event
    def set_mass_measure(self, value: str):
        self.mass_measure = value

    @rx.event
    def apply_mass_count(self):
        """Масовий вибір за кількістю штук (sync): доводить вибір поточної позиції
        каталогу до цільового числа — більше додає, менше знімає зайві."""
        if self._catalog_id_value() == -1:
            return
        try:
            target = int(self.mass_count)
        except (TypeError, ValueError):
            yield rx.toast.error("Вкажіть коректну кількість!")
            return
        if target < 0:
            yield rx.toast.error("Кількість не може бути від'ємною!")
            return

        self.is_loading = True
        yield

        # Знімаємо всі поточні обрані цієї позиції каталогу (повертаємо назад).
        self._deselect_current_catalog()
        # Добираємо потрібну кількість одиниць (для подільного — лише повні).
        units = ProductDAO.get_units_for_mass_select(
            owner_id=self.filter_by_owner,
            storage_id=self.filter_by_storage,
            catalog_id=self._catalog_id_value(),
            exclude_ids=self._excluded_ids(),
            full_only=self.sel_divisible,
            capacity=self.sel_capacity,
            no_fixed=self.sel_no_fixed_capacity,
            limit=target,
        )
        self.selected = self.selected + units
        self._sync_mass_fields()
        self._load_page(reset=True)
        self.is_loading = False
        if len(units) < target:
            yield rx.toast.warning(f"Доступно лише {len(units)} одиниць!")

    @rx.event
    def apply_mass_measure(self):
        """Масовий вибір подільного ТМЦ за обсягом у одиницях виміру. Жадібно
        набирає цілі одиниці за спаданням залишку; решту (не кратну) відзначає
        для авто-розділення (split на збереженні руху)."""
        if self._catalog_id_value() == -1 or not self.sel_divisible:
            return
        try:
            target = int(float(self.mass_measure))
        except (TypeError, ValueError):
            yield rx.toast.error("Вкажіть коректний обсяг!")
            return
        if target <= 0:
            yield rx.toast.error("Обсяг має бути більшим за 0!")
            return

        self.is_loading = True
        yield

        self._deselect_current_catalog()
        units = ProductDAO.get_units_for_measure(
            owner_id=self.filter_by_owner,
            storage_id=self.filter_by_storage,
            catalog_id=self._catalog_id_value(),
            exclude_ids=self._excluded_ids(),
        )
        remaining = target
        chosen: List[Product] = []
        for unit in units:
            if remaining <= 0:
                break
            if unit.count <= remaining:
                chosen.append(unit)
                remaining -= unit.count
            else:
                # unit.count > remaining > 0 — відділяємо точний обсяг решти.
                self.split_intent[unit.id] = remaining
                chosen.append(unit)
                remaining = 0
                break

        self.selected = self.selected + chosen
        self._sync_mass_fields()
        self._load_page(reset=True)
        self.is_loading = False
        if remaining > 0:
            yield rx.toast.warning(
                f"Набрано {target - remaining} з {target} {self.sel_unit} "
                "(більше немає в наявності)!"
            )

    def _deselect_current_catalog(self) -> None:
        catalog_id = self._catalog_id_value()
        kept: List[Product] = []
        for product in self.selected:
            if (
                product.product_catalog is not None
                and product.product_catalog.id == catalog_id
            ):
                self.split_intent.pop(product.id, None)
            else:
                kept.append(product)
        self.selected = kept

    @rx.event
    def select_item(self, product_id: int) -> None:
        # Переносимо одиницю з доступних в обрані (лишається видимою при фільтрах).
        for index, product in enumerate(self.available):
            if product.id == product_id:
                self.selected = self.selected + [self.available.pop(index)]
                self._sync_mass_fields()
                return

    @rx.event
    def deselect_item(self, product_id: int) -> None:
        # Повертаємо одиницю з обраних у початок доступних.
        for index, product in enumerate(self.selected):
            if product.id == product_id:
                removed = self.selected.pop(index)
                self.split_intent.pop(removed.id, None)
                self.available = [removed] + self.available
                self._sync_mass_fields()
                return

    def get_selected_items_only(self) -> List[Product]:
        return list(self.selected)

    def get_split_intent(self) -> Dict[int, int]:
        return dict(self.split_intent)
    # ======================
