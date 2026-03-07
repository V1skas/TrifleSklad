from typing import List, Optional

import reflex as rx
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import select

from TrifleSklad.declared import MovementsStatus, MovementsType, get_status_by_text
from TrifleSklad.models import (
    Action,
    Admission,
    AuthToken,
    Issue,
    Movement,
    MovementProducts,
    MovementProductsCatalog,
    Owner,
    PaymentType,
    Product,
    ProductCatalog,
    ProductCategory,
    Role,
    RolesActions,
    Sale,
    Storage,
    Supplier,
    User,
    UsersActions,
    UsersRoles,
    Worker,
)


class UserDAO:
    @classmethod
    def get_all(cls) -> List[User]:
        statement = select(User).where(User.is_deleted == False)

        with rx.session() as session:
            users = session.exec(statement).all()

            if len(users) > 0:
                session.expunge_all()
            return list(users)

    @classmethod
    def get_all_with_relationships(cls) -> List[User]:
        statement = (
            select(User)
            .options(
                selectinload(User.actions),
                selectinload(User.roles),
                selectinload(User.worker),
            )
            .where(User.is_deleted == False)
        )

        with rx.session() as session:
            users = session.exec(statement).all()

            if len(users) > 0:
                session.expunge_all()
            return list(users)

    @classmethod
    def get_user_by_id_with_relationships(cls, id: str) -> Optional[User]:
        statement = (
            select(User)
            .options(
                selectinload(User.actions),
                selectinload(User.roles),
                selectinload(User.worker),
            )
            .where(User.login == id)
            .where(User.is_deleted == False)
        )

        with rx.session() as session:
            user = session.exec(statement).one_or_none()

            if user:
                session.expunge(user)
            return user

    @classmethod
    def get_user_by_id(cls, id: str) -> Optional[User]:
        statement = select(User).where(User.login == id).where(User.is_deleted == False)

        with rx.session() as session:
            user = session.exec(statement).one_or_none()

            if user:
                session.expunge(user)
            return user

    @classmethod
    def get_user_actions_by_id(cls, user_login: str) -> List[str]:
        with rx.session() as session:
            direct_stmt = (
                select(Action.code)
                .join(UsersActions, Action.id == UsersActions.id_action)
                .where(UsersActions.id_user == user_login)
            )
            direct_actions = session.exec(direct_stmt).all()

            role_stmt = (
                select(Action.code)
                .join(RolesActions, Action.id == RolesActions.action_id)
                .join(UsersRoles, UsersRoles.id_role == RolesActions.role_id)
                .where(UsersRoles.id_user == user_login)
            )
            role_actions = session.exec(role_stmt).all()

            effective_actions = set(direct_actions).union(set(role_actions))

            print(f"Пользователь {user_login}. Прямые: {direct_actions}. Из ролей: {role_actions}")
            print(f"Итоговые права: {effective_actions}")

            return list(effective_actions)

    @classmethod
    def get_user_fio_by_login(cls, login: str) -> Optional[str]:
        statement = (
            select(Worker.fio)
            .join(User.worker)
            .where(User.login == login)
            .where(User.is_deleted == False)
        )

        with rx.session() as session:
            fio = session.exec(statement).one_or_none()
            return fio

    @classmethod
    def add_one(cls, user: User) -> tuple[bool, str, str]:
        try:
            with rx.session() as session:
                statement = select(User).where(User.login == user.login)

                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Помилка! Користувач з таким логіном вже існує!",
                        -1,
                    )

                user = session.merge(user)
                session.add(user)
                session.commit()
                session.refresh(user)
                return True, "Користувачаа додано!", user.login

        except IntegrityError as e:
            print("[UserDAO] IntegrityError:", e)
            return False, "Системна помилка! Користувач не може бути доданий.", -1
        except SQLAlchemyError as e:
            print(f"[UserDAO] SQLAlchemyError:\n{str(e)}")
            return False, "Системна помилка!", -1

    @classmethod
    def edit_one(cls, user: User) -> tuple[bool, str, str]:
        try:
            with rx.session() as session:
                if session.get(User, user.login) is None:
                    return False, "Помилка! Користувача не знайдено.", -1
                user = session.merge(user)
                session.add(user)
                session.commit()
                session.refresh(user)
                return True, "Користувача змінено", user.login

        except IntegrityError as e:
            print("[UserDAO] IntegrityError: ", e)
            return False, "Помилка! Користувач не може бути змінений.", -1
        except SQLAlchemyError as e:
            print("[UserDAO] SQLAlchemyError: ", e)
            return False, "Системна помилка!", -1
        except Exception as e:
            print("[UserDAO] Exception: ", e)
            return False, "Системна помилка!", -1

    @classmethod
    def delete_one(cls, id: str) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                user = session.get(User, id)

                if user is None:
                    return False, "Помилка! Користувача не знайдено."

                user.is_deleted = True
                session.commit()
                return True, "Користувача видалено!"

        except IntegrityError as e:
            print("[UserDAO] IntegrityError: ", e)
            return False, "Помилка! Користувач не може бути видалений.", -1
        except SQLAlchemyError as e:
            print("[UserDAO] SQLAlchemyError: ", e)
            return False, "Системна помилка!", -1
        except Exception as e:
            print("[UserDAO] Exception: ", e)
            return False, "Системна помилка!", -1


class AuthTokenDAO:
    @classmethod
    def get_by_token_user_actions(cls, token: str) -> Optional[AuthToken]:
        statement = (
            select(AuthToken)
            .where(AuthToken.token == token)
            .options(joinedload(AuthToken.user).options(selectinload(User.actions)))
        )

        with rx.session() as session:
            auth_token = session.exec(statement).one_or_none()

            if auth_token:
                session.expunge(auth_token)
            return auth_token

    @classmethod
    def add_one(cls, auth_token: AuthToken) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                session.add(auth_token)
                session.commit()
                session.refresh(auth_token)
                return True, "Токен успешно добавлен", auth_token.id

        except IntegrityError as e:
            print("[AuthTokenDAO] IntegrityError: ", e)
            return False, "Ошибка: Токен не может быть добавлен", -1
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def delete_one(cls, token: str):
        try:
            with rx.session() as session:
                auth_token = session.exec(
                    select(AuthToken).where(AuthToken.token == token)
                ).one_or_none()

                if auth_token is None:
                    return False, "Ошибка: Токен не найден"

                session.delete(auth_token)
                session.commit()
                return True, "Токен успешно удален"

        except IntegrityError:
            return False, "Ошибка: Токен не может быть удален"
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"

    @classmethod
    def delete_all_by_user(cls, login: str):
        try:
            with rx.session() as session:
                auth_tokens = session.exec(
                    select(AuthToken).where(AuthToken.user_login == login)
                ).all()

                if not auth_tokens:
                    return False, "Ошибка: Токены не найдены"

                for token in auth_tokens:
                    session.delete(token)

                session.commit()
                return True, "Все токены пользователя успешно удалены"

        except IntegrityError:
            return False, "Ошибка: Токены не могут быть удалены"
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"


