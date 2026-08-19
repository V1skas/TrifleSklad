from typing import Optional, Sequence

from sqlmodel import Session, select, update

from TrifleSklad.models import PaymentType


class PaymentTypeDao:
    @staticmethod
    def get_all(session: Session, with_del: bool = False) -> Sequence[PaymentType]:
        statement = select(PaymentType)
        if not with_del:
            statement = statement.where(PaymentType.is_deleted == False)
        return session.exec(statement).all()

    @staticmethod
    def get_by_id(id: int, session: Session, with_del: bool = False) -> Optional[PaymentType]:
        statement = select(PaymentType).where(PaymentType.id == id)
        if not with_del:
            statement = statement.where(PaymentType.is_deleted == False)
        return session.exec(statement).one_or_none()

    @staticmethod
    def get_default_id(session: Session) -> Optional[int]:
        statement = (
            select(PaymentType.id)
            .where(PaymentType.is_default == True)
            .where(PaymentType.is_deleted == False)
        )
        return session.exec(statement).first()

    @staticmethod
    def exists_by_title(title: str, session: Session, exclude_id: Optional[int] = None) -> bool:
        statement = (
            select(PaymentType)
            .where(PaymentType.title == title)
            .where(PaymentType.is_deleted == False)
        )
        if exclude_id is not None:
            statement = statement.where(PaymentType.id != exclude_id)
        return session.exec(statement).one_or_none() is not None

    @staticmethod
    def clear_default(session: Session, exclude_id: Optional[int] = None) -> None:
        statement = update(PaymentType).where(PaymentType.is_deleted == False)
        if exclude_id is not None:
            statement = statement.where(PaymentType.id != exclude_id)
        session.exec(statement.values(is_default=False))

    @staticmethod
    def add_one(item: PaymentType, session: Session) -> PaymentType:
        session.add(item)
        return item

    @staticmethod
    def edit_one(item: PaymentType, session: Session) -> PaymentType:
        return session.merge(item)
