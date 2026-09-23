from typing import List, Optional, Sequence, Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.actions import Action
from TrifleSklad.dao_legacy import WorkerDAO
from TrifleSklad.declared import StorageType
from TrifleSklad.models import Storage
from TrifleSklad.services.errors import ServiceError
from TrifleSklad.services.storage import StorageService
from TrifleSklad.states.app import AppState
from TrifleSklad.states.audit_mixin import AuditHistoryMixin
from TrifleSklad.states.list_filter_mixin import SearchFilterMixin

# Клієнти під капотом лишаються тими самими Storage з type == CLIENT
# (TS-56) — окремий розділ каталогу для користувача, той самий шар даних
# і той самий аудит (`table_name == "storage"`), що й «Об'єкти підприємства».


class ListClientState(SearchFilterMixin, AppState):
    items: Optional[Sequence[Storage]] = None
    in_progress: bool = True

    filter_title: str = ""
    filter_address: str = ""

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
            result.append(s)
        return result

    @rx.var
    def has_items(self) -> bool:
        return len(self.filtered_items) > 0

    @rx.var
    def has_active_filters(self) -> bool:
        return bool(self.filter_title.strip() or self.filter_address.strip())

    @rx.event
    def on_load(self):
        guard = self.access_guard(Action.CLIENT_LIST)
        if guard is not None:
            yield guard
            return
        try:
            self.in_progress = True
            self.filter_title = ""
            self.filter_address = ""
            self.is_filter_open = False
            self.items = StorageService().get_list_items(type_in=[StorageType.CLIENT])
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
    def on_click_add(self):
        return rx.redirect(routes.CATALOG_CLIENTS_ADD)


class AddClientState(AppState):
    item: Storage = Storage()
    in_process: bool = False
    list_workers: List[Tuple[str, str]] = []

    @rx.event
    def on_load(self):
        guard = self.access_guard(Action.CLIENT_CREATE)
        if guard is not None:
            yield guard
            return
        self.item = Storage(type=StorageType.CLIENT)
        self.list_workers = [(str(w.id), w.fio) for w in WorkerDAO.get_all()]

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
        if not self.has_permission(Action.CLIENT_CREATE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if not self.item.title:
            yield rx.toast.warning("Вкажіть назву!")
            return
        self.item.type = StorageType.CLIENT
        if self.item.id_responsible not in [int(w[0]) for w in self.list_workers]:
            yield rx.toast.warning("Відповідальний вказаний некоректно!")
            return
        try:
            self.item = StorageService().add_one(self.item, self.user.login)
            yield rx.toast.success("Клієнта успішно додано!")
            yield rx.redirect(routes.CATALOG_CLIENTS_VIEW_ID + str(self.item.id), replace=True)
        except ServiceError as e:
            yield rx.toast.warning(str(e))
        except Exception:
            yield rx.toast.error("Під час виконання запиту трапилась помилка. Спробуйте ще раз.")


class EditClientState(AppState):
    item: Storage = Storage()
    in_process: bool = False
    list_workers: List[Tuple[str, str]] = []

    @rx.event
    def on_load(self, id: str = ""):
        id = id or self._route_param("id", "")
        guard = self.access_guard(Action.CLIENT_EDIT)
        if guard is not None:
            yield guard
            return
        try:
            self.in_process = True
            item = StorageService().get_by_id(int(id))
            if item is None or item.type != StorageType.CLIENT:
                self.in_process = False
                yield rx.redirect(routes.CATALOG_CLIENTS)
                yield rx.toast.error("Запис не було знайдено")
                return
            self.item = item
            self.list_workers = [(str(w.id), w.fio) for w in WorkerDAO.get_all()]
            self.in_process = False
        except Exception:
            self.in_process = False
            yield rx.toast.error("Під час виконання запиту сталася помилка. Спробуйте знову.")

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
        if not self.has_permission(Action.CLIENT_EDIT):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if not self.item.title:
            yield rx.toast.warning("Вкажіть назву!")
            return
        self.item.type = StorageType.CLIENT
        if self.item.id_responsible not in [int(w[0]) for w in self.list_workers]:
            yield rx.toast.warning("Відповідальний вказаний некоректно!")
            return
        try:
            self.item = StorageService().edit_one(self.item, self.user.login)
            yield rx.toast.success("Клієнта успішно змінено!")
            yield rx.redirect(routes.CATALOG_CLIENTS_VIEW_ID + str(self.item.id), replace=True)
        except ServiceError as e:
            yield rx.toast.warning(str(e))
        except Exception:
            yield rx.toast.error("Під час виконання запиту трапилась помилка. Спробуйте ще раз.")


class ViewClientState(AuditHistoryMixin, AppState):
    HISTORY_TABLE = "storage"
    HISTORY_ACTION = Action.CLIENT_HISTORY
    HISTORY_DETAIL_ACTION = Action.CLIENT_HISTORY_DETAIL

    item: Optional[Storage] = None
    in_process: bool = True

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
        guard = self.access_guard(Action.CLIENT_VIEW)
        if guard is not None:
            yield guard
            return
        try:
            self.in_process = True
            self.item = StorageService().get_by_id(int(id))
            self.in_process = False
            if self.item is None or self.item.type != StorageType.CLIENT:
                yield rx.redirect(routes.CATALOG_CLIENTS)
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
        return rx.redirect(routes.CATALOG_CLIENTS_EDIT_ID + str(self.item.id))

    @rx.event
    def on_click_delete(self):
        if not self.has_permission(Action.CLIENT_DELETE):
            yield rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            return
        if self.item is None:
            return
        try:
            if StorageService().delete_one(self.item.id, self.user.login):
                yield rx.toast.success("Клієнта видалено!")
                yield ListClientState.on_load()
                yield rx.redirect(routes.CATALOG_CLIENTS)
            else:
                yield rx.toast.error("Помилка! Клієнта не знайдено.")
        except ServiceError as e:
            yield rx.toast.warning(str(e))