class RoleDAO:
    @classmethod
    def get_all_with_relationships(cls) -> List[Role]:
        statement = select(Role).options(
            selectinload(Role.actions), selectinload(Role.users)
        )

        with rx.session() as session:
            roles = session.exec(statement).all()

            if len(roles) > 0:
                session.expunge_all()
            return list(roles)

    @classmethod
    def get_all(cls) -> List[Role]:
        statement = select(Role)

        with rx.session() as session:
            roles = session.exec(statement).all()

            if len(roles) > 0:
                session.expunge_all()
            return list(roles)

    @classmethod
    def get_by_id(cls, id: str) -> Optional[Role]:
        statement = select(Role).where(Role.id == id)

        with rx.session() as session:
            role = session.exec(statement).one_or_none()

            if role:
                session.expunge(role)
            return role

    @classmethod
    def get_by_id_with_relationships(cls, id) -> Optional[Role]:
        statement = (
            select(Role)
            .options(selectinload(Role.actions), selectinload(Role.users))
            .where(Role.id == id)
        )

        with rx.session() as session:
            role = session.exec(statement).one_or_none()

            if role:
                session.expunge(role)
            return role

    @classmethod
    def get_by_list_id(cls, id_list: List[int]) -> List[Role]:
        statement = select(Role).where(Role.id.in_(id_list))

        with rx.session() as session:
            roles = session.exec(statement).all()

            if len(roles) > 0:
                session.expunge_all()
            return list(roles)

    @classmethod
    def add_one(cls, role: Role) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                statement = select(Role).where(Role.title == role.title)

                if session.exec(statement).one_or_none() is not None:
                    return False, "Ошибка: Роль с таким именем уже существует", -1

                session.add(role)
                session.commit()
                session.refresh(role)
                return True, "Роль успешно добавлена", role.id

        except IntegrityError as e:
            print("[RoleDAO] IntegrityError: ", e)
            return False, "Ошибка: Роль не может быть добавлена", -1
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def edit_one(cls, role: Role) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                role = session.merge(role)
                session.add(role)
                session.commit()
                session.refresh(role)
                return True, "Роль успішно змінена!", role.id
        except IntegrityError as e:
            print("[RoleDAO] IntegrityError: ", e)
            return False, "Системна помилка! Роль не може бути змінена.", -1
        except SQLAlchemyError as e:
            print("[RoleDAO] SQLAlchemyError: ", e)
            return False, "Системна помилка! Зверніться до розробника.", -1

    @classmethod
    def delete_one(cls, id: str) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                role = session.get(Role, id)

                if role is None:
                    return False, "Помилка! Роль для видалення не знайдена."

                session.delete(role)
                session.commit()
                return True, "Роль видалено."

        except IntegrityError as e:
            print("[RoleDAO] IntegrityError: ", e)
            return False, "Системна помилка! Роль не може бути видалена."
        except SQLAlchemyError as e:
            print("[RoleDAO] SQLAlchemyError: ", e)
            return False, "Системна помилка!"
        except Exception as e:
            return False, "Системна помилка!"


class ActionDAO:
    @classmethod
    def get_all(cls) -> List[Action]:
        statement = select(Action)

        with rx.session() as session:
            actions = session.exec(statement).all()

            if len(actions) > 0:
                session.expunge_all()
            return list(actions)

    @classmethod
    def get_by_id(cls, id: str) -> Optional[Action]:
        statement = select(Action).where(Action.id == id)

        with rx.session() as session:
            action = session.exec(statement).one_or_none()

            if action:
                session.expunge(action)
            return action

    @classmethod
    def get_by_list_id(cls, id_list: List[str]) -> List[Action]:
        statement = select(Action).where(Action.id.in_(id_list))

        with rx.session() as session:
            actions = session.exec(statement).all()

            if len(actions) > 0:
                session.expunge_all()
            return list(actions)


class WorkerDAO:
    @classmethod
    def get_all(cls) -> List[Worker]:
        statement = select(Worker)

        with rx.session() as session:
            workers = session.exec(statement).all()

            if len(workers) > 0:
                session.expunge_all()
            return list(workers)

    @classmethod
    def get_by_id(cls, id: str) -> Optional[Worker]:
        statement = select(Worker).where(Worker.id == id)

        with rx.session() as session:
            worker = session.exec(statement).one_or_none()

            if worker:
                session.expunge(worker)
            return worker

    @classmethod
    def get_by_fio(cls, fio: str) -> Optional[Worker]:
        statement = select(Worker).where(Worker.fio == fio)

        with rx.session() as session:
            worker = session.exec(statement).one_or_none()

            if worker:
                session.expunge(worker)
            return worker

    @classmethod
    def add_one(cls, form_data: dict) -> tuple[bool, str, int]:
        worker = Worker(**form_data)

        try:
            with rx.session() as session:
                statement = select(Worker).where(Worker.fio == worker.fio)

                if session.exec(statement).one_or_none() is not None:
                    return False, "Ошибка: Работник с таким ФИО уже существует", -1

                session.add(worker)
                session.commit()
                session.refresh(worker)
                return True, "Работник успешно добавлен", worker.id

        except IntegrityError as e:
            print("[WorkerDAO] IntegrityError: ", e)
            return False, "Ошибка: Работник не может быть добавлен", -1
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def edit_one(cls, form_data: dict) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                worker = session.get(Worker, form_data["id"])

                if worker is None:
                    return False, "Ошибка: Работник не найден", -1

                for key, value in form_data.items():
                    setattr(worker, key, value)

                statement = (
                    select(Worker)
                    .where(Worker.fio == worker.fio)
                    .where(Worker.id != worker.id)
                )
                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Ошибка: Работник с таким ФИО уже существует",
                        worker.id,
                    )

                session.commit()
                session.refresh(worker)
                return True, "Работник успешно изменен", worker.id

        except IntegrityError as e:
            print("[WorkerDAO] IntegrityError: ", e)
            return False, "Ошибка: Работник не может быть изменен", -1
        except SQLAlchemyError as e:
            print("[WorkerDAO] SQLAlchemyError: ", e)
            return False, f"Ошибка: {str(e)}", -1
        except Exception as e:
            print("[WorkerDAO] Exception: ", e)
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def delete_one(cls, id: str) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                worker = session.get(Worker, id)

                if worker is None:
                    return False, "Ошибка: Работник не найден"

                worker.is_deleted = True
                session.commit()
                return True, "Работник успешно удален"

        except IntegrityError:
            return False, "Ошибка: Работник не может быть удален"
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"


