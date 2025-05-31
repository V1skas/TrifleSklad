import reflex as rx

from typing import List, Tuple, Optional

import TrifleSklad.routes as routes
from TrifleSklad.models import Storage, Worker
from TrifleSklad.dao import StorageDAO, WorkerDAO

class StorageState(rx.State):
    class Pages:
        ADD = 'add'
        EDIT = 'edit'
        VIEW = 'view'
        LIST = 'list'

    current_page: str = Pages.LIST

    items: List[Storage] = []
    selected_item: int = -1

    def _check_path(self):
        page = self.router.page.params.get('page', '')
        if page != '':
            id = -1
            if page not in [self.Pages.ADD, self.Pages.EDIT, self.Pages.VIEW]:
                return rx.redirect(routes.CATALOG_STORAGES)

            # /storages/add
            if page == self.Pages.ADD:
                id = Storage()
            # /storages/edit/[id]
            elif page == self.Pages.EDIT:
                id = self.router.page.params.get('id', '')
                if id != '':
                    id = StorageDAO.get_by_id_with_relationships(id)
                    if id is None:
                        return [rx.redirect(routes.CATALOG_STORAGES), rx.toast.error("Запись не была найдена")]
                else:
                    return rx.redirect(routes.CATALOG_STORAGES)
            # /storages/view/[id]
            elif page == self.Pages.VIEW:
                id = self.router.page.params.get('id', '')
                if id != '':
                    id = StorageDAO.get_by_id_with_relationships(id)
                    if id is None:
                        return [rx.redirect(routes.CATALOG_STORAGES), rx.toast.error("Запись не была найдена")]
                else:
                    return rx.redirect(routes.CATALOG_STORAGES)

            self.items = []
            self.items.append(id)  # type: ignore
            self.selected_item = 0
            self.current_page = page
        else:
            # /storages
            self.selected_item = -1
            self.current_page = self.Pages.LIST
            self.items = StorageDAO.get_all_with_relationships()

    @rx.var
    def has_items(self) -> bool:
        return len(self.items) > 0

    @rx.var
    def get_items(self) -> List[Tuple[int, Storage]]:
        return [(index, item) for index, item in enumerate(self.items)]

    @rx.var
    def has_selected_item(self) -> bool:
        return self.selected_item != -1

    @rx.var
    def get_selected_item(self) -> Tuple[int, Storage]:
        if self.selected_item != -1:
            return (self.selected_item, self.items[self.selected_item])
        return (-1, Storage())

    @rx.event
    def on_load(self):
        self._check_path()

    @rx.event
    def add_one(self, form_data: dict):
        if "id_responsible" in form_data and form_data["id_responsible"]:
            worker: Optional[Worker] = WorkerDAO.get_by_fio(form_data["id_responsible"])
            if worker is None:
                return rx.toast.error("Ответственный не найден")
            
            form_data["id_responsible"] = worker.id
            form_data["worker"] = worker
        else:
            return rx.toast.error("Не указан ответственный")
        
        flag, text, id = StorageDAO.add_one(form_data)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_STORAGES_VIEW_ID}{id}")]
        return rx.toast.error(text)

    @rx.event
    def edit_one(self, form_data: dict):
        form_data["id"] = self.items[self.selected_item].id

        if "id_responsible" in form_data and form_data["id_responsible"]:
            worker: Optional[Worker] = WorkerDAO.get_by_fio(form_data["id_responsible"])
            if worker is None:
                return rx.toast.error("Ответственный не найден")
            
            form_data["id_responsible"] = worker.id
            form_data["worker"] = worker
        else:
            return rx.toast.error("Не указан ответственный")

        flag, text, id = StorageDAO.edit_one(form_data)
        if flag:
            return [rx.toast.success(text), rx.redirect(f"{routes.CATALOG_STORAGES_VIEW_ID}{id}")]
        return rx.toast.error(text)

    @rx.event
    def delete_one(self):
        if self.selected_item != -1:
            flag, text = StorageDAO.delete_one(self.items[self.selected_item].id)
            if flag:
                return [rx.toast.success(text), rx.redirect(routes.CATALOG_STORAGES)]
            else:
                return [rx.toast.error(text)]
        return rx.toast.error("Не выбрана запись для удаления")