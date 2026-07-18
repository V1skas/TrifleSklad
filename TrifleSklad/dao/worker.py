from typing import Optional, Sequence

from sqlmodel import Session, select, update

from TrifleSklad.models import Worker


class WorkerDao:
    @staticmethod
    def get_all(session: Session, with_del: bool = False) -> Sequence[Worker]:
        statement = select(Worker)
        if not with_del:
            statement = statement.where(Worker.is_deleted == False)
        return session.exec(statement).all()

    @staticmethod
    def get_by_id(id: int, session: Session, with_del: bool = False) -> Optional[Worker]:
        statement = select(Worker).where(Worker.id == id)
        if not with_del:
            statement = statement.where(Worker.is_deleted == False)
        return session.exec(statement).one_or_none()

    @staticmethod
    def exists_by_fio(fio: str, session: Session, exclude_id: Optional[int] = None) -> bool:
        statement = select(Worker).where(Worker.fio == fio).where(Worker.is_deleted == False)
        if exclude_id is not None:
            statement = statement.where(Worker.id != exclude_id)
        return session.exec(statement).one_or_none() is not None

    @staticmethod
    def clear_default(session: Session, exclude_id: Optional[int] = None) -> None:
        statement = update(Worker).where(Worker.is_deleted == False)
        if exclude_id is not None:
            statement = statement.where(Worker.id != exclude_id)
        session.exec(statement.values(is_default=False))

    @staticmethod
    def add_one(item: Worker, session: Session) -> Worker:
        session.add(item)
        return item

    @staticmethod
    def edit_one(item: Worker, session: Session) -> Worker:
        return session.merge(item)
