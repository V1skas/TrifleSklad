from typing import Optional, Sequence

from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, select, update

from TrifleSklad.models import Storage


class StorageDao:
    @staticmethod
    def get_all(session: Session, with_del: bool = False) -> Sequence[Storage]:
        statement = select(Storage).options(selectinload(Storage.responsible))
        if not with_del:
            statement = statement.where(Storage.is_deleted == False)
        return session.exec(statement).all()

    @staticmethod
    def get_by_id(id: int, session: Session, with_del: bool = False) -> Optional[Storage]:
        statement = select(Storage).options(joinedload(Storage.responsible)).where(Storage.id == id)
        if not with_del:
            statement = statement.where(Storage.is_deleted == False)
        return session.exec(statement).unique().one_or_none()

    @staticmethod
    def get_default_id(type: int, session: Session) -> Optional[int]:
        statement = (
            select(Storage.id)
            .where(Storage.type == type)
            .where(Storage.is_default == True)
            .where(Storage.is_deleted == False)
        )
        return session.exec(statement).first()

    @staticmethod
    def exists_by_title_type(title: str, type: int, session: Session, exclude_id: Optional[int] = None) -> bool:
        statement = (
            select(Storage)
            .where(Storage.title == title)
            .where(Storage.type == type)
            .where(Storage.is_deleted == False)
        )
        if exclude_id is not None:
            statement = statement.where(Storage.id != exclude_id)
        return session.exec(statement).one_or_none() is not None

    @staticmethod
    def clear_default(type: int, session: Session, exclude_id: Optional[int] = None) -> None:
        statement = update(Storage).where(Storage.type == type).where(Storage.is_deleted == False)
        if exclude_id is not None:
            statement = statement.where(Storage.id != exclude_id)
        session.exec(statement.values(is_default=False))

    @staticmethod
    def add_one(item: Storage, session: Session) -> Storage:
        session.add(item)
        return item

    @staticmethod
    def edit_one(item: Storage, session: Session) -> Storage:
        return session.merge(item)
