import hashlib
from datetime import timedelta
from typing import List, Optional, Tuple

import reflex as rx

from TrifleSklad.dao.auth_token import AuthTokenDao
from TrifleSklad.dao.user import UserDao
from TrifleSklad.declared import SESSION_TIMEOUT_MINUTES
from TrifleSklad.models import AuthToken, User
from TrifleSklad.utils import generations
from TrifleSklad.utils.clock import now_local


def generate_password_hash(password: str, salt: str) -> str:
    """SHA-256(password + salt). Навмисно простий (без KDF) — успадковано з
    попередньої реалізації, у користувачів вже є паролі на цьому алгоритмі.
    Точка заміни на bcrypt/argon2 — тут і в `auth()` нижче, більше ніде."""
    return hashlib.sha256((password + salt).encode("utf-8")).hexdigest()


class AuthService:
    def _compute_expiry(self):
        return now_local() + timedelta(minutes=SESSION_TIMEOUT_MINUTES)

    def get_auth_token(self, cache_token: str) -> Optional[AuthToken]:
        """Повертає валідний (не протермінований) токен і продовжує його
        (ковзне вікно). Протерміновані токени видаляються одразу."""
        try:
            with rx.session() as session:
                AuthTokenDao.delete_expired(session)

                token = AuthTokenDao.get_by_token(cache_token, session)
                if token is None:
                    session.commit()
                    return None
                if token.expires_at <= now_local():
                    AuthTokenDao.delete(token, session)
                    session.commit()
                    return None

                AuthTokenDao.touch(token, self._compute_expiry(), session)
                session.commit()
                session.refresh(token)
                session.expunge_all()
                return token
        except Exception as e:
            print(f"[AuthService][get_auth_token][ERROR] {e}")
            return None

    def get_list_user_actions(self, login: str) -> List[str]:
        try:
            with rx.session() as session:
                return UserDao.get_effective_actions(login, session)
        except Exception as e:
            print(f"[AuthService][get_list_user_actions][ERROR] {e}")
            return []

    def get_fio(self, login: str) -> Optional[str]:
        try:
            with rx.session() as session:
                return UserDao.get_fio(login, session)
        except Exception as e:
            print(f"[AuthService][get_fio][ERROR] {e}")
            return None

    def get_user_permissions_version(self, login: str) -> int:
        """Поточна версія прав користувача — для звірки з кешем у AppState."""
        try:
            with rx.session() as session:
                return UserDao.get_permissions_version(login, session)
        except Exception as e:
            print(f"[AuthService][get_user_permissions_version][ERROR] {e}")
            return 0

    def logout(self, token: AuthToken):
        try:
            with rx.session() as session:
                AuthTokenDao.delete(token, session)
                session.commit()
        except Exception as e:
            print(f"[AuthService][logout][ERROR] {e}")

    def auth(self, login: str, password: str) -> Optional[Tuple[User, AuthToken]]:
        try:
            with rx.session() as session:
                AuthTokenDao.delete_expired(session)

                user = UserDao.get_by_login(login, session)
                if user is None:
                    session.commit()
                    return None

                if generate_password_hash(password, user.salt) != user.password_hash:
                    session.commit()
                    return None

                auth_token = AuthToken(
                    token=generations.generate_auth_token(),
                    id_user=user.login,
                    expires_at=self._compute_expiry(),
                    last_activity_at=now_local(),
                )
                AuthTokenDao.add_one(auth_token, session)
                session.commit()
                session.refresh(auth_token)
                session.refresh(user)
                session.expunge_all()
                return user, auth_token
        except Exception as e:
            print(f"[AuthService][auth][ERROR] {e}")
            return None
