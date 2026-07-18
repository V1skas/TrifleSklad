from typing import Optional, Sequence

import reflex as rx

from TrifleSklad.dao.payment_type import PaymentTypeDao
from TrifleSklad.models import PaymentType
from TrifleSklad.services.errors import ServiceError


class PaymentTypeService:
    def get_list_items(self) -> Sequence[PaymentType]:
        try:
            with rx.session() as session:
                items = PaymentTypeDao.get_all(session)
                session.expunge_all()
                return items
        except Exception as e:
            print(f"[PaymentTypeService][get_list_items][ERROR] {e}")
            raise

    def get_by_id(self, id: int) -> Optional[PaymentType]:
        try:
            with rx.session() as session:
                item = PaymentTypeDao.get_by_id(id, session)
                if item is not None:
                    session.expunge(item)
                return item
        except Exception as e:
            print(f"[PaymentTypeService][get_by_id][ERROR] {e}")
            raise

    def add_one(self, item: PaymentType) -> PaymentType:
        try:
            with rx.session() as session:
                if PaymentTypeDao.exists_by_title(item.title, session):
                    raise ServiceError("Тип оплати з такою назвою вже існує!")
                if item.is_default:
                    PaymentTypeDao.clear_default(session)
                PaymentTypeDao.add_one(item, session)
                session.commit()
                session.refresh(item)
                session.expunge(item)
                return item
        except ServiceError:
            raise
        except Exception as e:
            print(f"[PaymentTypeService][add_one][ERROR] {e}")
            raise

    def edit_one(self, item: PaymentType) -> PaymentType:
        try:
            with rx.session() as session:
                if PaymentTypeDao.exists_by_title(item.title, session, exclude_id=item.id):
                    raise ServiceError("Тип оплати з такою назвою вже існує!")
                if item.is_default:
                    PaymentTypeDao.clear_default(session, exclude_id=item.id)
                merged = PaymentTypeDao.edit_one(item, session)
                session.commit()
                session.refresh(merged)
                session.expunge(merged)
                return merged
        except ServiceError:
            raise
        except Exception as e:
            print(f"[PaymentTypeService][edit_one][ERROR] {e}")
            raise

    def delete_one(self, id: int) -> bool:
        try:
            with rx.session() as session:
                item = PaymentTypeDao.get_by_id(id, session)
                if item is None:
                    return False
                item.is_deleted = True
                PaymentTypeDao.edit_one(item, session)
                session.commit()
                return True
        except Exception as e:
            print(f"[PaymentTypeService][delete_one][ERROR] {e}")
            return False