class ProductCategoryDAO:
    @classmethod
    def get_all(cls) -> List[ProductCategory]:
        statement = select(ProductCategory).where(ProductCategory.is_deleted == False)

        with rx.session() as session:
            categories = session.exec(statement).all()

            if len(categories) > 0:
                session.expunge_all()
            return list(categories)

    @classmethod
    def get_all_with_relationships(cls) -> List[ProductCategory]:
        statement = (
            select(ProductCategory)
            .options(selectinload(ProductCategory.products))
            .where(ProductCategory.is_deleted == False)
        )

        with rx.session() as session:
            categories = session.exec(statement).all()

            if len(categories) > 0:
                session.expunge_all()
            return list(categories)

    @classmethod
    def get_by_id(cls, id: str) -> Optional[ProductCategory]:
        statement = (
            select(ProductCategory)
            .where(ProductCategory.id == id)
            .where(ProductCategory.is_deleted == False)
        )

        with rx.session() as session:
            category = session.exec(statement).one_or_none()

            if category:
                session.expunge(category)
            return category

    @classmethod
    def get_by_title(cls, title: str) -> Optional[ProductCategory]:
        statement = (
            select(ProductCategory)
            .where(ProductCategory.title == title)
            .where(ProductCategory.is_deleted == False)
        )

        with rx.session() as session:
            category = session.exec(statement).one_or_none()

            if category:
                session.expunge(category)
            return category

    @classmethod
    def get_by_id_with_relationships(cls, id: str) -> Optional[ProductCategory]:
        statement = (
            select(ProductCategory)
            .options(joinedload(ProductCategory.products))
            .where(ProductCategory.id == id)
            .where(ProductCategory.is_deleted == False)
        )

        with rx.session() as session:
            category = session.exec(statement).unique().one_or_none()

            if category:
                session.expunge(category)
            return category

    @classmethod
    def add_one(cls, form_data: dict) -> tuple[bool, str, int]:
        category = ProductCategory(**form_data)

        try:
            with rx.session() as session:
                statement = (
                    select(ProductCategory)
                    .where(ProductCategory.title == category.title)
                    .where(ProductCategory.is_deleted == False)
                )

                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Ошибка: Категория с таким названием уже существует",
                        -1,
                    )

                session.add(category)
                session.commit()
                session.refresh(category)
                return True, "Категория успешно добавлена", category.id

        except IntegrityError as e:
            print("[ProductCategoryDAO] IntegrityError: ", e)
            return False, "Ошибка: Категория не может быть добавлена", -1
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def edit_one(cls, form_data: dict) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                category = session.get(ProductCategory, form_data["id"])

                if category is None:
                    return False, "Ошибка: Категория не найдена", -1

                for key, value in form_data.items():
                    setattr(category, key, value)

                statement = (
                    select(ProductCategory)
                    .where(ProductCategory.title == category.title)
                    .where(ProductCategory.id != category.id)
                    .where(ProductCategory.is_deleted == False)
                )
                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Ошибка: Категория с таким названием уже существует",
                        category.id,
                    )

                session.commit()
                session.refresh(category)
                return True, "Категория успешно изменена", category.id

        except IntegrityError as e:
            print("[ProductCategoryDAO] IntegrityError: ", e)
            return False, "Ошибка: Категория не может быть изменена", -1
        except SQLAlchemyError as e:
            print("[ProductCategoryDAO] SQLAlchemyError: ", e)
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def delete_one(cls, id: int) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                category = session.get(ProductCategory, id)

                if category is None:
                    return False, "Ошибка: Категория не найдена"

                category.is_deleted = True
                session.commit()
                return True, "Категория успешно удалена"

        except IntegrityError:
            return False, "Ошибка: Категория не может быть удалена"
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"


class ProductCatalogDAO:
    @classmethod
    def get_all(cls) -> List[ProductCatalog]:
        statement = select(ProductCatalog).where(ProductCatalog.is_deleted == False)

        with rx.session() as session:
            products = session.exec(statement).all()

            if len(products) > 0:
                session.expunge_all()
            return list(products)

    @classmethod
    def get_all_exclude_ids(cls, exclude_ids: List[int]) -> List[ProductCatalog]:
        statement = (
            select(ProductCatalog)
            .where(ProductCatalog.is_deleted == False)
            .where(ProductCatalog.id.not_in(exclude_ids))
        )

        with rx.session() as session:
            products = session.exec(statement).all()

            if len(products) > 0:
                session.expunge_all()
            return list(products)

    @classmethod
    def get_all_titles(cls) -> List[str]:
        statement = select(ProductCatalog.title).where(
            ProductCatalog.is_deleted == False
        )

        with rx.session() as session:
            return session.exec(statement).all()

    @classmethod
    def get_all_with_relationships(cls) -> List[ProductCatalog]:
        statement = (
            select(ProductCatalog)
            .options(selectinload(ProductCatalog.category))
            .where(ProductCatalog.is_deleted == False)
        )

        with rx.session() as session:
            products = session.exec(statement).all()

            if len(products) > 0:
                session.expunge_all()
            return list(products)

    @classmethod
    def get_by_id(cls, id: str) -> Optional[ProductCatalog]:
        statement = (
            select(ProductCatalog)
            .where(ProductCatalog.id == id)
            .where(ProductCatalog.is_deleted == False)
        )

        with rx.session() as session:
            product = session.exec(statement).one_or_none()

            if product:
                session.expunge(product)
            return product

    @classmethod
    def get_by_id_with_relationships(cls, id: str) -> Optional[ProductCatalog]:
        statement = (
            select(ProductCatalog)
            .options(joinedload(ProductCatalog.category))
            .where(ProductCatalog.id == id)
            .where(ProductCatalog.is_deleted == False)
        )

        with rx.session() as session:
            product = session.exec(statement).unique().one_or_none()

            if product:
                session.expunge(product)
            return product

    @classmethod
    def get_by_title(cls, title: str) -> Optional[ProductCatalog]:
        statement = (
            select(ProductCatalog)
            .where(ProductCatalog.title == title)
            .where(ProductCatalog.is_deleted == False)
        )

        with rx.session() as session:
            product = session.exec(statement).one_or_none()

            if product:
                session.expunge(product)
            return product

    @classmethod
    def add_one(cls, form_data: dict) -> tuple[bool, str, int]:
        product = ProductCatalog(**form_data)

        try:
            with rx.session() as session:
                statement = (
                    select(ProductCatalog)
                    .where(ProductCatalog.title == product.title)
                    .where(ProductCatalog.is_deleted == False)
                )

                if session.exec(statement).one_or_none() is not None:
                    return False, "Ошибка: Товар с таким названием уже существует", -1

                session.add(product)
                session.commit()
                session.refresh(product)
                return True, "Товар успешно добавлен", product.id

        except IntegrityError as e:
            print("[ProductCatalogDAO] IntegrityError: ", e)
            return False, "Ошибка: Товар не может быть добавлен", -1
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def edit_one(cls, form_data: dict) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                product = session.get(ProductCatalog, form_data["id"])

                if product is None:
                    return False, "Ошибка: Товар не найден", -1

                for key, value in form_data.items():
                    setattr(product, key, value)

                statement = (
                    select(ProductCatalog)
                    .where(ProductCatalog.title == product.title)
                    .where(ProductCatalog.id != product.id)
                    .where(ProductCatalog.is_deleted == False)
                )
                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Ошибка: Товар с таким названием уже существует",
                        product.id,
                    )

                session.commit()
                session.refresh(product)
                return True, "Товар успешно изменен", product.id

        except IntegrityError as e:
            print("[ProductCatalogDAO] IntegrityError: ", e)
            return False, "Ошибка: Товар не может быть изменен", -1
        except SQLAlchemyError as e:
            print("[ProductCatalogDAO] SQLAlchemyError: ", e)
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def delete_one(cls, id: int) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                product = session.get(ProductCatalog, id)

                if product is None:
                    return False, "Ошибка: Товар не найден"

                product.is_deleted = True
                session.commit()
                return True, "Товар успешно удален"

        except IntegrityError:
            return False, "Ошибка: Товар не может быть удален"
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"


