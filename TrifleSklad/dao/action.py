from typing import List, Optional, Sequence

from sqlmodel import Session, select

from TrifleSklad.models import Action


class ActionDao:
    @staticmethod
    def get_all(session: Session) -> Sequence[Action]:
        return session.exec(select(Action)).all()

    @staticmethod
    def get_by_id(id: int, session: Session) -> Optional[Action]:
        return session.exec(select(Action).where(Action.id == id)).one_or_none()

    @staticmethod
    def get_by_list_id(id_list: List[int], session: Session) -> Sequence[Action]:
        return session.exec(select(Action).where(Action.id.in_(id_list))).all()
