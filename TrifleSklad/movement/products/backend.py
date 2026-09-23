from typing import Dict, List, Optional, Tuple

import reflex as rx

from TrifleSklad.dao_legacy import ProductDAO
from TrifleSklad.declared import (
    format_amount,
    format_transferred_qty,
    generate_serial_range,
    sale_line_cost,
)
from TrifleSklad.models import Product
from TrifleSklad.movement.products_selector.backend import ProductsSelectorState


class ProductsMovementListState(rx.State):
    items: List[Product] = []

    dialog_open: bool = False
    view_mode: bool = False

    filter_by_owner: int = -1
    filter_by_storage: int = -1

    # Подільне ТМЦ: режим (передати цілком / розділити) та обсяг частини,
    # ключ — id одиниці товару.
    split_mode: Dict[int, bool] = {}
    split_amount: Dict[int, str] = {}

    # Позначка «поза бухгалтерським обліком», ключ — id одиниці товару.
    # Видима лише там, де вмикається (повернення — set_show_excluded(True)).
    excluded: Dict[int, bool] = {}
    show_excluded: bool = False

    # Розгорнуті позиції каталогу в таблиці (клік по рядку розкриває перелік
    # одиниць). Ключ — id позиції каталогу.
    expanded_catalogs: Dict[int, bool] = {}

    # Чи обов'язковий вибір власника для відкриття діалогу. Вимикається там, де
    # власник не задається (напр. повернення з площадки — фільтр лише за складом,
    # кожна одиниця зберігає свого власника).
    require_owner: bool = True

    # Обов'язковість серійного номера (вмикається лише там, де він потрібен —
    # напр. при видачі/продажу/списанні ТМЦ із серійним номером).
    require_serial: bool = False

    # Показ поля серійного номера без обов'язковості (напр. при переміщенні —
    # s/n можна уточнити, але це не обов'язково). require_serial теж робить поле
    # видимим (див. serial_visible).
    show_serial: bool = False

    # Ввід ціни за позицію (вмикається лише там, де він потрібен — напр. продаж).
    # Ключ — id позиції каталогу, значення — введена ціна за одиницю.
    require_price: bool = False
    prices: Dict[int, str] = {}

    # Одиниці, що вже входили в рух на момент відкриття форми редагування —
    # потрібні, щоб відрізнити «стару» одиницю від щойно доданої.
    preloaded_ids: List[int] = []

    _products_selector_state: Optional[ProductsSelectorState] = None

    async def on_load(self):
        # FUTURE: обследовать работу, возможно есть способ лучше
        self._products_selector_state = await self.get_state(ProductsSelectorState)
        self._products_selector_state.clear()
        self.split_mode = {}
        self.split_amount = {}
        self.excluded = {}
        self.show_excluded = False
        self.expanded_catalogs = {}
        self.require_owner = True
        self.require_serial = False
        self.show_serial = False
        self.require_price = False
        self.prices = {}
        self.serial_mask = {}
        self.serial_range_from = {}
        self.serial_range_to = {}
        self.serial_range_hex = {}
        # Скидаємо фільтри місця/власника, інакше кнопка «Додати» лишається
        # активною зі застарілими значеннями (і діалог показав би чужий ТМЦ),
        # доки користувач не обере склад і власника заново.
        self.filter_by_owner = -1
        self.filter_by_storage = -1
        self.items = []
        self.preloaded_ids = []

    def set_view_mode(self, is_view: bool):
        self.view_mode = is_view

    def set_require_serial(self, flag: bool):
        self.require_serial = flag

    def set_show_serial(self, flag: bool):
        self.show_serial = flag

    def set_show_excluded(self, flag: bool):
        self.show_excluded = flag

    @rx.var
    def serial_visible(self) -> bool:
        # Поле s/n показуємо як коли воно обов'язкове (видача/продаж/списання),
        # так і коли лише дозволене (переміщення).
        return self.require_serial or self.show_serial

    def set_require_owner(self, flag: bool):
        self.require_owner = flag

    def set_require_price(self, flag: bool):
        self.require_price = flag

    @rx.event
    def set_price(self, catalog_id: int, value: str):
        self.prices[catalog_id] = value

    def get_prices(self) -> Dict[int, float]:
        result: Dict[int, float] = {}
        for catalog_id, value in self.prices.items():
            try:
                result[catalog_id] = float(value) if value not in (None, "") else 0.0
            except (TypeError, ValueError):
                result[catalog_id] = 0.0
        return result

    @rx.event
    def set_serial_number(self, product_id: int, value: str):
        for index, product in enumerate(self.items):
            if product.id == product_id:
                self.items[index].serial_number = value
                break

    # Заповнення серійних номерів діапазоном за маскою (напр. "СН-{n}", 1..5).
    # Індивідуально для кожної позиції каталогу (ключ — id позиції каталогу),
    # оскільки різний ТМЦ може мати різні правила формування серійних номерів.
    # ======================
    serial_mask: Dict[int, str] = {}
    serial_range_from: Dict[int, str] = {}
    serial_range_to: Dict[int, str] = {}
    serial_range_hex: Dict[int, bool] = {}

    @rx.event
    def on_change_serial_mask(self, catalog_id: int, value: str):
        self.serial_mask[catalog_id] = value

    @rx.event
    def on_change_serial_range_from(self, catalog_id: int, value: str):
        self.serial_range_from[catalog_id] = value

    @rx.event
    def on_change_serial_range_to(self, catalog_id: int, value: str):
        self.serial_range_to[catalog_id] = value

    @rx.event
    def on_change_serial_range_hex(self, catalog_id: int, value: bool):
        self.serial_range_hex[catalog_id] = value

    @rx.event
    def fill_serial_range(self, catalog_id: int):
        empty_indexes = [
            i
            for i, p in enumerate(self.items)
            if p.product_catalog is not None
            and p.product_catalog.id == catalog_id
            and p.product_catalog.uniq
            and not p.serial_number
        ]
        if not empty_indexes:
            return rx.toast.error("Усі серійні номери вже заповнені!")
        values, error = generate_serial_range(
            self.serial_mask.get(catalog_id, ""),
            self.serial_range_from.get(catalog_id, "1"),
            self.serial_range_to.get(catalog_id, "1"),
            len(empty_indexes),
            self.serial_range_hex.get(catalog_id, False),
        )
        if error is not None:
            return rx.toast.error(error)
        items = list(self.items)
        for i, value in zip(empty_indexes, values):
            items[i].serial_number = value
        # Явне переприсвоєння — гарантує, що фронтенд побачить зміни одразу для
        # всіх позицій (мутація елементів списку в циклі не завжди позначає
        # реактивний var брудним для масового пакетного оновлення).
        self.items = items
        self.serial_mask[catalog_id] = ""
    # ======================

    @rx.var
    def is_view_mode(self) -> bool:
        return self.view_mode

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def ability_open_dialog(self) -> bool:
        # Потрібен обраний склад; власник — лише якщо require_owner.
        if self.filter_by_storage <= -1:
            return False
        return self.filter_by_owner > -1 or not self.require_owner

    @rx.var
    def get_items(self) -> List[Tuple[int, Product]]:
        return [(index, item) for index, item in enumerate(self.items)]

    @rx.event
    def toggle_catalog(self, catalog_id: int):
        self.expanded_catalogs[catalog_id] = not self.expanded_catalogs.get(
            catalog_id, False
        )

    @rx.var
    def grouped(
        self,
    ) -> List[Tuple[int, str, str, bool, bool, str, List[Tuple[int, Product]]]]:
        # Групує одиниці за позицією каталогу для таблиці:
        # (id каталогу, назва, к-сть, подільне?, унікальне?, залишок,
        #  перелік (глобальний індекс у self.items, Product)).
        # «К-сть» (group[2]) — для подільного з фіксованою ємністю дробове по
        # ємності + фіз. к-сть у дужках (format_transferred_qty), інакше число
        # фіз. одиниць. Залишок — сума count подільних одиниць групи (для
        # контролю обсягу), інакше «—». Глобальний індекс потрібен для
        # on_remove_selected/split_*.
        order: List[int] = []
        groups: Dict[
            int, Tuple[str, bool, bool, bool, float, float, List[Tuple[int, Product]]]
        ] = {}
        for index, product in enumerate(self.items):
            catalog = product.product_catalog
            if catalog is None:
                continue
            catalog_id = catalog.id
            if catalog_id not in groups:
                order.append(catalog_id)
                groups[catalog_id] = (
                    catalog.title,
                    catalog.divisible,
                    catalog.uniq,
                    bool(catalog.no_fixed_capacity),
                    catalog.capacity or 0,
                    0,
                    [],
                )
            title, divisible, uniq, no_fixed, capacity, remainder, units = groups[catalog_id]
            units.append((index, product))
            groups[catalog_id] = (
                title,
                divisible,
                uniq,
                no_fixed,
                capacity,
                remainder + (product.count or 0),
                units,
            )
        result: List[Tuple[int, str, str, bool, bool, str, List[Tuple[int, Product]]]] = []
        for catalog_id in order:
            title, divisible, uniq, no_fixed, capacity, remainder, units = groups[catalog_id]
            result.append(
                (
                    catalog_id,
                    title,
                    format_transferred_qty(remainder, len(units), divisible, capacity, no_fixed),
                    divisible,
                    uniq,
                    format_amount(remainder) if divisible else "—",
                    units,
                )
            )
        return result

    @rx.var
    def group_sums(self) -> Dict[int, float]:
        # Сума по позиції каталогу (для продажу). Для подільного ТМЦ, проданого
        # частиною, ціна за цілу одиницю масштабується пропорційно залишку
        # (sale_line_cost), інакше — ціна × к-сть одиниць.
        prices = self.get_prices()
        sums: Dict[int, float] = {}
        for catalog_id, units in self._grouped_units().items():
            sums[catalog_id] = sale_line_cost(prices.get(catalog_id, 0.0), units)
        return sums

    def _grouped_units(self) -> Dict[int, List[Tuple[int, bool, int]]]:
        # Групує вибрані одиниці за позицією каталогу:
        # id -> [(count, divisible, capacity), ...].
        groups: Dict[int, List[Tuple[int, bool, int]]] = {}
        for product in self.items:
            catalog = product.product_catalog
            if catalog is None:
                continue
            groups.setdefault(catalog.id, []).append(
                (product.count or 0, catalog.divisible, catalog.capacity)
            )
        return groups

    @rx.var
    def total_cost(self) -> float:
        prices = self.get_prices()
        total = 0.0
        for catalog_id, units in self._grouped_units().items():
            total += sale_line_cost(prices.get(catalog_id, 0.0), units)
        return round(total, 2)

    @rx.event
    def open_dialog(self):
        # Спершу показуємо скелетон, потім (після yield) довантажуємо ТМЦ —
        # щоб користувач бачив процес завантаження, а не порожній діалог.
        self._products_selector_state.is_loading = True
        # Скидаємо не лише items, а й службові індекси — інакше обчислювані
        # get_(un)selected_items впадуть на застарілих індексах під час дельти.
        self._products_selector_state.reset_items()
        self.dialog_open = True
        yield
        filter_products = [item.id for item in self.items]
        self._products_selector_state.set_filter(
            self.filter_by_owner, self.filter_by_storage, filter_products
        )
        self._products_selector_state.is_loading = False

    @rx.event
    def close_dialog(self):
        self.dialog_open = False

    @rx.event
    def on_save_selected(self):
        selected = self._products_selector_state.get_selected_items_only()
        # Намір авто-розділення решти (набір подільного ТМЦ за мірою): id → обсяг.
        split_intent = self._products_selector_state.get_split_intent()
        self.items += selected
        # За замовчуванням — передати цілком; режим розділення вмикає користувач
        # або масовий набір за мірою (split_intent).
        for product in selected:
            if self._is_divisible(product):
                if product.id in split_intent:
                    self.split_mode[product.id] = True
                    self.split_amount[product.id] = str(split_intent[product.id])
                else:
                    self.split_mode[product.id] = False
                    self.split_amount[product.id] = ""
            self.excluded.setdefault(product.id, False)
            # Ініціалізуємо ціну позиції (для продажу), якщо її ще немає.
            if (
                product.product_catalog is not None
                and product.product_catalog.id not in self.prices
            ):
                self.prices[product.product_catalog.id] = ""
            # Ініціалізуємо поля діапазону s/n позиції (уніального ТМЦ), якщо їх ще немає.
            if (
                product.product_catalog is not None
                and product.product_catalog.uniq
                and product.product_catalog.id not in self.serial_range_from
            ):
                cid = product.product_catalog.id
                self.serial_mask[cid] = ""
                self.serial_range_from[cid] = "1"
                self.serial_range_to[cid] = "1"
                self.serial_range_hex[cid] = False
        self.close_dialog()

    @rx.event
    def on_remove_selected(self, item: int):
        if 0 <= item < len(self.items):
            removed = self.items.pop(item)
            self.split_mode.pop(removed.id, None)
            self.split_amount.pop(removed.id, None)
            self.excluded.pop(removed.id, None)

    @rx.event
    def set_split_mode_value(self, product_id: int, value: str):
        self.split_mode[product_id] = value == "split"

    @rx.event
    def set_split_amount(self, product_id: int, value: str):
        self.split_amount[product_id] = value

    @rx.event
    def set_excluded(self, product_id: int, value: bool):
        self.excluded[product_id] = value

    @staticmethod
    def _is_divisible(product: Product) -> bool:
        return product.product_catalog is not None and product.product_catalog.divisible

    def prefill_for_edit(self, items: List[Product], prices: Optional[Dict[int, float]] = None) -> None:
        """Ініціалізація віджета для РЕДАГУВАННЯ руху: крім самих `items`
        обов'язково заповнює похідні словники (режим/обсяг поділу за id одиниці,
        ціни та поля діапазону s/n за id каталогу).

        У режимі перегляду ці контроли не рендеряться, тому ніхто їх не заповнює,
        а в режимі редагування фронтенд читав би відсутні ключі Dict-Var.
        """
        self.items = items
        self.preloaded_ids = [product.id for product in items]
        for product in items:
            if self._is_divisible(product):
                self.split_mode.setdefault(product.id, False)
                self.split_amount.setdefault(product.id, "")
            self.excluded.setdefault(product.id, product.excluded_from_accounting)
            if product.product_catalog is None:
                continue
            catalog_id = product.product_catalog.id
            if catalog_id not in self.prices:
                price = (prices or {}).get(catalog_id)
                self.prices[catalog_id] = "" if price is None else str(price)
            if product.product_catalog.uniq and catalog_id not in self.serial_range_from:
                self.serial_mask[catalog_id] = ""
                self.serial_range_from[catalog_id] = "1"
                self.serial_range_to[catalog_id] = "1"
                self.serial_range_hex[catalog_id] = False

    def collect_serials(self) -> Dict[int, str]:
        """id одиниці -> s/n для унікального ТМЦ підсумкового складу."""
        return {
            product.id: (product.serial_number or "")
            for product in self.items
            if product.product_catalog is not None and product.product_catalog.uniq
        }

    def collect_excluded(
        self, final_products: Optional[List[Product]] = None
    ) -> Dict[int, bool]:
        """id одиниці -> позначка «поза обліком» для підсумкового складу.

        Без аргументу — пряма мапа за `self.excluded` (шлях РЕДАГУВАННЯ: реальний
        поділ і фінальні id одиниць невідомі до збереження в транзакції сервісу,
        тож застосування виконує окремий DAO-крок, сам ураховуючи спадкування
        позначки від батька для осколків поділу).

        З `final_products` (шлях СТВОРЕННЯ, після `resolve_movement_products`) —
        мапа за фінальними id: розділена одиниця успадковує позначку вихідної
        (позиційна відповідність `self.items[i]` -> `final_products[i]`, та сама,
        що будує `resolve_movement_products`). НЕ читаємо `id_parent` з елементів
        `final_products` напряму — серед них є detached SQLAlchemy-об'єкти зі
        `self.items`, і звернення до незавантаженого атрибута на detached
        інстансі падає `DetachedInstanceError`.
        """
        if final_products is None:
            return dict(self.excluded)
        result: Dict[int, bool] = {}
        for source, final in zip(self.items, final_products):
            result[final.id] = self.excluded.get(source.id, False)
        return result

    def collect_unit_plan(self) -> Tuple[bool, str, List[Tuple[int, Optional[float]]]]:
        """Те саме, що `resolve_movement_products`, але БЕЗ запису в БД: валідує
        серійні номери й обсяги поділу і повертає ПЛАН — (id одиниці, обсяг
        відділення або None = цілком).

        Реальний поділ виконує `MovementEditService.save_full` у межах єдиної
        транзакції: `resolve_movement_products` ділить одразу з власним commit,
        і невдале збереження лишало б у БД осколки-сироти.
        """
        flag, text = self._validate_selection()
        if not flag:
            return False, text, []
        plan: List[Tuple[int, Optional[float]]] = []
        for product in self.items:
            if self._is_divisible(product) and self.split_mode.get(product.id, False):
                plan.append((product.id, float(int(self.split_amount.get(product.id, "0")))))
            else:
                plan.append((product.id, None))
        return True, "", plan

    def _validate_selection(self) -> Tuple[bool, str]:
        """Спільна валідація складу: обов'язкові s/n і коректні обсяги поділу."""
        if self.require_serial:
            for product in self.items:
                if product.product_catalog is None or not product.product_catalog.uniq:
                    continue
                serial = product.serial_number
                if serial is None or not serial.strip():
                    return False, f"Вкажіть серійний номер для «{product.product_catalog.title}»!"

        for product in self.items:
            if not (self._is_divisible(product) and self.split_mode.get(product.id, False)):
                continue
            title = product.product_catalog.title
            raw = self.split_amount.get(product.id, "")
            try:
                amount = int(raw)
            except (TypeError, ValueError):
                return False, f"Невірний обсяг для розділення «{title}»!"
            if amount < 1 or amount >= product.count:
                return (
                    False,
                    f"Обсяг для «{title}» має бути від 1 до {format_amount(product.count - 1)} "
                    "(не можна передати всю ємність у нову одиницю)!",
                )
        return True, ""

    def resolve_movement_products(self) -> Tuple[bool, str, List[Product]]:
        """Готує підсумковий перелік одиниць товару для руху: для позицій у режимі
        «розділити» створює дочірні одиниці потрібного обсягу (батьківські зменшує).
        Спершу повністю валідує всі обсяги, лише потім вносить зміни в БД.

        Шлях СТВОРЕННЯ руху. При редагуванні використовується `collect_unit_plan`,
        який поділ не виконує — його робить сервіс усередині своєї транзакції."""
        flag, text = self._validate_selection()
        if not flag:
            return False, text, []

        # Застосування розділень.
        resolved: List[Product] = []
        for product in self.items:
            if self._is_divisible(product) and self.split_mode.get(product.id, False):
                amount = int(self.split_amount.get(product.id, "0"))
                flag, text, child = ProductDAO.split_product(product.id, amount)
                if not flag or child is None:
                    return False, text, []
                child.product_catalog = product.product_catalog
                resolved.append(child)
            else:
                resolved.append(product)
        return True, "", resolved
