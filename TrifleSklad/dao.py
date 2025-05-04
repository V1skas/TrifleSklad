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
        

class RoleDAO:
    @classmethod
    def get_all_with_relationships(cls) -> List[Role]:
        statement = select(Role).options(
            joinedload(Role.actions),
            joinedload(Role.users)
        )
        
        with rx.session() as session:
            return session.exec(statement).all()
        
    @classmethod
    def get_all(cls) -> List[Role]:
        statement = select(Role)
        
        with rx.session() as session:
            return session.exec(statement).all()
        
    @classmethod
    def get_by_id(cls, id: str) -> Optional[Role]:
        statement = select(Role).where(Role.id == id)
        
        with rx.session() as session:
            return session.exec(statement).one_or_none()
        
    @classmethod
    def add_one(cls, form_data: dict) -> tuple[bool, str]:
        role = Role(**form_data)
        
        with rx.session() as session:
            try:
                statement = select(Role).where(Role.title == role.title)

                if session.exec(statement).one_or_none() is not None:
                    return False, "Ошибка: Роль с таким именем уже существует"

                session.add(role)
                session.commit()
                return True, "Роль успешно добавлена"
            
            except IntegrityError:
                session.rollback()
                return False, "Ошибка: Роль не может быть добавлена"
            except SQLAlchemyError as e:
                session.rollback()
                return False, f"Ошибка: {str(e)}"
            
    @classmethod
    def edit_one(cls, form_data: dict) -> tuple[bool, str]:
        with rx.session() as session:
            try:
                role = session.get(Role, form_data["id"])
                
                if role is None:
                    return False, "Ошибка: Роль не найдена"
                
                for key, value in form_data.items():
                    setattr(role, key, value)
                
                statement = select(Role).where(Role.title == role.title).where(Role.id != role.id)
                if session.exec(statement).one_or_none() is not None:
                    return False, "Ошибка: Роль с таким именем уже существует"
                
                session.add(role)
                session.commit()
                return True, "Роль успешно изменена"
            
            except IntegrityError:
                session.rollback()
                return False, "Ошибка: Роль не может быть изменена"
            except SQLAlchemyError as e:
                session.rollback()
                return False, f"Ошибка: {str(e)}"
            

class ActionDAO:
    @classmethod
    def get_all(cls) -> List[Action]:
        statement = select(Action)
        
        with rx.session() as session:
            return session.exec(statement).all()