class StorageDAO:
    @classmethod
    def get_all(cls) -> List[Storage]:
        statement = select(Storage).where(Storage.is_deleted == False)

        with rx.session() as session:
            storages = session.exec(statement).all()

            if len(storages) > 0:
                session.expunge_all()
            return list(storages)

    @classmethod
    def get_all_with_relationships(cls) -> List[Storage]:
        statement = (
            select(Storage)
            .options(selectinload(Storage.responsible))
            .where(Storage.is_deleted == False)
        )

        with rx.session() as session:
            storages = session.exec(statement).all()

            if len(storages) > 0:
                session.expunge_all()
            return list(storages)

    @classmethod
    def get_by_id(cls, id: str) -> Optional[Storage]:
        statement = (
            select(Storage).where(Storage.id == id).where(Storage.is_deleted == False)
        )

        with rx.session() as session:
            storage = session.exec(statement).one_or_none()

            if storage:
                session.expunge(storage)
            return storage

    @classmethod
    def get_by_id_with_relationships(cls, id: str) -> Optional[Storage]:
        statement = (
            select(Storage)
            .options(joinedload(Storage.responsible))
            .where(Storage.id == id)
            .where(Storage.is_deleted == False)
        )

        with rx.session() as session:
            storage = session.exec(statement).unique().one_or_none()

            if storage:
                session.expunge(storage)
            return storage

    @classmethod
    def get_by_title(cls, title: str) -> Optional[Storage]:
        statement = (
            select(Storage)
            .where(Storage.title == title)
            .where(Storage.is_deleted == False)
        )

        with rx.session() as session:
            storage = session.exec(statement).one_or_none()

            if storage:
                session.expunge(storage)
            return storage

    @classmethod
    def get_titles_by_type(cls, t: int) -> Optional[List[str]]:
        statement = (
            select(Storage.title)
            .where(Storage.type == t)
            .where(Storage.is_deleted == False)
        )

        with rx.session() as session:
            return session.exec(statement).all()

    @classmethod
    def get_all_by_type(cls, t: int) -> List[Storage]:
        statement = (
            select(Storage).where(Storage.type == t).where(Storage.is_deleted == False)
        )

        with rx.session() as session:
            storages = session.exec(statement).all()

            if len(storages) > 0:
                session.expunge_all()
            return list(storages)

    @classmethod
    def add_one(cls, form_data: dict) -> tuple[bool, str, int]:
        storage = Storage(**form_data)

        try:
            with rx.session() as session:
                statement = (
                    select(Storage)
                    .where(Storage.title == storage.title)
                    .where(Storage.is_deleted == False)
                )

                if session.exec(statement).one_or_none() is not None:
                    return False, "Ошибка: Склад с таким названием уже существует", -1

                session.add(storage)
                session.commit()
                session.refresh(storage)
                return True, "Склад успешно добавлен", storage.id

        except IntegrityError as e:
            print("[StorageDAO] IntegrityError: ", e)
            return False, "Ошибка: Склад не может быть добавлен", -1
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def edit_one(cls, form_data: dict) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                storage = session.get(Storage, form_data["id"])

                if storage is None:
                    return False, "Ошибка: Склад не найден", -1

                for key, value in form_data.items():
                    setattr(storage, key, value)

                statement = (
                    select(Storage)
                    .where(Storage.title == storage.title)
                    .where(Storage.id != storage.id)
                    .where(Storage.is_deleted == False)
                )
                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Ошибка: Склад с таким названием уже существует",
                        storage.id,
                    )

                session.commit()
                session.refresh(storage)
                return True, "Склад успешно изменен", storage.id

        except IntegrityError as e:
            print("[StorageDAO] IntegrityError: ", e)
            return False, "Ошибка: Склад не может быть изменен", -1
        except SQLAlchemyError as e:
            print("[StorageDAO] SQLAlchemyError: ", e)
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def delete_one(cls, id: int) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                storage = session.get(Storage, id)

                if storage is None:
                    return False, "Ошибка: Склад не найден"

                storage.is_deleted = True
                session.commit()
                return True, "Склад успешно удален"

        except IntegrityError:
            return False, "Ошибка: Склад не может быть удален"
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"


class OwnerDAO:
    @classmethod
    def get_all(cls) -> List[Owner]:
        statement = select(Owner).where(Owner.is_deleted == False)

        with rx.session() as session:
            owners = session.exec(statement).all()

            if len(owners) > 0:
                session.expunge_all()
            return list(owners)

    @classmethod
    def get_by_id(cls, id: str) -> Optional[Owner]:
        statement = select(Owner).where(Owner.id == id).where(Owner.is_deleted == False)

        with rx.session() as session:
            owner = session.exec(statement).one_or_none()

            if owner:
                session.expunge(owner)
            return owner

    @classmethod
    def get_by_title(cls, title: str) -> Optional[Owner]:
        statement = (
            select(Owner).where(Owner.title == title).where(Owner.is_deleted == False)
        )

        with rx.session() as session:
            owner = session.exec(statement).one_or_none()

            if owner:
                session.expunge(owner)
            return owner

    @classmethod
    def get_all_titles(cls) -> List[str]:
        statement = select(Owner.title).where(Owner.is_deleted == False)

        with rx.session() as session:
            return session.exec(statement).all()

    @classmethod
    def add_one(cls, form_data: dict) -> tuple[bool, str, int]:
        owner = Owner(**form_data)

        try:
            with rx.session() as session:
                statement = (
                    select(Owner)
                    .where(Owner.title == owner.title)
                    .where(Owner.is_deleted == False)
                )

                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Ошибка: Владелец с таким названием уже существует",
                        -1,
                    )

                session.add(owner)
                session.commit()
                session.refresh(owner)
                return True, "Владелец успешно добавлен", owner.id

        except IntegrityError as e:
            print("[OwnerDAO] IntegrityError: ", e)
            return False, "Ошибка: Владелец не может быть добавлен", -1
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def edit_one(cls, form_data: dict) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                owner = session.get(Owner, form_data["id"])

                if owner is None:
                    return False, "Ошибка: Владелец не найден", -1

                for key, value in form_data.items():
                    setattr(owner, key, value)

                statement = (
                    select(Owner)
                    .where(Owner.title == owner.title)
                    .where(Owner.id != owner.id)
                    .where(Owner.is_deleted == False)
                )
                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Ошибка: Владелец с таким названием уже существует",
                        owner.id,
                    )

                session.commit()
                session.refresh(owner)
                return True, "Владелец успешно изменен", owner.id

        except IntegrityError as e:
            print("[OwnerDAO] IntegrityError: ", e)
            return False, "Ошибка: Владелец не может быть изменен", -1
        except SQLAlchemyError as e:
            print("[OwnerDAO] SQLAlchemyError: ", e)
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def delete_one(cls, id: int) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                owner = session.get(Owner, id)

                if owner is None:
                    return False, "Ошибка: Владелец не найден"

                owner.is_deleted = True
                session.commit()
                return True, "Владелец успешно удален"

        except IntegrityError:
            return False, "Ошибка: Владелец не может быть удален"
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"


