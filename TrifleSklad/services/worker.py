from typing import Optional, Sequence

import reflex as rx

from TrifleSklad.audit import record_action
from TrifleSklad.audit.actions.worker import WorkerCreated, WorkerDeleted, WorkerUpdated
from TrifleSklad.dao.worker import WorkerDao
from TrifleSklad.models import Worker
from TrifleSklad.services.errors import ServiceError


class WorkerService:
    def get_list_items(self) -> Sequence[Worker]:
        try:
            with rx.session() as session:
                items = WorkerDao.get_all(session)
                session.expunge_all()
                return items
        except Exception as e:
            print(f"[WorkerService][get_list_items][ERROR] {e}")
            raise

    def get_by_id(self, id: int) -> Optional[Worker]:
        try:
            with rx.session() as session:
                item = WorkerDao.get_by_id(id, session)
                if item is not None:
                    session.expunge(item)
                return item
        except Exception as e:
            print(f"[WorkerService][get_by_id][ERROR] {e}")
            raise

    def add_one(self, item: Worker, actor_login: str) -> Worker:
        try:
            with rx.session() as session:
                if WorkerDao.exists_by_fio(item.fio, session):
                    raise ServiceError("Співробітник з таким ПІБ вже існує!")
                if item.is_default:
                    WorkerDao.clear_default(session)
                WorkerDao.add_one(item, session)
                session.flush()
                record_action(session, actor_login, item.id, WorkerCreated.for_create(item, session))
                session.commit()
                session.refresh(item)
                session.expunge(item)
                return item
        except ServiceError:
            raise
        except Exception as e:
            print(f"[WorkerService][add_one][ERROR] {e}")
            raise

    def edit_one(self, item: Worker, actor_login: str) -> Worker:
        try:
            with rx.session() as session:
                if WorkerDao.exists_by_fio(item.fio, session, exclude_id=item.id):
                    raise ServiceError("Співробітник з таким ПІБ вже існує!")
                old_snapshot = WorkerUpdated.snapshot(WorkerDao.get_by_id(item.id, session))
                if item.is_default:
                    WorkerDao.clear_default(session, exclude_id=item.id)
                merged = WorkerDao.edit_one(item, session)
                record_action(session, actor_login, item.id, WorkerUpdated.from_diff(old_snapshot, merged, session))
                session.commit()
                session.refresh(merged)
                session.expunge(merged)
                return merged
        except ServiceError:
            raise
        except Exception as e:
            print(f"[WorkerService][edit_one][ERROR] {e}")
            raise

    def delete_one(self, id: int, actor_login: str) -> bool:
        try:
            with rx.session() as session:
                item = WorkerDao.get_by_id(id, session)
                if item is None:
                    return False
                item.is_deleted = True
                WorkerDao.edit_one(item, session)
                record_action(session, actor_login, id, WorkerDeleted.for_delete(item, session))
                session.commit()
                return True
        except Exception as e:
            print(f"[WorkerService][delete_one][ERROR] {e}")
            return False
