from typing import Optional, Sequence

import reflex as rx

from TrifleSklad.audit import record_action
from TrifleSklad.audit.actions.storage import StorageCreated, StorageDeleted, StorageUpdated
from TrifleSklad.dao.storage import StorageDao
from TrifleSklad.dao_legacy import ProductDAO
from TrifleSklad.models import Storage
from TrifleSklad.services.errors import ServiceError


class StorageService:
    def get_list_items(self) -> Sequence[Storage]:
        try:
            with rx.session() as session:
                items = StorageDao.get_all(session)
                session.expunge_all()
                return items
        except Exception as e:
            print(f"[StorageService][get_list_items][ERROR] {e}")
            raise

    def get_by_id(self, id: int) -> Optional[Storage]:
        try:
            with rx.session() as session:
                item = StorageDao.get_by_id(id, session)
                if item is not None:
                    session.expunge(item)
                return item
        except Exception as e:
            print(f"[StorageService][get_by_id][ERROR] {e}")
            raise

    def add_one(self, item: Storage, actor_login: str) -> Storage:
        try:
            with rx.session() as session:
                if StorageDao.exists_by_title_type(item.title, item.type, session):
                    raise ServiceError("Місце зберігання з такою назвою та типом вже існує!")
                if item.is_default:
                    StorageDao.clear_default(item.type, session)
                StorageDao.add_one(item, session)
                session.flush()
                record_action(session, actor_login, item.id, StorageCreated.for_create(item, session))
                session.commit()
                session.refresh(item)
                session.expunge(item)
                return item
        except ServiceError:
            raise
        except Exception as e:
            print(f"[StorageService][add_one][ERROR] {e}")
            raise

    def edit_one(self, item: Storage, actor_login: str) -> Storage:
        try:
            with rx.session() as session:
                if StorageDao.exists_by_title_type(item.title, item.type, session, exclude_id=item.id):
                    raise ServiceError("Місце зберігання з такою назвою та типом вже існує!")
                old_snapshot = StorageUpdated.snapshot(StorageDao.get_by_id(item.id, session))
                if item.is_default:
                    StorageDao.clear_default(item.type, session, exclude_id=item.id)
                merged = StorageDao.edit_one(item, session)
                record_action(session, actor_login, item.id, StorageUpdated.from_diff(old_snapshot, merged, session))
                session.commit()
                session.refresh(merged)
                session.expunge(merged)
                return merged
        except ServiceError:
            raise
        except Exception as e:
            print(f"[StorageService][edit_one][ERROR] {e}")
            raise

    def delete_one(self, id: int, actor_login: str) -> bool:
        try:
            # Тимчасова залежність від dao_legacy — заміниться на нативний
            # ProductDao, коли products переїде на нові шари (в цій же хвилі).
            if ProductDAO.count_by_storage(id) > 0:
                raise ServiceError("Неможливо видалити склад, на якому є ТМЦ!")
            with rx.session() as session:
                item = StorageDao.get_by_id(id, session)
                if item is None:
                    return False
                item.is_deleted = True
                StorageDao.edit_one(item, session)
                record_action(session, actor_login, id, StorageDeleted.for_delete(item, session))
                session.commit()
                return True
        except ServiceError:
            raise
        except Exception as e:
            print(f"[StorageService][delete_one][ERROR] {e}")
            return False
