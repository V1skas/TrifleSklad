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
            selectinload(Role.actions),
            selectinload(Role.users)
        ).where(Role.is_deleted == False)
        
        with rx.session() as session:
            return session.exec(statement).all()
        
    @classmethod
    def get_all(cls) -> List[Role]:
        statement = select(Role).where(Role.is_deleted == False)
        
        with rx.session() as session:
            return session.exec(statement).all()
        
    @classmethod
    def get_by_id(cls, id: str) -> Optional[Role]:
        statement = select(Role).where(Role.id == id).where(Role.is_deleted == False)
        
        with rx.session() as session:
            return session.exec(statement).one_or_none()

    @classmethod    
    def get_by_id_with_relationships(cls, id) -> Optional[Role]:
        statement = select(Role).options(
            selectinload(Role.actions),
            selectinload(Role.users)
        ).where(Role.id == id).where(Role.is_deleted == False)
        
        with rx.session() as session:
            return session.exec(statement).one_or_none()
        
    @classmethod
    def add_one(cls, form_data: dict) -> tuple[bool, str]:
        role = Role(**form_data)
        
        with rx.session() as session:
            try:
                statement = select(Role).where(Role.title == role.title)

                if session.exec(statement).one_or_none() is not None:
                    return False, "Ошибка: Роль с таким именем уже существует", -1

                session.add(role)
                session.commit()
                session.refresh(role)
                return True, "Роль успешно добавлена", role.id
            
            except IntegrityError as e:
                session.rollback()
                print("[RoleDAO] IntegrityError: ", e)
                return False, "Ошибка: Роль не может быть добавлена", -1
            except SQLAlchemyError as e:
                session.rollback()
                return False, f"Ошибка: {str(e)}", -1
            
    @classmethod
    def edit_one(cls, form_data: dict) -> tuple[bool, str, int]:
        with rx.session() as session:
            try:
                role = session.get(Role, form_data["id"])
                
                if role is None:
                    return False, "Ошибка: Роль не найдена", -1
                
                for key, value in form_data.items():
                    if key == "actions":
                        # value — список id действий, получаем объекты из базы
                        actions = session.exec(select(Action).where(Action.id.in_(value))).all()
                        setattr(role, key, actions)
                    else:
                        setattr(role, key, value)
                
                statement = select(Role).where(Role.title == role.title).where(Role.id != role.id)
                if session.exec(statement).one_or_none() is not None:
                    return False, "Ошибка: Роль с таким именем уже существует", role.id
                
                session.commit()
                session.refresh(role)
                return True, "Роль успешно изменена", role.id
            
            except IntegrityError as e:
                session.rollback()
                print("[RoleDAO] IntegrityError: ", e)
                return False, "Ошибка: Роль не может быть изменена", -1
            except SQLAlchemyError as e:
                session.rollback()
                print("[RoleDAO] SQLAlchemyError: ", e)
                return False, f"Ошибка: {str(e)}", -1
            
    @classmethod
    def delete_one(cls, id: str) -> tuple[bool, str]:
        with rx.session() as session:
            try:
                role = session.get(Role, id)
                
                if role is None:
                    return False, "Ошибка: Роль не найдена"
                
                session.delete(role)
                session.commit()
                return True, "Роль успешно удалена"
            
            except IntegrityError:
                session.rollback()
                return False, "Ошибка: Роль не может быть удалена"
            except SQLAlchemyError as e:
                session.rollback()
                return False, f"Ошибка: {str(e)}"
            except Exception as e:
                session.rollback()
                return False, f"Ошибка: {str(e)}"
            

class ActionDAO:
    @classmethod
    def get_all(cls) -> List[Action]:
        statement = select(Action)
        
        with rx.session() as session:
            return session.exec(statement).all()
        
    @classmethod
    def get_by_id(cls, id: str) -> Optional[Action]:
        statement = select(Action).where(Action.id == id)
        
        with rx.session() as session:
            return session.exec(statement).one_or_none()
        
    @classmethod
    def get_by_list_id(cls, id_list: List[str]) -> List[Action]:
        statement = select(Action).where(Action.id.in_(id_list))
        
        with rx.session() as session:
            return session.exec(statement).all()