from typing import List, Optional, Sequence, Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.dao_legacy import WorkerDAO
from TrifleSklad.declared import StorageType, storage_type_list
from TrifleSklad.models import Storage

# «Об'єкти підприємства» — усі типи місць зберігання, крім клієнтів: клієнти
# відображаються в окремому розділі «Клієнти» (states/client.py, TS-56), хоча
# під капотом лишаються тим самим Storage з type == CLIENT.
_NON_CLIENT_STORAGE_TYPES = [t for t in storage_type_list if t != StorageType.CLIENT]
from TrifleSklad.services.errors import ServiceError
from TrifleSklad.services.storage import StorageService
from TrifleSklad.states.app import AppState
from TrifleSklad.states.audit_mixin import AuditHistoryMixin
from TrifleSklad.states.list_filter_mixin import SearchFilterMixin


class ListStorageState(SearchFilterMixin, AppState):
    items: Optional[Sequence[Storage]] = None
    in_progress: bool = True

    filter_title: str = ""
    filter_address: str = ""
    filter_type: str = "all"

    @rx.var
    def filtered_items(self) -> List[Storage]:
        if self.items is None:
            return []
        title = self.filter_title.strip().lower()
        address = self.filter_address.strip().lower()
        result = []
        for s in self.items:
            if title and title not in (s.title or "").lower():
                continue
            if address and address not in (s.address or "").lower():
                continue
            if self.filter_type != "all" and str(s.type) != self.filter_type:
                continue
            result.append(s)
        return result

    @rx.var
    def has_items(self) -> bool:
        return len(self.filtered_items) > 0

    @rx.var
    def storage_type_options(self) -> List[Tuple[str, str]]:
        return [(storage_type_list[t], str(t)) for t in _NON_CLIENT_STORAGE_TYPES]

    @rx.var
    def has_active_filters(self) -> bool:
        return bool(self.filter_title.strip() or self.filter_address.strip() or self.filter_type != "all")

    @rx.event
    def on_load(self):
        if not self.has_permission(Action.STORAGE_LIST):
            yield rx.redirect(routes.WELCOME)
            yield rx.toast.error("У Вас немає дозволу на перегляд цієї сторінки!")
            return
        try:
            self.in_progress = True
            self.filter_title = ""
            self.filter_address = ""
            self.filter_type = "all"
            self.is_filter_open = False
            self.items = StorageService().get_list_items(type_in=_NON_CLIENT_STORAGE_TYPES)
            self.in_progress = False
        except Exception:
            yield rx.toast.error("Під час виконання запиту сталася помилка. Спробуйте знову.")

    @rx.event
    def set_filter_title(self, value: str):
        self.filter_title = value

    @rx.event
    def set_filter_address(self, value: str):
        self.filter_address = value

    @rx.event
    def set_filter_type(self, value: str):
        self.filter_type = value

    @rx.event
    def on_click_add(self):
        return rx.redirect(routes.CATALOG_STORAGES_ADD)


