from typing import Optional, Sequence

import reflex as rx

from TrifleSklad.audit import record_action
from TrifleSklad.audit.actions.role import RoleCreated, RoleDeleted, RoleUpdated
from TrifleSklad.audit.labels import diff_related_titles
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

    def add_one(self, item: Role, actor_login: str) -> Role:
        try:
            with rx.session() as session:
                if RoleDao.exists_by_title(item.title, session):
                    raise ServiceError("Роль з таким іменем вже існує!")
                RoleDao.add_one(item, session)
                session.flush()
                lines = diff_related_titles([], item.actions)
                record_action(session, actor_login, item.id, RoleCreated.for_create(item, session, lines=lines))
                session.commit()
                session.refresh(item)
                session.expunge(item)
                return item
        except ServiceError:
            raise
        except Exception as e:
            print(f"[RoleService][add_one][ERROR] {e}")
            raise

    def edit_one(self, item: Role, actor_login: str) -> Role:
        try:
            with rx.session() as session:
                if RoleDao.exists_by_title(item.title, session, exclude_id=item.id):
                    raise ServiceError("Роль з таким іменем вже існує!")
                old_row = RoleDao.get_by_id(item.id, session)
                old_snapshot = RoleUpdated.snapshot(old_row)
                old_actions = list(old_row.actions or [])
                merged = RoleDao.edit_one(item, session)
                # Зміна прав ролі має застосуватись одразу всім її носіям —
                # бампаємо їхню permissions_version у тій самій транзакції.
                RoleDao.bump_permissions_version_for_role_holders(item.id, session)
                lines = diff_related_titles(old_actions, merged.actions)
                record_action(
                    session, actor_login, item.id, RoleUpdated.from_diff(old_snapshot, merged, session, lines=lines)
                )
                session.commit()
                session.refresh(merged)
                session.expunge(merged)
                return merged
        except ServiceError:
            raise
        except Exception as e:
            print(f"[RoleService][edit_one][ERROR] {e}")
            raise

    def delete_one(self, id: int, actor_login: str) -> bool:
        try:
            with rx.session() as session:
                item = RoleDao.get_by_id(id, session)
                if item is None:
                    return False
                lines = diff_related_titles(item.actions, [])
                deleted_action = RoleDeleted.for_delete(item, session, lines=lines)
                RoleDao.delete_one(item, session)
                record_action(session, actor_login, id, deleted_action)
                session.commit()
                return True
        except Exception as e:
            print(f"[RoleService][delete_one][ERROR] {e}")
            return False
