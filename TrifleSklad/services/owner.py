from typing import Optional, Sequence

import reflex as rx

from TrifleSklad.dao.owner import OwnerDao
from TrifleSklad.dao_legacy import ProductDAO
from TrifleSklad.models import Owner
from TrifleSklad.services.errors import ServiceError


class OwnerService:
    def get_list_items(self) -> Sequence[Owner]:
        try:
            with rx.session() as session:
                items = OwnerDao.get_all(session)
                session.expunge_all()
                return items
        except Exception as e:
            print(f"[OwnerService][get_list_items][ERROR] {e}")
            raise

    def get_by_id(self, id: int) -> Optional[Owner]:
        try:
            with rx.session() as session:
                item = OwnerDao.get_by_id(id, session)
                if item is not None:
                    session.expunge(item)
                return item
        except Exception as e:
            print(f"[OwnerService][get_by_id][ERROR] {e}")
            raise

    def add_one(self, item: Owner) -> Owner:
        try:
            with rx.session() as session:
                if OwnerDao.exists_by_title(item.title, session):
                    raise ServiceError("Власник з такою назвою вже існує!")
                if item.is_default:
                    OwnerDao.clear_default(session)
                OwnerDao.add_one(item, session)
                session.commit()
                session.refresh(item)
                session.expunge(item)
                return item
        except ServiceError:
            raise
        except Exception as e:
            print(f"[OwnerService][add_one][ERROR] {e}")
            raise

    def edit_one(self, item: Owner) -> Owner:
        try:
            with rx.session() as session:
                if OwnerDao.exists_by_title(item.title, session, exclude_id=item.id):
                    raise ServiceError("Власник з такою назвою вже існує!")
                if item.is_default:
                    OwnerDao.clear_default(session, exclude_id=item.id)
                merged = OwnerDao.edit_one(item, session)
                session.commit()
                session.refresh(merged)
                session.expunge(merged)
                return merged
        except ServiceError:
            raise
        except Exception as e:
            print(f"[OwnerService][edit_one][ERROR] {e}")
            raise

    def delete_one(self, id: int) -> bool:
        try:
            # Тимчасова залежність від dao_legacy — заміниться на нативний
            # ProductDao, коли products переїде на нові шари (в цій же хвилі).
            if ProductDAO.count_by_owner(id) > 0:
                raise ServiceError("Неможливо видалити власника, за яким закріплено ТМЦ!")
            with rx.session() as session:
                item = OwnerDao.get_by_id(id, session)
                if item is None:
                    return False
                item.is_deleted = True
                OwnerDao.edit_one(item, session)
                session.commit()
                return True
        except ServiceError:
            raise
        except Exception as e:
            print(f"[OwnerService][delete_one][ERROR] {e}")
            return False
