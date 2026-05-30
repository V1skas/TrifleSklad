import reflex as rx

from typing import List, Tuple, Optional, Dict

from TrifleSklad import declared

import TrifleSklad.routes as routes
from TrifleSklad.state import AppState
from TrifleSklad.actions import Action as ActionEnum

from TrifleSklad.models import Storage, Worker
from TrifleSklad.dao import StorageDAO, WorkerDAO


class ViewStorageState(rx.State):
    item: Optional[Storage] = None
    app_state: Optional[AppState] = None

    def _load_item(self, id: int):
        self.item = StorageDAO.get_by_id_with_relationships(id)

    # Vars
    # ====
    @rx.var
    def storage_type(self) -> str:
        return declared.storage_type_list[self.item.type] if self.item is not None and self.item.type is not None else ""
    
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
        return self.item.responsible.fio if self.item is not None and self.item.responsible is not None else "None"    
    # ====

    # Action handlers
    # ===============
    @rx.event
    async def on_load(self, id: int):
        self._load_item(id)
        if self.item is None:
            return [
                rx.redirect(routes.CATALOG_STORAGES),
                rx.toast.error("Запис не знайдено!")
            ]
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
    # ===============


class AddStorageState(rx.State):
    item: Optional[Storage] = None
    app_state: Optional[AppState] = None
    list_workers: List[Tuple[str, str]] = []

    def _reset_item(self):
        self.item: Storage = Storage()

    def _load_workers(self):
        self.list_workers = [(str(item.id), item.fio) for item in WorkerDAO.get_all()]

    # Vars
    # ====
    @rx.var
    def storage_type(self) -> str:
        return declared.storage_type_list[self.item.type] if self.item is not None and self.item.type is not None else ""
    
    @rx.var
    def storage_type_id(self) -> str:
        return str(self.item.type) if self.item is not None and self.item.type is not None else "-1"
    
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
        return self.item.responsible.fio if self.item is not None and self.item.responsible is not None else "None"

    @rx.var
    def id_responsible(self) -> str:
        return str(self.item.id_responsible) if self.item is not None and self.item.id_responsible is not None else "-1"  
    # ====

    # Action handlers
    # ===============
    @rx.event
    async def on_load(self):
        self._reset_item()
        self._load_workers()
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)

    @rx.event
    def on_change_type(self, st_type: str):
        if st_type.isdigit():
            t = int(st_type)
            self.item.type = t if 0 < t < len(declared.storage_type_list) + 1 else None
        else:
            self.item.type = None

    @rx.event
    def on_change_title(self, title: str):
        self.item.title = title if title != "" else None

    @rx.event
    def on_change_description(self, description: str):
        self.item.description = description if description != "" else None

    @rx.event
    def on_change_address(self, address: str):
        self.item.address = address if address != "" else None

    @rx.event
    def on_change_responsible(self, id_responsible: str):
        if id_responsible.isdigit():
            self.item.id_responsible = int(id_responsible)

    @rx.event
    def add_one(self):
        if not self.app_state.has_permission(ActionEnum.STORAGE_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        
        if self.item.type is None or self.item.title is None:
            return rx.toast.error("Обов'язкові поля повинні бути заповнені!")
        
        if self.item.id_responsible not in [int(item[0]) for item in self.list_workers]:
            return rx.toast.error("Відповідальний вказаний некоректно!")
        
        flag, text, id = StorageDAO.add_one(self.item)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_STORAGES_VIEW_ID}{id}")]
        return rx.toast.error(text)
    # ===============


