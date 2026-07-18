from typing import Optional, Sequence

from sqlmodel import Session, select

from TrifleSklad.models import Supplier


class SupplierDao:
    @staticmethod
    def get_all(session: Session, with_del: bool = False) -> Sequence[Supplier]:
        statement = select(Supplier)
        if not with_del:
            statement = statement.where(Supplier.is_deleted == False)
        return session.exec(statement).all()

    @staticmethod
    def get_by_id(id: int, session: Session, with_del: bool = False) -> Optional[Supplier]:
        statement = select(Supplier).where(Supplier.id == id)
        if not with_del:
            statement = statement.where(Supplier.is_deleted == False)
        return session.exec(statement).one_or_none()

    @staticmethod
    def exists_by_title(title: str, session: Session, exclude_id: Optional[int] = None) -> bool:
        statement = select(Supplier).where(Supplier.title == title).where(Supplier.is_deleted == False)
        if exclude_id is not None:
            statement = statement.where(Supplier.id != exclude_id)
        return session.exec(statement).one_or_none() is not None

    @staticmethod
    def add_one(item: Supplier, session: Session) -> Supplier:
        session.add(item)
        return item

    @staticmethod
    def edit_one(item: Supplier, session: Session) -> Supplier:
        return session.merge(item)
