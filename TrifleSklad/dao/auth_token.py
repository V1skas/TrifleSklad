from datetime import datetime
from typing import Optional

from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, delete, select

from TrifleSklad.models import AuthToken, User
from TrifleSklad.utils.clock import now_local


class AuthTokenDao:
    @staticmethod
    def get_by_token(token: str, session: Session) -> Optional[AuthToken]:
        statement = (
            select(AuthToken)
            .where(AuthToken.token == token)
            .options(joinedload(AuthToken.user).options(selectinload(User.actions)))
        )
        return session.exec(statement).one_or_none()

    @staticmethod
    def add_one(auth_token: AuthToken, session: Session):
        session.add(auth_token)

    @staticmethod
    def delete(auth_token: AuthToken, session: Session):
        session.delete(auth_token)

    @staticmethod
    def delete_expired(session: Session, now: Optional[datetime] = None) -> int:
        """Видаляє всі токени, у яких expires_at <= now. Повертає к-сть видалених."""
        current = now or now_local()
        result = session.exec(delete(AuthToken).where(AuthToken.expires_at <= current))
        return getattr(result, "rowcount", 0) or 0

    @staticmethod
    def touch(auth_token: AuthToken, new_expires_at: datetime, session: Session) -> AuthToken:
        """Продовжує термін дії токена (ковзне вікно)."""
        auth_token.last_activity_at = now_local()
        auth_token.expires_at = new_expires_at
        session.add(auth_token)
        return auth_token
