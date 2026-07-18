from typing import Optional, Sequence

import reflex as rx

from TrifleSklad.dao.role import RoleDao
from TrifleSklad.models import Role
from TrifleSklad.services.errors import ServiceError


class RoleService:
    def get_list_items(self) -> Sequence[Role]:
        try:
            with rx.session() as session:
                items = RoleDao.get_all(session)
                session.expunge_all()
                return items
        except Exception as e:
            print(f"[RoleService][get_list_items][ERROR] {e}")
            raise

    def get_by_id(self, id: int) -> Optional[Role]:
        try:
            with rx.session() as session:
                item = RoleDao.get_by_id(id, session)
                if item is not None:
                    session.expunge(item)
                return item
        except Exception as e:
            print(f"[RoleService][get_by_id][ERROR] {e}")
            raise

    def add_one(self, item: Role) -> Role:
        try:
            with rx.session() as session:
                if RoleDao.exists_by_title(item.title, session):
                    raise ServiceError("Роль з таким іменем вже існує!")
                RoleDao.add_one(item, session)
                session.commit()
                session.refresh(item)
                session.expunge(item)
                return item
        except ServiceError:
            raise
        except Exception as e:
            print(f"[RoleService][add_one][ERROR] {e}")
            raise

    def edit_one(self, item: Role) -> Role:
        try:
            with rx.session() as session:
                if RoleDao.exists_by_title(item.title, session, exclude_id=item.id):
                    raise ServiceError("Роль з таким іменем вже існує!")
                merged = RoleDao.edit_one(item, session)
                # Зміна прав ролі має застосуватись одразу всім її носіям —
                # бампаємо їхню permissions_version у тій самій транзакції.
                RoleDao.bump_permissions_version_for_role_holders(item.id, session)
                session.commit()
                session.refresh(merged)
                session.expunge(merged)
                return merged
        except ServiceError:
            raise
        except Exception as e:
            print(f"[RoleService][edit_one][ERROR] {e}")
            raise

    def delete_one(self, id: int) -> bool:
        try:
            with rx.session() as session:
                item = RoleDao.get_by_id(id, session)
                if item is None:
                    return False
                RoleDao.delete_one(item, session)
                session.commit()
                return True
        except Exception as e:
            print(f"[RoleService][delete_one][ERROR] {e}")
            return False