class SupplierDAO:
    @classmethod
    def get_all(cls) -> List[Supplier]:
        statement = select(Supplier).where(Supplier.is_deleted == False)

        with rx.session() as session:
            return session.exec(statement).all()

    @classmethod
    def get_by_id(cls, id: str) -> Optional[Supplier]:
        statement = (
            select(Supplier)
            .where(Supplier.id == id)
            .where(Supplier.is_deleted == False)
        )

        with rx.session() as session:
            return session.exec(statement).one_or_none()

    @classmethod
    def get_by_title(cls, title: str) -> Optional[Supplier]:
        statement = (
            select(Supplier)
            .where(Supplier.title == title)
            .where(Supplier.is_deleted == False)
        )

        with rx.session() as session:
            return session.exec(statement).one_or_none()

    @classmethod
    def get_all_titles(cls) -> List[str]:
        statement = select(Supplier.title).where(Supplier.is_deleted == False)

        with rx.session() as session:
            return session.exec(statement).all()

    @classmethod
    def add_one(cls, form_data: dict) -> tuple[bool, str, int]:
        supplier = Supplier(**form_data)

        try:
            with rx.session() as session:
                statement = (
                    select(Supplier)
                    .where(Supplier.title == supplier.title)
                    .where(Supplier.is_deleted == False)
                )

                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Ошибка: Поставщик с таким названием уже существует",
                        -1,
                    )

                session.add(supplier)
                session.commit()
                session.refresh(supplier)
                return True, "Поставщик успешно добавлен", supplier.id

        except IntegrityError as e:
            print("[SupplierDAO] IntegrityError: ", e)
            return False, "Ошибка: Поставщик не может быть добавлен", -1
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def edit_one(cls, form_data: dict) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                supplier = session.get(Supplier, form_data["id"])

                if supplier is None:
                    return False, "Ошибка: Поставщик не найден", -1

                for key, value in form_data.items():
                    setattr(supplier, key, value)

                statement = (
                    select(Supplier)
                    .where(Supplier.title == supplier.title)
                    .where(Supplier.id != supplier.id)
                    .where(Supplier.is_deleted == False)
                )
                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Ошибка: Поставщик с таким названием уже существует",
                        supplier.id,
                    )

                session.commit()
                session.refresh(supplier)
                return True, "Поставщик успешно изменен", supplier.id

        except IntegrityError as e:
            print("[SupplierDAO] IntegrityError: ", e)
            return False, "Ошибка: Поставщик не может быть изменен", -1
        except SQLAlchemyError as e:
            print("[SupplierDAO] SQLAlchemyError: ", e)
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def delete_one(cls, id: int) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                supplier = session.get(Supplier, id)

                if supplier is None:
                    return False, "Ошибка: Поставщик не найден"

                supplier.is_deleted = True
                session.commit()
                return True, "Поставщик успешно удален"

        except IntegrityError:
            return False, "Ошибка: Поставщик не может быть удален"
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"


class ProductDAO:
    @classmethod
    def get_all(cls) -> List[Product]:
        statement = select(Product)

        with rx.session() as session:
            products = session.exec(statement).all()

            if len(products) > 0:
                session.expunge_all()
            return list(products)

    @classmethod
    def get_by_id(cls, id: str) -> Optional[Product]:
        statement = select(Product).where(Product.id == id)

        with rx.session() as session:
            product = session.exec(statement).one_or_none()

            if product:
                session.expunge(product)
            return product

    @classmethod
    def get_by_owner_storage_with_product_catalog(
        cls, owner_id: int, storage_id: int
    ) -> List[Product]:
        statement = (
            select(Product)
            .options(joinedload(Product.product_catalog))
            .where(Product.id_owner == owner_id)
            .where(Product.id_storage == storage_id)
            .where(Product.is_deleted == False)
        )

        with rx.session() as session:
            products = session.exec(statement).all()

            if len(products) > 0:
                session.expunge_all()
            return list(products)

    @classmethod
    def add_one(cls, form_data: dict) -> tuple[bool, str, int]:
        product = Product(**form_data)

        try:
            with rx.session() as session:
                session.add(product)
                session.commit()
                session.refresh(product)
                return True, "Единица товара успешно добавлена", product.id

        except IntegrityError as e:
            print("[ProductDAO] IntegrityError: ", e)
            return False, "Ошибка: Единица товара не может быть добавлена", -1
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def edit_one(cls, form_data: dict) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                product = session.get(Product, form_data["id"])

                if product is None:
                    return False, "Ошибка: Единица товара не найдена", -1

                for key, value in form_data.items():
                    setattr(product, key, value)

                session.commit()
                session.refresh(product)
                return True, "Единица товара успешно изменена", product.id

        except IntegrityError as e:
            print("[ProductDAO] IntegrityError: ", e)
            return False, "Ошибка: Единица товара не может быть изменена", -1
        except SQLAlchemyError as e:
            print("[ProductDAO] SQLAlchemyError: ", e)
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def delete_list(cls, id_list: List[int]) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                statement = select(Product).where(Product.id.in_(id_list))
                products = session.exec(statement).all()

                for product in products:
                    product.is_deleted = True
                    session.add(product)

                session.commit()
                return True, "Единицы товара успешно удалены"

        except IntegrityError:
            return False, "Ошибка: Единицы товара не могут быть удалены"
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"

    @classmethod
    def undelete_list(cls, id_list: List[int]) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                statement = select(Product).where(Product.id.in_(id_list))
                products = session.exec(statement).all()

                for product in products:
                    product.is_deleted = False
                    session.add(product)

                session.commit()
                return True, "Единицы товара успешно восстановлены"

        except IntegrityError:
            return False, "Ошибка: Единицы товара не могут быть восстановлены"
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"

    @classmethod
    def update_owner_storage(
        cls, id_list: List[int], new_owner_id: int, new_storage_id: int
    ) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                statement = select(Product).where(Product.id.in_(id_list))
                products = session.exec(statement).all()

                for product in products:
                    product.id_owner = new_owner_id
                    product.id_storage = new_storage_id
                    session.add(product)

                session.commit()
                return True, "Единицы товара успешно перемещены"

        except IntegrityError:
            return False, "Ошибка: Единицы товара не могут быть перемещены"
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"


