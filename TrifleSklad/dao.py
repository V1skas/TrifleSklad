import reflex as rx

from typing import Optional, List
from sqlmodel import select, union
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from TrifleSklad.models import *


class UserDAO:
    @classmethod
    def get_user_by_id_with_relationships(cls, id: str) -> Optional[User]:
        statement = select(User).options(
                joinedload(User.actions),
                joinedload(User.roles),
                joinedload(User.worker)
            ).where(User.login == id)
        
        with rx.session() as session:
            return session.exec(statement).one_or_none()
        
    @classmethod
    def get_user_by_id(cls, id: str) -> Optional[User]:
        statement = select(User).where(User.login == id)
        
        with rx.session() as session:
            return session.exec(statement).one_or_none()
        
    @classmethod
    def get_user_actions_by_id(cls, id: str) -> List[str]:
        subquery1 = select(RolesActions.action_id).join(UsersRoles, RolesActions.role_id == UsersRoles.id_role).where(UsersRoles.id_user == id).distinct().subquery()
        subquery2 = select(UsersActions.id_action).where(UsersActions.id_user == id).distinct().subquery()
        
        statement = union(select(subquery1.c.action_id), select(subquery2.c.id_action))
        
        with rx.session() as session:
            result = session.exec(statement).all()
            print(result)
            return result