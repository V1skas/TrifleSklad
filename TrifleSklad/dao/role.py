from typing import Optional, Sequence

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select, update

from TrifleSklad.models import User, UsersRoles, Role


class RoleDao:
    @staticmethod
    def get_all(session: Session) -> Sequence[Role]:
        return session.exec(select(Role)).all()

    @staticmethod
    def get_by_id(id: int, session: Session) -> Optional[Role]:
        statement = select(Role).options(selectinload(Role.actions)).where(Role.id == id)
        return session.exec(statement).one_or_none()

    @staticmethod
    def exists_by_title(title: str, session: Session, exclude_id: Optional[int] = None) -> bool:
        statement = select(Role).where(Role.title == title)
        if exclude_id is not None:
            statement = statement.where(Role.id != exclude_id)
        return session.exec(statement).one_or_none() is not None

    @staticmethod
    def add_one(item: Role, session: Session) -> Role:
        session.add(item)
        return item

    @staticmethod
    def edit_one(item: Role, session: Session) -> Role:
        return session.merge(item)

    @staticmethod
    def delete_one(item: Role, session: Session) -> None:
        session.delete(item)

    @staticmethod
    def bump_permissions_version_for_role_holders(role_id: int, session: Session) -> None:
        """Бампає `permissions_version` усіх користувачів, що мають цю роль —
        щоб зміна прав ролі застосувалась без релогіну (AppState.require_auth
        звіряє версію на кожному запиті)."""
        holder_logins = session.exec(
            select(UsersRoles.id_user).where(UsersRoles.id_role == role_id)
        ).all()
        if not holder_logins:
            return
        session.exec(
            update(User).where(User.login.in_(holder_logins)).values(permissions_version=User.permissions_version + 1)
        )
