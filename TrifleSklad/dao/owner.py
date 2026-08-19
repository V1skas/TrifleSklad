from typing import Optional, Sequence

from sqlmodel import Session, select, update

from TrifleSklad.models import Owner


class OwnerDao:
    @staticmethod
    def get_all(session: Session, with_del: bool = False) -> Sequence[Owner]:
        statement = select(Owner)
        if not with_del:
            statement = statement.where(Owner.is_deleted == False)
        return session.exec(statement).all()

    @staticmethod
    def get_by_id(id: int, session: Session, with_del: bool = False) -> Optional[Owner]:
        statement = select(Owner).where(Owner.id == id)
        if not with_del:
            statement = statement.where(Owner.is_deleted == False)
        return session.exec(statement).one_or_none()

    @staticmethod
    def get_default_id(session: Session) -> Optional[int]:
        statement = (
            select(Owner.id)
            .where(Owner.is_default == True)
            .where(Owner.is_deleted == False)
        )
        return session.exec(statement).first()

    @staticmethod
    def exists_by_title(title: str, session: Session, exclude_id: Optional[int] = None) -> bool:
        statement = select(Owner).where(Owner.title == title).where(Owner.is_deleted == False)
        if exclude_id is not None:
            statement = statement.where(Owner.id != exclude_id)
        return session.exec(statement).one_or_none() is not None

    @staticmethod
    def clear_default(session: Session, exclude_id: Optional[int] = None) -> None:
        statement = update(Owner).where(Owner.is_deleted == False)
        if exclude_id is not None:
            statement = statement.where(Owner.id != exclude_id)
        session.exec(statement.values(is_default=False))

    @staticmethod
    def add_one(item: Owner, session: Session) -> Owner:
        session.add(item)
        return item

    @staticmethod
    def edit_one(item: Owner, session: Session) -> Owner:
        return session.merge(item)
