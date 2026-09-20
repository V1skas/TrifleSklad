from datetime import date
from typing import List, Tuple

import reflex as rx

from TrifleSklad.dao_legacy import (
    OwnerDAO,
    ProductCatalogDAO,
    ProductCategoryDAO,
    StorageDAO,
)
from TrifleSklad.declared import StorageType, movements_status_list
from TrifleSklad.utils.clock import now_local

# Сентинел «без фільтра» для select-ів (Radix забороняє порожнє value у item).
ALL = "all"

# Скидання прокрутки тіла сторінки на початок після зміни сторінки/фільтра:
# короткий список інакше лишається за межами видимої області (scrollTop від
# попередньої, довшої сторінки). id проставлено на скролері в page_wrapper.
_SCROLL_TOP_SCRIPT = (
    "const el=document.getElementById('page-scroll-body');"
    "if(el){requestAnimationFrame(()=>{el.scrollTop=0;});}"
)


class MovementListFilterMixin(rx.State, mixin=True):
    """Спільна логіка списків руху ТМЦ: сторінкування + фільтр за датою/статусами
    + (контекстно) за складом/власником відправлення/призначення.
    Підмішується в кожен `List*State`; конкретний запит до БД виконує `_reload`,
    який реалізує клас-нащадок (різні DAO/типи)."""

    # Пагінація
    _current_page: int = 1
    _all_pages: int = 1
    _limit: int = 20

    # Чи скидались значення фільтрів у цій сесії. Скид робиться лише при першому
    # вході в розділ; повернення з детального перегляду (повторний монтаж
    # сторінки) зберігає фільтр — тільки перечитує опції й перезавантажує список.
    _filters_initialized: bool = False

    # Фільтр (карта з'являється по кнопці)
    is_filter_open: bool = False
    # Фільтр за датою вмикається перемикачем і застосовується по «Застосувати».
    filter_date_enabled: bool = False
    filter_date_from: str = ""
    filter_date_to: str = ""
    selected_statuses: List[int] = []

    # Фільтр за місцем/власником (застосовується кнопкою «Застосувати», як дата).
    # Який саме з них показувати — вирішує конкретна секція (передає у filter_card).
    filter_incoming_storage: str = ALL
    filter_destination_storage: str = ALL
    filter_incoming_owner: str = ALL
    filter_destination_owner: str = ALL

    # Фільтр за позиціями каталогу, що входять до руху (мультивибір зі списком +
    # пошуком). Спільний для всіх типів руху; застосовується по «Застосувати».
    selected_catalog_ids: List[int] = []
    catalog_filter_search: str = ""
    # Звуження списку в поповері за категорією (лише навігація, не впливає на
    # результат списку руху). ALL — усі категорії.
    catalog_filter_category: str = ALL

    # Опції селектів фільтра. list_storages — усі сховища; list_warehouses — лише
    # склади; list_sites — площадки/відділи (вибір залежить від контексту секції).
    list_storages: List[Tuple[str, str]] = []
    list_warehouses: List[Tuple[str, str]] = []
    list_sites: List[Tuple[str, str]] = []
    list_owners: List[Tuple[str, str]] = []
    # Усі позиції каталогу для мультивибору: (id, назва, одиниця, id-категорії).
    list_catalog: List[Tuple[str, str, str, str]] = []
    # Категорії для звуження поповера: (назва, id-рядок).
    list_categories: List[Tuple[str, str]] = []

    # Має реалізувати нащадок: оновлює self.items і self._all_pages за поточними
    # сторінкою/фільтрами (виклик відповідного DAO.get_paginated/...).
    def _reload(self) -> None:
        raise NotImplementedError

    # Vars
    # ======================
    @rx.var
    def get_current_page(self) -> str:
        return str(self._current_page)

    @rx.var
    def get_all_pages(self) -> str:
        return str(self._all_pages)

    @rx.var
    def has_active_filters(self) -> bool:
        return bool(
            self.filter_date_enabled
            or self.selected_statuses
            or self.selected_catalog_ids
            or self.filter_incoming_storage != ALL
            or self.filter_destination_storage != ALL
            or self.filter_incoming_owner != ALL
            or self.filter_destination_owner != ALL
        )

    @rx.var
    def statuses_for_filter(self) -> List[Tuple[int, str, bool]]:
        # (індекс статусу, назва, чи обраний)
        return [
            (index, name, index in self.selected_statuses)
            for index, name in enumerate(movements_status_list)
        ]

    @rx.var
    def catalog_filter_count(self) -> int:
        return len(self.selected_catalog_ids)

    @rx.var
    def catalog_options_for_filter(self) -> List[Tuple[str, str, bool]]:
        # (id-рядок, «назва (одиниця)», чи обраний). Пошук — підрядок у назві,
        # плюс звуження за категорією; обрані спливають наверх, далі — за алфавітом.
        query = self.catalog_filter_search.lower()
        category = self.catalog_filter_category
        selected = set(self.selected_catalog_ids)
        rows: List[Tuple[str, str, bool]] = []
        for id_str, title, unit, category_id in self.list_catalog:
            if query and query not in title.lower():
                continue
            if category != ALL and category_id != category:
                continue
            label = f"{title} ({unit})" if unit else title
            rows.append((id_str, label, int(id_str) in selected))
        rows.sort(key=lambda row: (not row[2], row[1].lower()))
        return rows
    # ======================

    # Backend only
    # ======================
    def _date_from_eff(self) -> str:
        # Дата застосовується лише коли перемикач увімкнено.
        return self.filter_date_from if self.filter_date_enabled else ""

    def _date_to_eff(self) -> str:
        return self.filter_date_to if self.filter_date_enabled else ""

    def _load_filter_options(self) -> None:
        storages = StorageDAO.get_all()
        self.list_storages = [(s.title, str(s.id)) for s in storages]
        self.list_warehouses = [
            (s.title, str(s.id)) for s in storages if s.type == StorageType.WAREHOUSE
        ]
        self.list_sites = [
            (s.title, str(s.id))
            for s in storages
            if s.type in (StorageType.TECHNICAL_SITE, StorageType.DEPARTMENT)
        ]
        self.list_owners = [(o.title, str(o.id)) for o in OwnerDAO.get_all()]
        self.list_catalog = [
            (
                str(p.id),
                p.title,
                p.unit,
                str(p.id_category) if p.id_category is not None else "",
            )
            for p in ProductCatalogDAO.get_all()
        ]
        self.list_categories = [
            (c.title, str(c.id)) for c in ProductCategoryDAO.get_all()
        ]

    def _load_section_filter_options(self) -> None:
        """Опції секційних фільтрів (переозначає підклас, напр. list_suppliers)."""

    def _reset_section_filter_values(self) -> None:
        """Скидання значень секційних фільтрів до дефолтів (переозначає підклас)."""

    def _reset_filter_values(self) -> None:
        """Скидання ЗНАЧЕНЬ базових фільтрів до дефолтів. Не чіпає is_filter_open
        (кнопка «Скинути» лишає картку відкритою) — це робить _enter_list."""
        today = now_local().date().isoformat()
        self._current_page = 1
        self.filter_date_enabled = False
        # Дати за замовчуванням — сьогодні (видимі й у state), щоб фільтр спрацював
        # одразу після увімкнення перемикача, навіть якщо дату не чіпали.
        self.filter_date_from = today
        self.filter_date_to = today
        self.selected_statuses = []
        self.selected_catalog_ids = []
        self.catalog_filter_search = ""
        self.catalog_filter_category = ALL
        self.filter_incoming_storage = ALL
        self.filter_destination_storage = ALL
        self.filter_incoming_owner = ALL
        self.filter_destination_owner = ALL

    def _enter_list(self) -> None:
        """Викликати в on_load кожного списку. Опції довідників перечитуються
        завжди (щоб підхопити нові записи), а значення фільтрів скидаються лише
        при ПЕРШОМУ вході в розділ у межах сесії — повернення з детального
        перегляду (повторний монтаж) зберігає фільтр."""
        self._load_filter_options()
        self._load_section_filter_options()
        if not self._filters_initialized:
            self._filters_initialized = True
            self.is_filter_open = False
            self._reset_filter_values()
            self._reset_section_filter_values()
    # ======================

    # Event handlers
    # ======================
    @rx.event
    def toggle_filter(self):
        self.is_filter_open = not self.is_filter_open

    def _apply_filters(self):
        """Застосувати фільтри одразу (окремої кнопки «Застосувати» немає):
        на 1-у сторінку, перезавантажити список, прокрутка вгору."""
        self._current_page = 1
        self._reload()
        return rx.call_script(_SCROLL_TOP_SCRIPT)

    @rx.event
    def on_change_filter_date_enabled(self, value: bool):
        self.filter_date_enabled = value
        return self._apply_filters()

    @rx.event
    def on_change_filter_date_from(self, value: str):
        self.filter_date_from = value
        return self._apply_filters()

    @rx.event
    def on_change_filter_date_to(self, value: str):
        self.filter_date_to = value
        return self._apply_filters()

    @rx.event
    def set_status(self, index: int, checked: bool):
        if checked and index not in self.selected_statuses:
            self.selected_statuses = self.selected_statuses + [index]
        elif not checked and index in self.selected_statuses:
            self.selected_statuses = [s for s in self.selected_statuses if s != index]
        return self._apply_filters()

    @rx.event
    def set_catalog_search(self, value: str):
        # Звужує лише перелік у поповері; список руху не перезавантажує.
        self.catalog_filter_search = value

    @rx.event
    def set_catalog_category(self, value: str):
        # Звужує лише перелік у поповері; список руху не перезавантажує.
        self.catalog_filter_category = value

    @rx.event
    def toggle_catalog(self, id_str: str):
        # Клік по позиції каталогу — додати/зняти галочку; обрана позиція одразу
        # спливає наверх і список руху одразу перезавантажується.
        cid = int(id_str)
        if cid in self.selected_catalog_ids:
            self.selected_catalog_ids = [x for x in self.selected_catalog_ids if x != cid]
        else:
            self.selected_catalog_ids = self.selected_catalog_ids + [cid]
        return self._apply_filters()

    @rx.event
    def on_change_filter_incoming_storage(self, value: str):
        self.filter_incoming_storage = value
        return self._apply_filters()

    @rx.event
    def on_change_filter_destination_storage(self, value: str):
        self.filter_destination_storage = value
        return self._apply_filters()

    @rx.event
    def on_change_filter_incoming_owner(self, value: str):
        self.filter_incoming_owner = value
        return self._apply_filters()

    @rx.event
    def on_change_filter_destination_owner(self, value: str):
        self.filter_destination_owner = value
        return self._apply_filters()

    @rx.event
    def reset_filters(self):
        # Значення секційних фільтрів скидає хук (переозначений у підкласах);
        # is_filter_open не чіпаємо — картка лишається відкритою.
        self._reset_filter_values()
        self._reset_section_filter_values()
        self._reload()
        return rx.call_script(_SCROLL_TOP_SCRIPT)

    @rx.event
    def current_page_increment(self):
        if self._current_page + 1 <= self._all_pages:
            self._current_page += 1
            self._reload()
            return rx.call_script(_SCROLL_TOP_SCRIPT)

    @rx.event
    def current_page_decrement(self):
        if self._current_page > 1:
            self._current_page -= 1
            self._reload()
            return rx.call_script(_SCROLL_TOP_SCRIPT)

    @rx.event
    def on_change_current_page(self, value: str):
        if value != "" and value.isdigit() and 0 < int(value) <= self._all_pages:
            self._current_page = int(value)
            self._reload()
            return rx.call_script(_SCROLL_TOP_SCRIPT)
    # ======================
