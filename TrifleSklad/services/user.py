import hashlib
import os
from typing import Optional, Sequence

import reflex as rx

from TrifleSklad.audit import record_action
from TrifleSklad.audit.actions.user import UserCreated, UserDeleted, UserUpdated
from TrifleSklad.audit.labels import diff_related_titles
from TrifleSklad.dao.user import UserDao
from TrifleSklad.models import User
from TrifleSklad.services.errors import ServiceError

# Символи, заборонені в паролі (кирилиця та пробіл — щоб уникнути проблем із
# розкладкою клавіатури при вводі на різних пристроях).
_FORBIDDEN_PASSWORD_CHARS = set(" абвгдеёжзийклмнопрстуфхцчшщъыьэюяАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ")


def is_password_invalid(password: str) -> bool:
    return any(ch in _FORBIDDEN_PASSWORD_CHARS for ch in password)


def generate_salt() -> str:
    return os.urandom(16).hex()


def generate_password_hash(password: str, salt: str) -> str:
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()


class UserService:
    def get_list_items(self) -> Sequence[User]:
        try:
            with rx.session() as session:
                items = UserDao.get_all_with_relationships(session)
                session.expunge_all()
                return items
        except Exception as e:
            print(f"[UserService][get_list_items][ERROR] {e}")
            raise

    def get_by_login(self, login: str) -> Optional[User]:
        try:
            with rx.session() as session:
                item = UserDao.get_by_login_with_relationships(login, session)
                if item is not None:
                    session.expunge(item)
                return item
        except Exception as e:
            print(f"[UserService][get_by_login][ERROR] {e}")
            raise

    def add_one(self, item: User, actor_login: str, raw_password: str) -> User:
        try:
            with rx.session() as session:
                if UserDao.get_by_login(item.login, session, with_del=True) is not None:
                    raise ServiceError("Користувач з таким логіном вже існує!")
                if is_password_invalid(raw_password):
                    raise ServiceError("Пароль містить недопустимі символи!")
                item.salt = generate_salt()
                item.password_hash = generate_password_hash(raw_password, item.salt)
                UserDao.add_one(item, session)
                session.flush()
                lines = diff_related_titles([], item.roles) + diff_related_titles([], item.actions)
                record_action(session, actor_login, item.login, UserCreated.for_create(item, session, lines=lines))
                session.commit()
                session.refresh(item)
                session.expunge(item)
                return item
        except ServiceError:
            raise
        except Exception as e:
            print(f"[UserService][add_one][ERROR] {e}")
            raise

    def edit_one(self, item: User, actor_login: str, raw_password: str = "") -> User:
        try:
            with rx.session() as session:
                if raw_password != "":
                    if is_password_invalid(raw_password):
                        raise ServiceError("Пароль містить недопустимі символи!")
                    item.salt = generate_salt()
                    item.password_hash = generate_password_hash(raw_password, item.salt)
                old_row = UserDao.get_by_login_with_relationships(item.login, session)
                old_snapshot = UserUpdated.snapshot(old_row)
                old_roles = list(old_row.roles or [])
                old_actions = list(old_row.actions or [])
                merged = UserDao.edit_one(item, session)
                # Зміна ролей/індивідуальних прав користувача має застосуватись
                # одразу — бампаємо його permissions_version у тій самій транзакції.
                merged.permissions_version = (merged.permissions_version or 0) + 1
                session.add(merged)
                lines = diff_related_titles(old_roles, merged.roles) + diff_related_titles(old_actions, merged.actions)
                action_obj = UserUpdated.from_diff(old_snapshot, merged, session, lines=lines)
                if raw_password:
                    action_obj.mark_password_changed()
                record_action(session, actor_login, item.login, action_obj)
                session.commit()
                session.refresh(merged)
                session.expunge(merged)
                return merged
        except ServiceError:
            raise
        except Exception as e:
            print(f"[UserService][edit_one][ERROR] {e}")
            raise

    def delete_one(self, login: str, actor_login: str) -> bool:
        try:
            with rx.session() as session:
                item = UserDao.get_by_login(login, session)
                if item is None:
                    return False
                item.is_deleted = True
                session.add(item)
                record_action(session, actor_login, login, UserDeleted.for_delete(item, session))
                session.commit()
                return True
        except Exception as e:
            print(f"[UserService][delete_one][ERROR] {e}")
            return False