class MovementDAO:
    @classmethod
    def get_all(cls) -> List[Movement]:
        statement = select(Movement)

        with rx.session() as session:
            movements = session.exec(statement).all()

            if len(movements) > 0:
                session.expunge_all()
            return list(movements)

    @classmethod
    def get_by_id(cls, id: str) -> Optional[Movement]:
        statement = select(Movement).where(Movement.id == id)

        with rx.session() as session:
            movement = session.exec(statement).one_or_none()

            if movement:
                session.expunge(movement)
            return movement

    @classmethod
    def get_all_by_type(cls, movement_type: int) -> List[Movement]:
        statement = select(Movement).where(Movement.type == movement_type)

        with rx.session() as session:
            movements = session.exec(statement).all()

            if len(movements) > 0:
                session.expunge_all()
            return list(movements)

    @classmethod
    def get_all_with_storage_owner(cls) -> List[Movement]:
        statement = select(Movement).options(
            joinedload(Movement.incoming_storage), joinedload(Movement.incoming_owner)
        )

        with rx.session() as session:
            movements = session.exec(statement).all()

            if len(movements) > 0:
                session.expunge_all()
            return list(movements)

    @classmethod
    def get_all_by_type_with_storage_owner(cls, type: int) -> List[Movement]:
        statement = (
            select(Movement)
            .options(
                joinedload(Movement.incoming_storage),
                joinedload(Movement.incoming_owner),
                joinedload(Movement.destination_storage),
                joinedload(Movement.destination_owner),
            )
            .where(Movement.type == type)
        )

        with rx.session() as session:
            movements = session.exec(statement).all()

            if len(movements) > 0:
                session.expunge_all()
            return list(movements)

    @classmethod
    def get_by_id_with_product_storage_owner(cls, id: str) -> Optional[Movement]:
        statement = (
            select(Movement)
            .options(
                selectinload(Movement.products_catalog).options(
                    joinedload(MovementProductsCatalog.product),
                    selectinload(MovementProductsCatalog.products),
                ),
                joinedload(Movement.incoming_storage),
                joinedload(Movement.incoming_owner),
                joinedload(Movement.destination_owner),
                joinedload(Movement.destination_storage),
            )
            .where(Movement.id == id)
        )

        with rx.session() as session:
            movement = session.exec(statement).one_or_none()

            if movement:
                session.expunge_all()
            return movement

    @classmethod
    def add_one(cls, form_data: dict) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                movement: Movement = Movement()
                movement.id_incoming_owner = form_data.get("id_incoming_owner")
                movement.id_incoming_storage = form_data.get("id_incoming_storage")
                movement.id_destination_owner = form_data.get("id_destination_owner")
                movement.id_destination_storage = form_data.get(
                    "id_destination_storage"
                )
                movement.type = form_data.get("type")
                movement.date = form_data.get("date")
                movement.comment = form_data.get("comment")
                movement.status = get_status_by_text(form_data.get("status"))
                movement.total_cost = 0.0
                movement.id_user = form_data["id_user"]

                products_catalog: List[ProductCatalog] = []
                movement_products_catalog: List[MovementProductsCatalog] = []
                products_list: List[Product] = form_data.get("movement_products_list")

                for product in products_list:
                    if product.product_catalog not in products_catalog:
                        products_catalog.append(
                            product.product_catalog
                        )  # FUTURES: можно оптимизировать

                for product_catalog in products_catalog:
                    movement_product_catalog: MovementProductsCatalog = (
                        MovementProductsCatalog(
                            id_movement=movement.id,
                            id_product_catalog=product_catalog.id,
                            count=0,
                            products=[],
                        )
                    )
                    for product in products_list:
                        if product.id_product_catalog == product_catalog.id:
                            movement_product_catalog.products.append(product)
                            movement_product_catalog.count += 1
                    movement_products_catalog.append(movement_product_catalog)

                movement.products_catalog = movement_products_catalog

                session.add(movement)
                session.commit()

                return True, "Движение товара успешно добавлено", movement.id

        except IntegrityError as e:
            print("[MovementDAO] IntegrityError: ", e)
            return False, "Ошибка: Движение товара не может быть добавлено", -1
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def edit_one(cls, form_data: dict) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                movement = session.get(Movement, form_data["id"])

                if movement is None:
                    return False, "Ошибка: Движение товара не найдено", -1

                for key, value in form_data.items():
                    setattr(movement, key, value)

                session.commit()
                session.refresh(movement)
                return True, "Движение товара успешно изменено", movement.id

        except IntegrityError as e:
            print("[MovementDAO] IntegrityError: ", e)
            return False, "Ошибка: Единица товара не может быть изменена", -1
        except SQLAlchemyError as e:
            print("[MovementDAO] SQLAlchemyError: ", e)
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def cancel_movement(cls, id: int) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                movement = session.get(Movement, id)

                if movement is None:
                    return False, "Ошибка: Движение товара не найдено"

                movement.status = MovementsStatus.CANCELED

                session.commit()
                return True, "Движение товара успешно отменено"

        except IntegrityError:
            return False, "Ошибка: Движение товара не может быть отменено"
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"


class MovementProductsCatalogDAO:
    @classmethod
    def get_all(cls) -> List[MovementProductsCatalog]:
        statement = select(MovementProductsCatalog)

        with rx.session() as session:
            movement_products_catalogs = session.exec(statement).all()

            if len(movement_products_catalogs) > 0:
                session.expunge_all()
            return list(movement_products_catalogs)

    @classmethod
    def get_by_id(cls, id: str) -> Optional[MovementProductsCatalog]:
        statement = select(MovementProductsCatalog).where(
            MovementProductsCatalog.id == id
        )

        with rx.session() as session:
            movement_products_catalog = session.exec(statement).one_or_none()

            if movement_products_catalog:
                session.expunge(movement_products_catalog)
            return movement_products_catalog

    @classmethod
    def add_one(cls, form_data: dict) -> tuple[bool, str, int]:
        movement_products_catalog = MovementProductsCatalog(**form_data)

        try:
            with rx.session() as session:
                session.add(movement_products_catalog)
                session.commit()
                session.refresh(movement_products_catalog)
                return True, "Товар успешно добавлен", movement_products_catalog.id

        except IntegrityError as e:
            print("[MovementProductsCatalogDAO] IntegrityError: ", e)
            return False, "Ошибка: Товар не может быть добавлен", -1
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def edit_one(cls, form_data: dict) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                movement_products_catalog = session.get(
                    MovementProductsCatalog, form_data["id"]
                )

                if movement_products_catalog is None:
                    return False, "Ошибка: Движение товара не найдено", -1

                for key, value in form_data.items():
                    setattr(movement_products_catalog, key, value)

                session.commit()
                session.refresh(movement_products_catalog)
                return (
                    True,
                    "Движение товара успешно изменено",
                    movement_products_catalog.id,
                )

        except IntegrityError as e:
            print("[MovementProductsCatalogDAO] IntegrityError: ", e)
            return False, "Ошибка: Единица товара не может быть изменена", -1
        except SQLAlchemyError as e:
            print("[MovementProductsCatalogDAO] SQLAlchemyError: ", e)
            return False, f"Ошибка: {str(e)}", -1


