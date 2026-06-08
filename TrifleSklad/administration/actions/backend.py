import reflex as rx

from typing import List, Tuple, Optional

from TrifleSklad.models import Action
from TrifleSklad.dao import ActionDAO

class ActionsState(rx.State):
    items: List[Action] = []
    unselected_items: List[int] = []
    selected_items: List[int] = []
    unselected_items_filtered: List[int] = []
    selected_items_filtered: List[int] = []
    filter: str = ""

    def _load_items(self) -> None:
        self.items = ActionDAO.get_all()
        self.unselected_items = [i for i in range(len(self.items))]
        self.selected_items = []
        self.filter = ""

    def _set_selected_items(self, items: List[Action]) -> None:
        self.selected_items = [i for i in range(len(self.items)) if self.items[i] in items]
        self.unselected_items = [i for i in range(len(self.items)) if self.items[i] not in items]
        self.set_filter("")

    def _get_selected_items(self) -> List[Action]:
        return [self.items[index] for index in self.selected_items]

    @rx.var
    def get_id_selected_items(self) -> List[int]:
        return [self.items[index].id for index in reversed(self.selected_items)] if len(self.selected_items) > 0 else []

    @rx.var
    def get_selected_items(self) -> List[Tuple[int, Action]]:
        if self.filter != "":
            return [(index, self.items[index]) for index in reversed(self.selected_items_filtered)]
        else:
            return [(index, self.items[index]) for index in reversed(self.selected_items)]
    
    @rx.var
    def get_unselected_items(self) -> List[Tuple[int, Action]]:
        if self.filter != "":
            return [(index, self.items[index]) for index in reversed(self.unselected_items_filtered)]
        else:
            return [(index, self.items[index]) for index in self.unselected_items]
    
    @rx.event
    def on_load(self, selected_items: List[Action]) -> None:
        self._load_items()
        self._set_selected_items(selected_items)
        self.set_filter("")
    
    @rx.event
    def select_item(self, item: int) -> None:
        if item in self.selected_items:
            self.unselected_items.append(item)
            self.unselected_items.sort()
            self.selected_items.remove(item)
        else:
            self.selected_items.append(item)
            self.unselected_items.remove(item)
        self.set_filter(self.filter)

    @rx.event
    def set_filter(self, filter: str) -> None:
        self.filter = filter
        self.unselected_items_filtered = [i for i in self.unselected_items if self.items[i].title.lower().find(filter.lower()) != -1]
        self.selected_items_filtered = [i for i in self.selected_items if self.items[i].title.lower().find(filter.lower()) != -1]