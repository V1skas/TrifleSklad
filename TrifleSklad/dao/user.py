from typing import List, Optional, Sequence

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from TrifleSklad.models import Action, RolesActions, User, UsersActions, UsersRoles, Worker


class UserDao:
    @staticmethod
    def get_by_login(login: str, session: Session, with_del: bool = False) -> Optional[User]:
        statement = select(User).where(User.login == login)
        if not with_del:
            statement = statement.where(User.is_deleted == False)
        return session.exec(statement).one_or_none()

    @staticmethod
    def get_by_login_with_relationships(login: str, session: Session, with_del: bool = False) -> Optional[User]:
        statement = (
            select(User)
            .options(selectinload(User.actions), selectinload(User.roles), selectinload(User.worker))
            .where(User.login == login)
        )
        if not with_del:
            statement = statement.where(User.is_deleted == False)
        return session.exec(statement).one_or_none()

    @staticmethod
    def get_all_with_relationships(session: Session, with_del: bool = False) -> Sequence[User]:
        statement = select(User).options(
            selectinload(User.actions), selectinload(User.roles), selectinload(User.worker)
        )
        if not with_del:
            statement = statement.where(User.is_deleted == False)
        return session.exec(statement).all()

    @staticmethod
    def add_one(item: User, session: Session) -> User:
        session.add(item)
        return item

    @staticmethod
    def edit_one(item: User, session: Session) -> User:
        db_user = session.get(User, item.login)
        db_user.id_worker = item.id_worker
        db_user.salt = item.salt
        db_user.password_hash = item.password_hash
        db_user.is_deleted = item.is_deleted
        db_user.roles = [session.merge(r) for r in (item.roles or [])]
        db_user.actions = [session.merge(a) for a in (item.actions or [])]
        return db_user

    @staticmethod
    def get_effective_actions(login: str, session: Session) -> List[str]:
        direct_stmt = (
            select(Action.code)
            .join(UsersActions, Action.id == UsersActions.id_action)
            .where(UsersActions.id_user == login)
        )
        direct_actions = session.exec(direct_stmt).all()

        role_stmt = (
            select(Action.code)
            .join(RolesActions, Action.id == RolesActions.action_id)
            .join(UsersRoles, UsersRoles.id_role == RolesActions.role_id)
            .where(UsersRoles.id_user == login)
        )
        role_actions = session.exec(role_stmt).all()

        return list(set(direct_actions).union(set(role_actions)))

    @staticmethod
    def get_fio(login: str, session: Session) -> Optional[str]:
        statement = (
            select(Worker.fio)
            .join(User.worker)
            .where(User.login == login)
            .where(User.is_deleted == False)
        )
        return session.exec(statement).one_or_none()

    @staticmethod
    def get_permissions_version(login: str, session: Session) -> int:
        user = UserDao.get_by_login(login, session)
        return user.permissions_version if user is not None else 0