class PaymentTypeDAO:
    @classmethod
    def get_all(cls) -> List[PaymentType]:
        statement = select(PaymentType).where(PaymentType.is_deleted == False)

        with rx.session() as session:
            payment_types = session.exec(statement).all()

            if len(payment_types) > 0:
                session.expunge_all()
            return list(payment_types)

    @classmethod
    def get_by_id(cls, id: str) -> Optional[PaymentType]:
        statement = select(PaymentType).where(PaymentType.id == id)

        with rx.session() as session:
            payment_type = session.exec(statement).one_or_none()

            if payment_type:
                session.expunge(payment_type)
            return payment_type

    @classmethod
    def add_one(cls, form_data: dict) -> tuple[bool, str, int]:
        payment_type = PaymentType(**form_data)

        try:
            with rx.session() as session:
                statement = (
                    select(PaymentType)
                    .where(PaymentType.title == payment_type.title)
                    .where(PaymentType.is_deleted == False)
                )

                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Ошибка: Тип оплаты с таким названием уже существует",
                        -1,
                    )

                session.add(payment_type)
                session.commit()
                session.refresh(payment_type)
                return True, "Тип оплаты успешно добавлен", payment_type.id

        except IntegrityError as e:
            print("[PaymentTypeDAO] IntegrityError: ", e)
            return False, "Ошибка: Тип оплаты не может быть добавлен", -1
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def edit_one(cls, form_data: dict) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                payment_type = session.get(PaymentType, form_data["id"])

                if payment_type is None:
                    return False, "Ошибка: Тип оплаты не найден", -1

                for key, value in form_data.items():
                    setattr(payment_type, key, value)

                statement = (
                    select(PaymentType)
                    .where(PaymentType.title == payment_type.title)
                    .where(PaymentType.id != payment_type.id)
                    .where(PaymentType.is_deleted == False)
                )
                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Ошибка: Тип оплаты с таким названием уже существует",
                        payment_type.id,
                    )

                session.commit()
                session.refresh(payment_type)
                return True, "Тип оплаты успешно изменен", payment_type.id

        except IntegrityError as e:
            print("[PaymentTypeDAO] IntegrityError: ", e)
            return False, "Ошибка: Тип оплаты не может быть изменен", -1
        except SQLAlchemyError as e:
            print("[PaymentTypeDAO] SQLAlchemyError: ", e)
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def delete_one(cls, id: int) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                payment_type = session.get(PaymentType, id)

                if payment_type is None:
                    return False, "Ошибка: Тип оплаты не найден"

                payment_type.is_deleted = True
                session.commit()
                return True, "Тип оплаты успешно удален"

        except IntegrityError:
            return False, "Ошибка: Тип оплаты не может быть удален"
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"


class AdmissionDAO:
    @classmethod
    def get_all(cls) -> List[Admission]:
        statement = select(Admission)

        with rx.session() as session:
            return session.exec(statement).all()

    @classmethod
    def get_all_with_all_relationship(cls) -> List[Admission]:
        statement = select(Admission).options(
            joinedload(Admission.supplier),
            joinedload(Admission.payment_type),
            joinedload(Admission.movement).options(
                selectinload(Movement.products_catalog).options(
                    joinedload(MovementProductsCatalog.product),
                    selectinload(MovementProductsCatalog.products).options(
                        joinedload(Product.product_catalog),
                        joinedload(Product.owner),
                        joinedload(Product.storage),
                    ),
                ),
                joinedload(Movement.destination_storage),
                joinedload(Movement.destination_owner),
            ),
        )

        with rx.session() as session:
            admissions = session.exec(statement).all()

            if len(admissions) > 0:
                session.expunge_all()
            return list(admissions)

    @classmethod
    def get_all_with_supplier_movement_storage_owner(cls) -> List[Admission]:
        statement = select(Admission).options(
            joinedload(Admission.supplier),
            joinedload(Admission.payment_type),
            joinedload(Admission.movement).options(
                joinedload(Movement.destination_storage),
                joinedload(Movement.destination_owner),
            ),
        )

        with rx.session() as session:
            admissions = session.exec(statement).all()

            if len(admissions) > 0:
                session.expunge_all()
            return list(admissions)

    @classmethod
    def get_by_id(cls, id: str) -> Optional[Admission]:
        statement = select(Admission).where(Admission.id == id)

        with rx.session() as session:
            admission = session.exec(statement).one_or_none()

            if admission:
                session.expunge(admission)
            return admission

    @classmethod
    def get_by_id_with_all_relationship(cls, id: str) -> Optional[Admission]:
        statement = (
            select(Admission)
            .options(
                joinedload(Admission.supplier),
                joinedload(Admission.payment_type),
                joinedload(Admission.movement).options(
                    selectinload(Movement.products_catalog).options(
                        joinedload(MovementProductsCatalog.product),
                        selectinload(MovementProductsCatalog.products).options(
                            joinedload(Product.product_catalog),
                            joinedload(Product.owner),
                            joinedload(Product.storage),
                        ),
                    ),
                    joinedload(Movement.destination_storage),
                    joinedload(Movement.destination_owner),
                ),
            )
            .where(Admission.id == id)
        )

        with rx.session() as session:
            admission = session.exec(statement).one_or_none()

            if admission:
                session.expunge(admission)
            return admission

    @classmethod
    def get_by_id_with_supplier_movement_product_storage_owner(
        cls, id: str
    ) -> Optional[Admission]:
        statement = (
            select(Admission)
            .options(
                joinedload(Admission.supplier),
                joinedload(Admission.payment_type),
                joinedload(Admission.movement).options(
                    selectinload(Movement.products_catalog).options(
                        joinedload(MovementProductsCatalog.product),
                    ),
                    joinedload(Movement.destination_storage),
                    joinedload(Movement.destination_owner),
                ),
            )
            .where(Admission.id == id)
        )

        with rx.session() as session:
            admission = session.exec(statement).one_or_none()

            if admission:
                session.expunge(admission)
            return admission

    @classmethod
    def add_one(cls, movement: Admission) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                session.expire_on_commit = False
                session.add(movement)
                session.commit()
                return True, "Поставка успешно добавлена", movement.id

        except IntegrityError as e:
            print("[AdmissionDAO] IntegrityError: ", e)
            return False, "Ошибка: Поставка не может быть добавлена", -1
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def edit_one(cls, admission: Admission) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                session.merge(admission)
                session.commit()
                return True, "Движение товара успешно изменено", admission.id

        except IntegrityError as e:
            print("[AdmissionDAO] IntegrityError: ", e)
            return False, "Ошибка: Единица товара не может быть изменена", -1
        except SQLAlchemyError as e:
            print("[AdmissionDAO] SQLAlchemyError: ", e)
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def delete_one(cls, id: int) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                admission: Admission = session.get(Admission, id)
                movement: Movement = session.get(Movement, id)
                movements_products_catalog: Optional[List[MovementProductsCatalog]] = (
                    session.exec(
                        select(MovementProductsCatalog).where(
                            MovementProductsCatalog.id_movement == id
                        )
                    ).all()
                )
                products_in_movement: Optional[List[MovementProducts]] = session.exec(
                    select(MovementProducts).where(
                        MovementProducts.id_movement_product.in_(
                            [movement.id for movement in movements_products_catalog]
                        )
                    )
                ).all()
                products: Optional[List[Product]] = session.exec(
                    select(Product).where(
                        Product.id.in_(
                            [product.id_product for product in products_in_movement]
                        )
                    )
                ).all()

                other_movements_with_current_products: Optional[
                    List[MovementProducts]
                ] = session.exec(
                    select(MovementProducts)
                    .where(
                        MovementProducts.id_product.in_(
                            [product.id for product in products]
                        )
                    )
                    .where(
                        MovementProducts.id_movement_product.not_in(
                            [mpc.id for mpc in movements_products_catalog]
                        )
                    )
                ).all()

                if admission is None:
                    return False, "Ошибка: Поставка не найдена"

                if len(other_movements_with_current_products) > 0:
                    return (
                        False,
                        "Ошибка: Поставка не может быть удалена, так как товары уже используются в других движениях",
                    )

                for item in products_in_movement:
                    session.delete(item)
                for item in movements_products_catalog:
                    session.delete(item)
                session.delete(admission)
                session.delete(movement)

                for item in products:
                    session.delete(item)
                session.commit()
                return True, "Поставка успешно удалена"

        except IntegrityError as e:
            return False, f"Ошибка: Поставка не может быть удалена: {e}"
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"


