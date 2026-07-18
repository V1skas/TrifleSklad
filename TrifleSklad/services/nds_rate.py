from typing import Optional, Sequence

import reflex as rx

from TrifleSklad.dao.nds_rate import NdsRateDao
from TrifleSklad.models import NDSRate
from TrifleSklad.services.errors import ServiceError


class NdsRateService:
    def get_list_items(self) -> Sequence[NDSRate]:
        try:
            with rx.session() as session:
                items = NdsRateDao.get_all(session)
                session.expunge_all()
                return items
        except Exception as e:
            print(f"[NdsRateService][get_list_items][ERROR] {e}")
            raise

    def get_by_id(self, id: int) -> Optional[NDSRate]:
        try:
            with rx.session() as session:
                item = NdsRateDao.get_by_id(id, session)
                if item is not None:
                    session.expunge(item)
                return item
        except Exception as e:
            print(f"[NdsRateService][get_by_id][ERROR] {e}")
            raise

    def add_one(self, item: NDSRate) -> NDSRate:
        try:
            with rx.session() as session:
                if NdsRateDao.exists_by_title(item.title, session):
                    raise ServiceError("Ставка ПДВ з такою назвою вже існує!")
                NdsRateDao.add_one(item, session)
                session.commit()
                session.refresh(item)
                session.expunge(item)
                return item
        except ServiceError:
            raise
        except Exception as e:
            print(f"[NdsRateService][add_one][ERROR] {e}")
            raise

    def edit_one(self, item: NDSRate) -> NDSRate:
        try:
            with rx.session() as session:
                if NdsRateDao.exists_by_title(item.title, session, exclude_id=item.id):
                    raise ServiceError("Ставка ПДВ з такою назвою вже існує!")
                merged = NdsRateDao.edit_one(item, session)
                session.commit()
                session.refresh(merged)
                session.expunge(merged)
                return merged
        except ServiceError:
            raise
        except Exception as e:
            print(f"[NdsRateService][edit_one][ERROR] {e}")
            raise

    def delete_one(self, id: int) -> bool:
        try:
            with rx.session() as session:
                item = NdsRateDao.get_by_id(id, session)
                if item is None:
                    return False
                item.is_deleted = True
                NdsRateDao.edit_one(item, session)
                session.commit()
                return True
        except Exception as e:
            print(f"[NdsRateService][delete_one][ERROR] {e}")
            return False