class AddStorageState(AppState):
    item: Storage = Storage()
    in_process: bool = False
    list_workers: List[Tuple[str, str]] = []

    @rx.event
    def on_load(self):
        if not self.has_permission(Action.STORAGE_CREATE):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        self.item = Storage()
        self.list_workers = [(str(w.id), w.fio) for w in WorkerDAO.get_all()]

    @rx.var
    def storage_type_id(self) -> str:
        return str(self.item.type) if self.item is not None and self.item.type is not None else ""

    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""

    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""

    @rx.var
    def address(self) -> str:
        return self.item.address if self.item is not None and self.item.address is not None else ""

    @rx.var
    def id_responsible(self) -> str:
        return str(self.item.id_responsible) if self.item is not None and self.item.id_responsible is not None else ""

    @rx.var
    def is_default(self) -> bool:
        return bool(self.item.is_default) if self.item is not None else False

    @rx.event
    def set_storage_type_id(self, value: str):
        self.item.type = int(value) if value.isdigit() else None

    @rx.event
    def set_title(self, value: str):
        self.item.title = value

    @rx.event
    def set_description(self, value: str):
        self.item.description = value if value != "" else None

    @rx.event
    def set_address(self, value: str):
        self.item.address = value if value != "" else None

    @rx.event
    def set_id_responsible(self, value: str):
        self.item.id_responsible = int(value) if value.isdigit() else None

    @rx.event
    def set_is_default(self, value: bool):
        self.item.is_default = value

    @rx.event
    def on_save(self):
        if not self.has_permission(Action.STORAGE_CREATE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if not self.item.title:
            yield rx.toast.warning("Вкажіть назву!")
            return
        if self.item.type is None:
            yield rx.toast.warning("Оберіть тип!")
            return
        if self.item.id_responsible not in [int(w[0]) for w in self.list_workers]:
            yield rx.toast.warning("Відповідальний вказаний некоректно!")
            return
        try:
            self.item = StorageService().add_one(self.item, self.user.login)
            yield rx.toast.success("Склад успішно додано!")
            yield rx.redirect(routes.CATALOG_STORAGES_VIEW_ID + str(self.item.id), replace=True)
        except ServiceError as e:
            yield rx.toast.warning(str(e))
        except Exception:
            yield rx.toast.error("Під час виконання запиту трапилась помилка. Спробуйте ще раз.")


class EditStorageState(AppState):
    item: Storage = Storage()
    in_process: bool = False
    list_workers: List[Tuple[str, str]] = []

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(Action.STORAGE_EDIT):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        try:
            self.in_process = True
            item = StorageService().get_by_id(int(id))
            if item is None or item.type == StorageType.CLIENT:
                self.in_process = False
                yield rx.redirect(routes.CATALOG_STORAGES)
                yield rx.toast.error("Запис не було знайдено")
                return
            self.item = item
            self.list_workers = [(str(w.id), w.fio) for w in WorkerDAO.get_all()]
            self.in_process = False
        except Exception:
            self.in_process = False
            yield rx.toast.error("Під час виконання запиту сталася помилка. Спробуйте знову.")

    @rx.var
    def storage_type_id(self) -> str:
        return str(self.item.type) if self.item is not None and self.item.type is not None else ""

    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""

    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""

    @rx.var
    def address(self) -> str:
        return self.item.address if self.item is not None and self.item.address is not None else ""

    @rx.var
    def id_responsible(self) -> str:
        return str(self.item.id_responsible) if self.item is not None and self.item.id_responsible is not None else ""

    @rx.var
    def is_default(self) -> bool:
        return bool(self.item.is_default) if self.item is not None else False

    @rx.event
    def set_storage_type_id(self, value: str):
        self.item.type = int(value) if value.isdigit() else None

    @rx.event
    def set_title(self, value: str):
        self.item.title = value

    @rx.event
    def set_description(self, value: str):
        self.item.description = value if value != "" else None

    @rx.event
    def set_address(self, value: str):
        self.item.address = value if value != "" else None

    @rx.event
    def set_id_responsible(self, value: str):
        self.item.id_responsible = int(value) if value.isdigit() else None

    @rx.event
    def set_is_default(self, value: bool):
        self.item.is_default = value

    @rx.event
    def on_save(self):
        if not self.has_permission(Action.STORAGE_EDIT):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if not self.item.title:
            yield rx.toast.warning("Вкажіть назву!")
            return
        if self.item.type is None:
            yield rx.toast.warning("Оберіть тип!")
            return
        if self.item.id_responsible not in [int(w[0]) for w in self.list_workers]:
            yield rx.toast.warning("Відповідальний вказаний некоректно!")
            return
        try:
            self.item = StorageService().edit_one(self.item, self.user.login)
            yield rx.toast.success("Склад успішно змінено!")
            yield rx.redirect(routes.CATALOG_STORAGES_VIEW_ID + str(self.item.id), replace=True)
        except ServiceError as e:
            yield rx.toast.warning(str(e))
        except Exception:
            yield rx.toast.error("Під час виконання запиту трапилась помилка. Спробуйте ще раз.")


class ViewStorageState(AuditHistoryMixin, AppState):
    HISTORY_TABLE = "storage"
    HISTORY_ACTION = Action.STORAGE_HISTORY
    HISTORY_DETAIL_ACTION = Action.STORAGE_HISTORY_DETAIL

    item: Optional[Storage] = None
    in_process: bool = True

    @rx.var
    def storage_type(self) -> str:
        return storage_type_list[self.item.type] if self.item is not None and self.item.type is not None else ""

    @rx.var
    def title(self) -> str:
        return self.item.title if self.item is not None and self.item.title is not None else ""

    @rx.var
    def description(self) -> str:
        return self.item.description if self.item is not None and self.item.description is not None else ""

    @rx.var
    def address(self) -> str:
        return self.item.address if self.item is not None and self.item.address is not None else ""

    @rx.var
    def responsible(self) -> str:
        return self.item.responsible.fio if self.item is not None and self.item.responsible is not None else ""

    @rx.var
    def is_default(self) -> bool:
        return bool(self.item.is_default) if self.item is not None else False

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        if not self.has_permission(Action.STORAGE_VIEW):
            yield rx.toast.error("У Вас немає доступу до цієї сторінки!")
            yield rx.redirect(routes.WELCOME)
            return
        try:
            self.in_process = True
            self.item = StorageService().get_by_id(int(id))
            self.in_process = False
            if self.item is None or self.item.type == StorageType.CLIENT:
                yield rx.redirect(routes.CATALOG_STORAGES)
                yield rx.toast.error("Запис не було знайдено")
                return
            self._load_history(self.item.id)
        except Exception:
            self.in_process = False
            yield rx.toast.error("Під час виконання запиту сталася помилка. Спробуйте знову.")

    @rx.event
    def on_click_edit(self):
        if self.item is None:
            return
        return rx.redirect(routes.CATALOG_STORAGES_EDIT_ID + str(self.item.id))

    @rx.event
    def on_click_delete(self):
        if not self.has_permission(Action.STORAGE_DELETE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None:
            return
        try:
            if StorageService().delete_one(self.item.id, self.user.login):
                yield rx.toast.success("Склад видалено!")
                yield ListStorageState.on_load()
                yield rx.redirect(routes.CATALOG_STORAGES)
            else:
                yield rx.toast.error("Помилка! Склад не знайдено.")
        except ServiceError as e:
            yield rx.toast.warning(str(e))