class IssueDAO:
    @classmethod
    def get_all(cls) -> List[Issue]:
        statement = select(Issue)

        with rx.session() as session:
            issues = session.exec(statement).all()

            if len(issues) > 0:
                session.expunge_all()
            return list(issues)

    @classmethod
    def get_all_with_all_relationship(cls) -> List[Issue]:
        statement = select(Issue).options(
            joinedload(Issue.movement).options(
                selectinload(Movement.products_catalog).options(
                    joinedload(MovementProductsCatalog.product),
                    selectinload(MovementProductsCatalog.products).options(
                        joinedload(Product.product_catalog),
                        joinedload(Product.owner),
                        joinedload(Product.storage),
                    ),
                ),
                joinedload(Movement.incoming_storage),
                joinedload(Movement.incoming_owner),
            ),
            joinedload(Issue.recipient),
        )

        with rx.session() as session:
            issues = session.exec(statement).all()

            if len(issues) > 0:
                session.expunge_all()
            return list(issues)

    @classmethod
    def get_by_id(cls, id: str) -> Optional[Issue]:
        statement = select(Issue).where(Issue.id == id)

        with rx.session() as session:
            issue = session.exec(statement).one_or_none()

            if issue:
                session.expunge(issue)
            return issue

    @classmethod
    def get_by_id_with_all_relationship(cls, id: str) -> Optional[Issue]:
        statement = (
            select(Issue)
            .options(
                joinedload(Issue.movement).options(
                    selectinload(Movement.products_catalog).options(
                        joinedload(MovementProductsCatalog.product),
                        selectinload(MovementProductsCatalog.products).options(
                            joinedload(Product.product_catalog),
                            joinedload(Product.owner),
                            joinedload(Product.storage),
                        ),
                    ),
                    joinedload(Movement.incoming_storage),
                    joinedload(Movement.incoming_owner),
                    joinedload(Movement.destination_owner),
                    joinedload(Movement.destination_storage),
                ),
                joinedload(Issue.recipient),
            )
            .where(Issue.id == id)
        )

        with rx.session() as session:
            issue = session.exec(statement).one_or_none()

            if issue:
                session.expunge(issue)
            return issue

    @classmethod
    def get_by_id_with_movement_product_storage_owner_recipient(
        cls, id: str
    ) -> Optional[Issue]:
        statement = (
            select(Issue)
            .options(
                joinedload(Issue.movement).options(
                    selectinload(Movement.products_catalog).options(
                        joinedload(MovementProductsCatalog.product),
                        selectinload(MovementProductsCatalog.products),
                    ),
                    joinedload(Movement.incoming_storage),
                    joinedload(Movement.incoming_owner),
                    joinedload(Movement.destination_storage),
                ),
                joinedload(Issue.recipient),
            )
            .where(Issue.id == id)
        )

        with rx.session() as session:
            issue = session.exec(statement).one_or_none()

            if issue:
                session.expunge(issue)
            return issue

    @classmethod
    def add_one(cls, issue: Issue) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                session.expire_on_commit = False
                session.add(issue)
                session.commit()
                return True, "Выдача успешно добавлена", issue.id

        except IntegrityError as e:
            print("[IssueDAO] IntegrityError: ", e)
            return False, "Ошибка: Выдача не может быть добавлена", -1
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def edit_one(cls, issue: Issue) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                session.expire_on_commit = False
                session.add(issue)
                session.commit()
                return True, "Выдача успешно изменена", issue.id

        except IntegrityError as e:
            print("[IssueDAO] IntegrityError: ", e)
            return False, "Ошибка: Выдача не может быть изменена", -1
        except SQLAlchemyError as e:
            print("[IssueDAO] SQLAlchemyError: ", e)
            return False, f"Ошибка: {str(e)}", -1


class SaleDAO:
    @classmethod
    def get_all(cls) -> List[Sale]:
        statement = select(Sale)

        with rx.session() as session:
            sales = session.exec(statement).all()

            if len(sales) > 0:
                session.expunge_all()
            return list(sales)

    @classmethod
    def get_by_id(cls, id: str) -> Optional[Sale]:
        statement = select(Sale).where(Sale.id == id)

        with rx.session() as session:
            sale = session.exec(statement).one_or_none()

            if sale:
                session.expunge(sale)
            return sale

    @classmethod
    def add_one(cls, form_data: dict) -> tuple[bool, str, int]:
        sale = Sale(**form_data)

        try:
            with rx.session() as session:
                session.add(sale)
                session.commit()
                session.refresh(sale)
                return True, "Продажа успешно добавлена", sale.id

        except IntegrityError as e:
            print("[SaleDAO] IntegrityError: ", e)
            return False, "Ошибка: Продажа не может быть добавлена", -1
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def edit_one(cls, form_data: dict) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                sale = session.get(Sale, form_data["id"])

                if sale is None:
                    return False, "Ошибка: Продажа не найдена", -1

                for key, value in form_data.items():
                    setattr(sale, key, value)

                session.commit()
                session.refresh(sale)
                return True, "Продажа успешно изменена", sale.id

        except IntegrityError as e:
            print("[SaleDAO] IntegrityError: ", e)
            return False, "Ошибка: Продажа не может быть изменена", -1
        except SQLAlchemyError as e:
            print("[SaleDAO] SQLAlchemyError: ", e)
            return False, f"Ошибка: {str(e)}", -1
