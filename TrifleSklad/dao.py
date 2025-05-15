import reflex as rx

from typing import Optional, List
from sqlmodel import select, union
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from TrifleSklad.models import *


class UserDAO:
    @classmethod
    def get_all(cls) -> List[User]:
        statement = select(User).where(User.is_deleted == False)
        
        with rx.session() as session:
            return session.exec(statement).all()
        
    @classmethod
    def get_all_with_relationships(cls) -> List[User]:
        statement = select(User).options(
            selectinload(User.actions),
            selectinload(User.roles),
            selectinload(User.worker)
        ).where(User.is_deleted == False)
        
        with rx.session() as session:
            return session.exec(statement).all()

    @classmethod
    def get_user_by_id_with_relationships(cls, id: str) -> Optional[User]:
        statement = select(User).options(
                selectinload(User.actions),
                selectinload(User.roles),
                selectinload(User.worker)
            ).where(User.login == id).where(User.is_deleted == False)
        
        with rx.session() as session:
            return session.exec(statement).one_or_none()
        
    @classmethod
    def get_user_by_id(cls, id: str) -> Optional[User]:
        statement = select(User).where(User.login == id).where(User.is_deleted == False)
        
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
        
    @classmethod
    def add_one(cls, form_data: dict) -> tuple[bool, str, str]:
        user = User(**form_data)
        
        with rx.session() as session:
            try:
                statement = select(User).where(User.login == user.login)

                if session.exec(statement).one_or_none() is not None:
                    return False, "Ошибка: Пользователь с таким логином уже существует", -1

                session.add(user)
                session.commit()
                session.refresh(user)
                return True, "Пользователь успешно добавлен", user.login
            
            except IntegrityError as e:
                session.rollback()
                print("[UserDAO] IntegrityError: ", e)
                return False, "Ошибка: Пользователь не может быть добавлен", -1
            except SQLAlchemyError as e:
                session.rollback()
                return False, f"Ошибка: {str(e)}", -1
            
    @classmethod
    def edit_one(cls, form_data: dict) -> tuple[bool, str, str]:
        with rx.session() as session:
            try:
                user = session.get(User, form_data["login"])
                
                if user is None:
                    return False, "Ошибка: Пользователь не найден", -1

                for key, value in form_data.items():
                    if key == "actions":
                        # value — список id действий, получаем объекты из базы
                        actions = session.exec(select(Action).where(Action.id.in_(value))).all()
                        setattr(user, key, actions)
                    elif key == "roles":
                        # value — список id ролей, получаем объекты из базы
                        roles = session.exec(select(Role).where(Role.id.in_(value))).all()
                        setattr(user, key, roles)
                    else:
                        setattr(user, key, value)
                
                statement = select(User).where(User.login == user.login).where(User.login != user.login)
                if session.exec(statement).one_or_none() is not None:
                    return False, "Ошибка: Пользователь с таким логином уже существует", user.login
                
                session.commit()
                session.refresh(user)
                return True, "Пользователь успешно изменен", user.login
            
            except IntegrityError as e:
                session.rollback()
                print("[UserDAO] IntegrityError: ", e)
                return False, "Ошибка: Пользователь не может быть изменен", -1
            except SQLAlchemyError as e:
                session.rollback()
                print("[UserDAO] SQLAlchemyError: ", e)
                return False, f"Ошибка: {str(e)}", -1
            except Exception as e:
                session.rollback()
                print("[UserDAO] Exception: ", e)
                return False, f"Ошибка: {str(e)}", -1
            
    @classmethod
    def delete_one(cls, id: str) -> tuple[bool, str]:
        with rx.session() as session:
            try:
                user = session.get(User, id)
                
                if user is None:
                    return False, "Ошибка: Пользователь не найден"
                
                user.is_deleted = True
                session.commit()
                return True, "Пользователь успешно удален"
            
            except IntegrityError:
                session.rollback()
                return False, "Ошибка: Пользователь не может быть удален"
            except SQLAlchemyError as e:
                session.rollback()
                return False, f"Ошибка: {str(e)}"
            except Exception as e:
                session.rollback()
                return False, f"Ошибка: {str(e)}"
        