class EditStorageState(rx.State):
    item: Optional[Storage] = None
    app_state: Optional[AppState] = None
    list_workers: List[Tuple[str, str]] = []

    def _load_item(self, id: int):
        self.item = StorageDAO.get_by_id_with_relationships(id)

    def _load_workers(self):
        self.list_workers = [(str(item.id), item.fio) for item in WorkerDAO.get_all()]

    # Vars
    # ====
    @rx.var
    def storage_type(self) -> str:
        return declared.storage_type_list[self.item.type] if self.item is not None and self.item.type is not None else ""
    
    @rx.var
    def storage_type_id(self) -> str:
        return str(self.item.type) if self.item is not None and self.item.type is not None else "-1"
    
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
        return self.item.responsible.fio if self.item is not None and self.item.responsible is not None else "None" 

    @rx.var
    def id_responsible(self) -> str:
        return str(self.item.id_responsible) if self.item is not None and self.item.id_responsible is not None else "-1"   
    # ====

    # Action handlers
    # ===============
    @rx.event
    async def on_load(self, id: int):
        self._load_item(id)
        if self.item is None:
            return [
                rx.redirect(routes.CATALOG_STORAGES),
                rx.toast.error("Запис не знайдено!")
            ]
        self._load_workers()
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)

    @rx.event
    def on_change_type(self, st_type: str):
        if st_type.isdigit():
            t = int(st_type)
            self.item.type = t if 0 < t < len(declared.storage_type_list) + 1 else None
        else:
            self.item.type = None

    @rx.event
    def on_change_title(self, title: str):
        self.item.title = title if title != "" else None

    @rx.event
    def on_change_description(self, description: str):
        self.item.description = description if description != "" else None

    @rx.event
    def on_change_address(self, address: str):
        self.item.address = address if address != "" else None

    @rx.event
    def on_change_responsible(self, id_responsible: str):
        if id_responsible.isdigit():
            self.item.id_responsible = int(id_responsible)

    @rx.event
    def edit_one(self):
        if not self.app_state.has_permission(ActionEnum.STORAGE_EDIT):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")

        if self.item.type is None or self.item.title is None:
            return rx.toast.error("Обов'язкові поля повинні бути заповнені!")

        if self.item.id_responsible not in [int(item[0]) for item in self.list_workers]:
            return rx.toast.error("Відповідальний вказаний некоректно!")
        
        flag, text, id = StorageDAO.edit_one(self.item)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_STORAGES_VIEW_ID}{id}")]
        return rx.toast.error(text)
    # ===============


class ListStorageState(rx.State):
    items: List[Storage] = []

    # Frontend vars
    # =============
    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0
    # =============

    # Action handlers
    # ===============
    @rx.event
    def on_load(self):
        self.items = StorageDAO.get_all_with_relationships()
    # ===============


class StorageState(rx.State):
    class Pages:
        ADD = 'add'
        EDIT = 'edit'
        VIEW = 'view'
        LIST = 'list'

    current_page: str = Pages.LIST
    app_state: Optional[AppState] = None

    @rx.var
    def get_titles_type_storages_list(self) -> List[str]:
        return list(declared.storage_type_list.values())

    @rx.var
    def get_titles_type_storages_dict(self) -> List[Tuple[str, str]]:
        return [(str(key), value) for key, value in declared.storage_type_list.items()]
    
    @rx.var
    def get_titles_type_storages_dict_as_dict(self) -> Dict[str, str]:
        return declared.storage_type_list

    def _check_path(self):
        page = self.router.page.params.get('page', '')
        if page != '':
            id = -1
            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                yield rx.redirect(routes.CATALOG_STORAGES)
                return

            # /storages/add
            if page == self.Pages.ADD:
                if not self.app_state.has_permission(ActionEnum.STORAGE_CREATE):
                    yield rx.redirect(routes.WELCOME)
                    return
                yield AddStorageState.on_load()
            # /storages/edit/[id]
            elif page == self.Pages.EDIT:
                if not self.app_state.has_permission(ActionEnum.STORAGE_EDIT):
                    yield rx.redirect(routes.WELCOME)
                    return

                id = self.router.page.params.get('id', '')
                if id != '':
                    yield EditStorageState.on_load(id)
                else:
                    yield rx.redirect(routes.CATALOG_STORAGES)
                    return
            # /storages/view/[id]
            elif page == self.Pages.VIEW:
                if not self.app_state.has_permission(ActionEnum.STORAGE_VIEW):
                    yield rx.redirect(routes.WELCOME)
                    return

                id = self.router.page.params.get('id', '')
                if id != '':
                    yield ViewStorageState.on_load(id)
                else:
                    yield rx.redirect(routes.CATALOG_STORAGES)
                    return

            self.current_page = page
        else:
            # /storages
            if not self.app_state.has_permission(ActionEnum.STORAGE_LIST):
                yield rx.redirect(routes.WELCOME)
                return
            yield ListStorageState.on_load()
            self.current_page = self.Pages.LIST

    @rx.event
    async def on_load(self):
        if self.app_state is None:
            self.app_state = await self.get_state(AppState)
        return self._check_path()

    @rx.event
    def delete_one(self, id: int):
        if id > -1:
            if not self.app_state.has_permission(ActionEnum.STORAGE_DELETE):
                return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
            flag, text = StorageDAO.delete_one(id)
            if flag:
                return [rx.toast.success(text), rx.redirect(routes.CATALOG_STORAGES)]
            else:
                return [rx.toast.error(text)]
        return rx.toast.error("Не обрано запис для видалення!")