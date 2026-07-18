from typing import Optional, Sequence

import reflex as rx

from TrifleSklad.dao.supplier import SupplierDao
from TrifleSklad.models import Supplier
from TrifleSklad.services.errors import ServiceError


class SupplierService:
    def get_list_items(self) -> Sequence[Supplier]:
        try:
            with rx.session() as session:
                items = SupplierDao.get_all(session)
                session.expunge_all()
                return items
        except Exception as e:
            print(f"[SupplierService][get_list_items][ERROR] {e}")
            raise

    def get_by_id(self, id: int) -> Optional[Supplier]:
        try:
            with rx.session() as session:
                item = SupplierDao.get_by_id(id, session)
                if item is not None:
                    session.expunge(item)
                return item
        except Exception as e:
            print(f"[SupplierService][get_by_id][ERROR] {e}")
            raise

    def add_one(self, item: Supplier) -> Supplier:
        try:
            with rx.session() as session:
                if SupplierDao.exists_by_title(item.title, session):
                    raise ServiceError("Постачальник з такою назвою вже існує!")
                SupplierDao.add_one(item, session)
                session.commit()
                session.refresh(item)
                session.expunge(item)
                return item
        except ServiceError:
            raise
        except Exception as e:
            print(f"[SupplierService][add_one][ERROR] {e}")
            raise

    def edit_one(self, item: Supplier) -> Supplier:
        try:
            with rx.session() as session:
                if SupplierDao.exists_by_title(item.title, session, exclude_id=item.id):
                    raise ServiceError("Постачальник з такою назвою вже існує!")
                merged = SupplierDao.edit_one(item, session)
                session.commit()
                session.refresh(merged)
                session.expunge(merged)
                return merged
        except ServiceError:
            raise
        except Exception as e:
            print(f"[SupplierService][edit_one][ERROR] {e}")
            raise

    def delete_one(self, id: int) -> bool:
        try:
            with rx.session() as session:
                item = SupplierDao.get_by_id(id, session)
                if item is None:
                    return False
                item.is_deleted = True
                SupplierDao.edit_one(item, session)
                session.commit()
                return True
        except Exception as e:
            print(f"[SupplierService][delete_one][ERROR] {e}")
            return False
