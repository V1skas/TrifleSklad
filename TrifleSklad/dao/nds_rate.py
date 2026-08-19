from typing import Optional, Sequence

from sqlmodel import Session, select, update

from TrifleSklad.models import NDSRate


class NdsRateDao:
    @staticmethod
    def get_all(session: Session, with_del: bool = False) -> Sequence[NDSRate]:
        statement = select(NDSRate)
        if not with_del:
            statement = statement.where(NDSRate.is_deleted == False)
        return session.exec(statement).all()

    @staticmethod
    def get_by_id(id: int, session: Session, with_del: bool = False) -> Optional[NDSRate]:
        statement = select(NDSRate).where(NDSRate.id == id)
        if not with_del:
            statement = statement.where(NDSRate.is_deleted == False)
        return session.exec(statement).one_or_none()

    @staticmethod
    def get_default_id(session: Session) -> Optional[int]:
        statement = (
            select(NDSRate.id)
            .where(NDSRate.is_default == True)
            .where(NDSRate.is_deleted == False)
        )
        return session.exec(statement).first()

    @staticmethod
    def exists_by_title(title: str, session: Session, exclude_id: Optional[int] = None) -> bool:
        statement = (
            select(NDSRate)
            .where(NDSRate.title == title)
            .where(NDSRate.is_deleted == False)
        )
        if exclude_id is not None:
            statement = statement.where(NDSRate.id != exclude_id)
        return session.exec(statement).one_or_none() is not None

    @staticmethod
    def clear_default(session: Session, exclude_id: Optional[int] = None) -> None:
        statement = update(NDSRate).where(NDSRate.is_deleted == False)
        if exclude_id is not None:
            statement = statement.where(NDSRate.id != exclude_id)
        session.exec(statement.values(is_default=False))

    @staticmethod
    def add_one(item: NDSRate, session: Session) -> NDSRate:
        session.add(item)
        return item

    @staticmethod
    def edit_one(item: NDSRate, session: Session) -> NDSRate:
        return session.merge(item)
