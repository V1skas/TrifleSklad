from typing import List, Sequence

import reflex as rx

from TrifleSklad.dao.action import ActionDao
from TrifleSklad.models import Action


class ActionService:
    def get_list_items(self) -> Sequence[Action]:
        try:
            with rx.session() as session:
                items = ActionDao.get_all(session)
                session.expunge_all()
                return items
        except Exception as e:
            print(f"[ActionService][get_list_items][ERROR] {e}")
            raise

    def get_by_list_id(self, id_list: List[int]) -> Sequence[Action]:
        try:
            with rx.session() as session:
                items = ActionDao.get_by_list_id(id_list, session)
                session.expunge_all()
                return items
        except Exception as e:
            print(f"[ActionService][get_by_list_id][ERROR] {e}")
            raise