class RoleDAO:
    @classmethod
    def get_all_with_relationships(cls) -> List[Role]:
        statement = select(Role).options(
            selectinload(Role.actions),
            selectinload(Role.users)
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
    def get_by_id_with_relationships(cls, id) -> Optional[Role]:
        statement = select(Role).options(
            selectinload(Role.actions),
            selectinload(Role.users)
        ).where(Role.id == id)
        
        with rx.session() as session:
            return session.exec(statement).one_or_none()
        
    @classmethod
    def get_by_list_id(cls, id_list: List[int]) -> List[Role]:
        statement = select(Role).where(Role.id.in_(id_list))
        
        with rx.session() as session:
            return session.exec(statement).all()
        
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
        

class WorkerDAO:
    @classmethod
    def get_all(cls) -> List[Worker]:
        statement = select(Worker)
        
        with rx.session() as session:
            return session.exec(statement).all()
        
    @classmethod
    def get_by_id(cls, id: str) -> Optional[Worker]:
        statement = select(Worker).where(Worker.id == id)
        
        with rx.session() as session:
            return session.exec(statement).one_or_none()
        
    @classmethod
    def get_by_fio(cls, fio: str) -> Optional[Worker]:
        statement = select(Worker).where(Worker.fio == fio)
        
        with rx.session() as session:
            return session.exec(statement).one_or_none()
        
    @classmethod
    def add_one(cls, form_data: dict) -> tuple[bool, str, int]:
        worker = Worker(**form_data)
        
        with rx.session() as session:
            try:
                statement = select(Worker).where(Worker.fio == worker.fio)

                if session.exec(statement).one_or_none() is not None:
                    return False, "Ошибка: Работник с таким ФИО уже существует", -1

                session.add(worker)
                session.commit()
                session.refresh(worker)
                return True, "Работник успешно добавлен", worker.id
            
            except IntegrityError as e:
                session.rollback()
                print("[WorkerDAO] IntegrityError: ", e)
                return False, "Ошибка: Работник не может быть добавлен", -1
            except SQLAlchemyError as e:
                session.rollback()
                return False, f"Ошибка: {str(e)}", -1
            
    @classmethod
    def edit_one(cls, form_data: dict) -> tuple[bool, str, int]:
        with rx.session() as session:
            try:
                worker = session.get(Worker, form_data["id"])
                
                if worker is None:
                    return False, "Ошибка: Работник не найден", -1
                
                for key, value in form_data.items():
                    setattr(worker, key, value)
                
                statement = select(Worker).where(Worker.fio == worker.fio).where(Worker.id != worker.id)
                if session.exec(statement).one_or_none() is not None:
                    return False, "Ошибка: Работник с таким ФИО уже существует", worker.id
                
                session.commit()
                session.refresh(worker)
                return True, "Работник успешно изменен", worker.id
            
            except IntegrityError as e:
                session.rollback()
                print("[WorkerDAO] IntegrityError: ", e)
                return False, "Ошибка: Работник не может быть изменен", -1
            except SQLAlchemyError as e:
                session.rollback()
                print("[WorkerDAO] SQLAlchemyError: ", e)
                return False, f"Ошибка: {str(e)}", -1
            except Exception as e:
                session.rollback()
                print("[WorkerDAO] Exception: ", e)
                return False, f"Ошибка: {str(e)}", -1
            
    @classmethod
    def delete_one(cls, id: str) -> tuple[bool, str]:
        with rx.session() as session:
            try:
                worker = session.get(Worker, id)
                
                if worker is None:
                    return False, "Ошибка: Работник не найден"
                
                worker.is_deleted = True
                session.commit()
                return True, "Работник успешно удален"
            
            except IntegrityError:
                session.rollback()
                return False, "Ошибка: Работник не может быть удален"
            except SQLAlchemyError as e:
                session.rollback()
                return False, f"Ошибка: {str(e)}"
            except Exception as e:
                session.rollback()
                return False, f"Ошибка: {str(e)}"