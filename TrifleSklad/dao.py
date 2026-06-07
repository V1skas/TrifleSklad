from collections import OrderedDict
from typing import Dict, List, Optional

import reflex as rx
import math

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import select, func

from TrifleSklad.declared import MovementsStatus, MovementsType, RequestStatus
from TrifleSklad.models import (
    Action,
    Admission,
    AuthToken,
    Issue,
    Movement,
    MovementProducts,
    MovementProductsCatalog,
    NDSRate,
    Owner,
    PaymentType,
    Product,
    ProductCatalog,
    ProductCategory,
    Request,
    RequestProductsCatalog,
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
            return False, "Системна помилка! Користувач не може бути доданий.", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1

    @classmethod
    def edit_one(cls, user: User) -> tuple[bool, str, str]:
        try:
            with rx.session() as session:
                db_user = session.get(User, user.login)
                if db_user is None:
                    return False, "Помилка! Користувача не знайдено.", -1

                db_user.id_worker = user.id_worker
                db_user.salt = user.salt
                db_user.password_hash = user.password_hash
                db_user.is_deleted = user.is_deleted

                db_user.roles = [session.merge(r) for r in (user.roles or [])]
                db_user.actions = [session.merge(a) for a in (user.actions or [])]

                session.commit()
                return True, "Користувача змінено", db_user.login

        except IntegrityError as e:
            return False, "Помилка! Користувач не може бути змінений.", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1
        except Exception as e:
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
            return False, "Помилка! Користувач не може бути видалений.", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1
        except Exception as e:
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
            .options(selectinload(Role.actions))
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
            return False, "Системна помилка! Роль не може бути змінена.", -1
        except SQLAlchemyError as e:
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
            return False, "Системна помилка! Роль не може бути видалена."
        except SQLAlchemyError as e:
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
        statement = select(Worker).where(Worker.is_deleted == False)

        with rx.session() as session:
            workers = session.exec(statement).all()

            if len(workers) > 0:
                session.expunge_all()
            return list(workers)

    @classmethod
    def get_by_id(cls, id: str) -> Optional[Worker]:
        statement = select(Worker).where(Worker.id == id).where(Worker.is_deleted == False)

        with rx.session() as session:
            worker = session.exec(statement).one_or_none()

            if worker:
                session.expunge(worker)
            return worker

    @classmethod
    def get_by_fio(cls, fio: str) -> Optional[Worker]:
        statement = select(Worker).where(Worker.fio == fio).where(Worker.is_deleted == False)

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
                statement = (
                    select(Worker)
                    .where(Worker.fio == worker.fio)
                    .where(Worker.is_deleted == False)
                )

                if session.exec(statement).one_or_none() is not None:
                    return False, "Помилка! Співробітник з таким ПІБ вже існує!", -1

                session.add(worker)
                session.commit()
                session.refresh(worker)
                return True, "Співробітника додано!", worker.id

        except IntegrityError as e:
            return False, "Системна помилка! Співробітник не може бути доданий.", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1

    @classmethod
    def edit_one(cls, form_data: dict) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                worker = session.get(Worker, form_data["id"])

                if worker is None:
                    return False, "Помилка! Співробітника не знайдено.", -1

                for key, value in form_data.items():
                    setattr(worker, key, value)

                statement = (
                    select(Worker)
                    .where(Worker.fio == worker.fio)
                    .where(Worker.id != worker.id)
                    .where(Worker.is_deleted == False)
                )
                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Помилка! Співробітник з таким ПІБ вже існує!",
                        worker.id,
                    )

                session.commit()
                session.refresh(worker)
                return True, "Інформацію про співробітника змінено!", worker.id

        except IntegrityError as e:
            return False, "Системна помилка! Співробітник не може бути змінений.", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1
        except Exception as e:
            return False, "Системна помилка!", -1

    @classmethod
    def delete_one(cls, id: str) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                worker = session.get(Worker, id)

                if worker is None:
                    return False, "Помилка! Співробітника не знайдено."

                worker.is_deleted = True
                session.commit()
                return True, "Співробітника видалено!"

        except IntegrityError as e:
            return False, "Системна помилка! Співробітник не може бути видалений."
        except SQLAlchemyError as e:
            return False, "Системна помилка!"
        except Exception as e:
            return False, "Системна помилка!"


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
    def get_by_id(cls, id: int) -> Optional[ProductCategory]:
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
    def get_by_id_with_relationships(cls, id: int) -> Optional[ProductCategory]:
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
    def add_one(cls, category: ProductCategory) -> tuple[bool, str, int]:
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
                        "Помилка! Категорія з такою назвою вже існує!",
                        -1,
                    )

                session.add(category)
                session.commit()
                session.refresh(category)
                return True, "Категорію успішно додано!", category.id

        except IntegrityError as e:
            return False, "Системна помилка! Категорія не може бути додана!", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1

    @classmethod
    def edit_one(cls, category: ProductCategory) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                statement = (
                    select(ProductCategory)
                    .where(ProductCategory.title == category.title)
                    .where(ProductCategory.id != category.id)
                    .where(ProductCategory.is_deleted == False)
                )
                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Помилка! Категорія з такою назвою вже існує!",
                        category.id,
                    )
                category = session.merge(category)
                session.add(category)
                session.commit()
                session.refresh(category)
                return True, "Категорію успішно змінено!", category.id

        except IntegrityError as e:
            return False, "Системна помилка! Категорія не може бути змінена!", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1

    @classmethod
    def delete_one(cls, id: int) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                category = session.get(ProductCategory, id)

                if category is None:
                    return False, "Помилка! Категорію не знайдено!"

                category.is_deleted = True
                session.commit()
                return True, "Категорію успішно видалено!"

        except IntegrityError as e:
            return False, "Системна помилка! Категорія не може бути видалена!"
        except SQLAlchemyError as e:
            return False, "Системна помилка!"
        except Exception as e:
            return False, "Системна помилка!"


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
    def get_count_with_search(cls, search_str: Optional[str] = None) -> int:
        if search_str is not None and search_str.strip():
            condition = ProductCatalog.title.ilike(f"%{search_str.strip()}%")
        else:
            condition = True

        statement = select(func.count(ProductCatalog.id)).where(condition).where(ProductCatalog.is_deleted == False)

        with rx.session() as session:
            return session.exec(statement).one()
        
    @classmethod
    def get_all_with_relationships_by_page(cls, page: int = 1, count_items: int = 0, limit: int = 20, search_str: Optional[str] = None) -> tuple[int, List[ProductCatalog]]:
        if search_str is not None and search_str.strip():
            condition = ProductCatalog.title.ilike(f"%{search_str.strip()}%")
        else:
            condition = True

        total_pages = math.ceil(count_items / limit)
        if total_pages == 0:
            total_pages = 1

        skip = (page - 1) * limit
        
        statement = (
                select(ProductCatalog)
                .options(selectinload(ProductCatalog.category))
                .where(ProductCatalog.is_deleted == False)
                .where(condition)
                .offset(skip)
                .limit(limit)
            )

        with rx.session() as session:
            items = session.exec(statement).all()
            session.expunge_all()
            return total_pages, items

    @classmethod
    def get_by_id(cls, id: int) -> Optional[ProductCatalog]:
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
    def get_by_id_with_relationships(cls, id: int) -> Optional[ProductCatalog]:
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
    def get_by_category(cls, id_category) -> List[ProductCatalog]:
        statement = (
            select(ProductCatalog).where(ProductCatalog.id_category == id_category)
            .where(ProductCatalog.is_deleted == False)
        )

        with rx.session() as session:
            products = session.exec(statement).all()

            for product in products:
                session.expunge(product)
        return products

    @classmethod
    def get_list_units(cls) -> list[str]:
        statement = select(ProductCatalog.unit).distinct()
        
        with rx.session() as session:
            units_from_db = session.exec(statement).all()
            uniq_units = sorted([u.strip() for u in units_from_db if u])
            
        return uniq_units
        
    @classmethod
    def add_one(cls, product: ProductCatalog) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                statement = (
                    select(ProductCatalog)
                    .where(ProductCatalog.title == product.title)
                    .where(ProductCatalog.is_deleted == False)
                )

                if session.exec(statement).one_or_none() is not None:
                    return False, "Помилка! Товар з такою назвою вже існує!", -1

                session.add(product)
                session.commit()
                session.refresh(product)
                return True, "Товар додано!", product.id

        except IntegrityError as e:
            return False, "Системна помилка! Товар не може бути доданий!", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1
        except Exception as e:
            return False, "Системна помилка!", -1

    @classmethod
    def edit_one(cls, product: ProductCatalog) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                statement = (
                    select(ProductCatalog)
                    .where(ProductCatalog.title == product.title)
                    .where(ProductCatalog.id != product.id)
                    .where(ProductCatalog.is_deleted == False)
                )
                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Помилка! Товар з такою назвою вже існує!",
                        product.id,
                    )

                product = session.merge(product)
                session.add(product)
                session.commit()
                session.refresh(product)
                return True, "Товар успішно змінено!", product.id

        except IntegrityError as e:
            return False, "Системна помилка! Товар не може бути змінений!", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1
        except Exception as e:
            return False, "Системна помилка!", -1

    @classmethod
    def delete_one(cls, id: int) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                product = session.get(ProductCatalog, id)

                if product is None:
                    return False, "Помилка! Товар не знайдено"

                product.is_deleted = True
                session.commit()
                return True, "Товар видалено!"

        except IntegrityError as e:
            return False, "Системна помилка! Товар не може бути видалений!"
        except SQLAlchemyError as e:
            return False, "Системна помилка!"
        except Exception as e:
            return False, "Системна помилка!"


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
    def get_by_id(cls, id: int) -> Optional[Storage]:
        statement = (
            select(Storage).where(Storage.id == id).where(Storage.is_deleted == False)
        )

        with rx.session() as session:
            storage = session.exec(statement).one_or_none()

            if storage:
                session.expunge(storage)
            return storage

    @classmethod
    def get_by_id_with_relationships(cls, id: int) -> Optional[Storage]:
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
    def is_type(cls, id: int, types) -> bool:
        """True, якщо склад `id` існує (не видалений) і його тип входить у `types`
        (одне значення StorageType або колекція). Серверна перевірка типу місця
        зберігання для операцій руху."""
        if isinstance(types, int):
            types = (types,)
        statement = (
            select(Storage.type)
            .where(Storage.id == id)
            .where(Storage.is_deleted == False)
        )
        with rx.session() as session:
            storage_type = session.exec(statement).one_or_none()
        return storage_type is not None and storage_type in types

    @classmethod
    def add_one(cls, storage: Storage) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                statement = (
                    select(Storage)
                    .where(Storage.title == storage.title)
                    .where(Storage.is_deleted == False)
                )

                if session.exec(statement).one_or_none() is not None:
                    return False, "Помилка! Місце зберігання з такою назвою вже існує!", -1

                session.add(storage)
                session.commit()
                session.refresh(storage)
                return True, "Склад успішно додано!", storage.id

        except IntegrityError as e:
            return False, "Системна помилка! Склад не може бути доданий!", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1

    @classmethod
    def edit_one(cls, storage: Storage) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                statement = (
                    select(Storage)
                    .where(Storage.title == storage.title)
                    .where(Storage.id != storage.id)
                    .where(Storage.is_deleted == False)
                )
                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Помилка! Склад з такою назвою вже існує!",
                        storage.id,
                    )

                storage = session.merge(storage)
                session.add(storage)
                session.commit()
                session.refresh(storage)
                return True, "Склад успішно змінено!", storage.id

        except IntegrityError as e:
            return False, "Системна помилка! Склад не може бути змінено!", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1

    @classmethod
    def delete_one(cls, id: int) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                storage = session.get(Storage, id)

                if storage is None:
                    return False, "Помилка! Склад не знайдено!"

                storage.is_deleted = True
                session.commit()
                return True, "Склад видалено!"

        except IntegrityError as e:
            return False, "Системна помилка! Склад не може бути видалено!"
        except Exception as e:
            return False, "Системна помилка!"


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
    def add_one(cls, owner: Owner) -> tuple[bool, str, int]:
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
                        "Помилка! Власник з такою назвою вже існує!",
                        -1,
                    )

                session.add(owner)
                session.commit()
                session.refresh(owner)
                return True, "Власника успішно додано!", owner.id

        except IntegrityError as e:
            return False, "Помилка! Власника не може бути додано!", -1
        except SQLAlchemyError as e:
            return False, "Помилка!", -1

    @classmethod
    def edit_one(cls, owner: Owner) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                statement = (
                    select(Owner)
                    .where(Owner.title == owner.title)
                    .where(Owner.id != owner.id)
                    .where(Owner.is_deleted == False)
                )
                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Помилка! Власник з такою назвою вже існує!",
                        owner.id,
                    )

                owner = session.merge(owner)
                session.add(owner)
                session.commit()
                session.refresh(owner)
                return True, "Інформацію про власника успішно змінено!", owner.id

        except IntegrityError as e:
            return False, "Помилка! Інформація про власника не може бути змінена!", -1
        except SQLAlchemyError as e:
            return False, "Помилка!", -1

    @classmethod
    def delete_one(cls, id: int) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                owner = session.get(Owner, id)

                if owner is None:
                    return False, "Помилка! Власника не знайдено!"

                owner.is_deleted = True
                session.commit()
                return True, "Інформація про власника видалена!"

        except IntegrityError as e:
            return False, "Помилка! Інформація про власника не може бути видалена!"
        except SQLAlchemyError as e:
            return False, "Помилка!"
        except Exception as e:
            return False, "Помилка!"


class SupplierDAO:
    @classmethod
    def get_all(cls) -> List[Supplier]:
        statement = select(Supplier).where(Supplier.is_deleted == False)

        with rx.session() as session:
            return session.exec(statement).all()

    @classmethod
    def get_by_id(cls, id: int) -> Optional[Supplier]:
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
    def add_one(cls, supplier: Supplier) -> tuple[bool, str, int]:
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
                        "Помилка! Постачальник з такою назвою вже існує!",
                        -1,
                    )

                session.add(supplier)
                session.commit()
                session.refresh(supplier)
                return True, "Постачальника додано!", supplier.id

        except IntegrityError as e:
            return False, "Помилка! Інформація про постачальника не може бути додана!", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1
        except Exception as e:
            return False, "Системна помилка!", -1

    @classmethod
    def edit_one(cls, supplier: Supplier) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                statement = (
                    select(Supplier)
                    .where(Supplier.title == supplier.title)
                    .where(Supplier.id != supplier.id)
                    .where(Supplier.is_deleted == False)
                )
                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Помилка! Постачальник з такою назвою вже існує!",
                        supplier.id,
                    )

                supplier = session.merge(supplier)
                session.add(supplier)
                session.commit()
                session.refresh(supplier)
                return True, "Інформація про постачальника змінена!", supplier.id

        except IntegrityError as e:
            return False, "Помилка! Інформація про постачальника не може бути змінена!", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1
        except Exception as e:
            return False, "Системна помилка!", -1

    @classmethod
    def delete_one(cls, id: int) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                supplier = session.get(Supplier, id)

                if supplier is None:
                    return False, "Помилка! Постачальника не знайдено!"

                supplier.is_deleted = True
                session.commit()
                return True, "Інформація про постачальника видалена!"

        except IntegrityError as e:
            return False, "Помилка! Інформація про постачальника не може бути видалена!"
        except SQLAlchemyError as e:
            return False, "Системна помилка!"
        except Exception as e:
            return False, "Системна помилка!"


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
        # owner_id == -1 — без фільтра за власником (напр. повернення з площадки:
        # на місці лежить ТМЦ різних власників, кожна одиниця зберігає свого).
        statement = (
            select(Product)
            .options(joinedload(Product.product_catalog))
            .where(Product.id_storage == storage_id)
            .where(Product.is_deleted == False)
        )
        if owner_id != -1:
            statement = statement.where(Product.id_owner == owner_id)

        with rx.session() as session:
            products = session.exec(statement).all()

            if len(products) > 0:
                session.expunge_all()
            return list(products)

    @classmethod
    def count_by_storage(cls, storage_id: int) -> int:
        statement = (
            select(func.count(Product.id))
            .where(Product.id_storage == storage_id)
            .where(Product.is_deleted == False)
        )

        with rx.session() as session:
            return session.exec(statement).one()

    @classmethod
    def count_by_owner(cls, owner_id: int) -> int:
        statement = (
            select(func.count(Product.id))
            .where(Product.id_owner == owner_id)
            .where(Product.is_deleted == False)
        )

        with rx.session() as session:
            return session.exec(statement).one()

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
            return False, "Ошибка: Единица товара не может быть изменена", -1
        except SQLAlchemyError as e:
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
    def split_product(
        cls, parent_id: int, amount: int
    ) -> tuple[bool, str, Optional[Product]]:
        """Відділяє від подільної одиниці товару частину обсягом `amount`:
        створює нову дочірню одиницю (id_parent = parent_id) із вказаним count
        у тому ж місці зберігання, а в батьківської одиниці зменшує count.
        Заборонено відділяти весь обсяг (amount має бути < поточного count)."""
        try:
            with rx.session() as session:
                parent = session.get(Product, parent_id)
                if parent is None:
                    return False, "Помилка: одиницю товару не знайдено", None
                if amount < 1 or amount >= parent.count:
                    return (
                        False,
                        "Помилка: некоректний обсяг для розділення одиниці товару",
                        None,
                    )

                child = Product(
                    serial_number=parent.serial_number,
                    id_product_catalog=parent.id_product_catalog,
                    id_storage=parent.id_storage,
                    id_owner=parent.id_owner,
                    id_parent=parent.id,
                    count=amount,
                    is_deleted=False,
                )
                parent.count -= amount

                session.add(child)
                session.add(parent)
                session.commit()
                session.refresh(child)
                session.expunge(child)
                return True, "Одиницю товару розділено", child

        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}", None

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

    @classmethod
    def apply_issue_relocation(
        cls, products: List[Product], new_owner_id: int, new_storage_id: int
    ) -> tuple[bool, str]:
        """Фіналізує одиниці ТМЦ при видачі на площадку/відділ. Видача без
        окремого руху списання фіксується самим рухом видачі:
        - **витратний** (неунікальний) ТМЦ — подільний або неподільний без
          серійного номера — списується на місці (is_deleted), бо вважається
          спожитим;
        - **унікальний** (із серійним номером) ТМЦ — переміщується на призначення
          як відстежуване обладнання.
        `products` — перелік Product із завантаженим зв'язком product_catalog
        (для перевірки uniq). Невідомий каталог (None) — про всяк випадок
        переміщується, а не списується."""
        write_off_ids = [
            p.id
            for p in products
            if p.product_catalog is not None and not p.product_catalog.uniq
        ]
        movable_ids = [p.id for p in products if p.id not in write_off_ids]
        if write_off_ids:
            flag, text = cls.delete_list(write_off_ids)
            if not flag:
                return flag, text
        if movable_ids:
            flag, text = cls.update_owner_storage(
                movable_ids, new_owner_id, new_storage_id
            )
            if not flag:
                return flag, text
        return True, "Единицы товара обработаны"

    @classmethod
    def update_storage(cls, id_list: List[int], new_storage_id: int) -> tuple[bool, str]:
        """Оновлює лише місце зберігання одиниць, не чіпаючи власника
        (повернення з площадки/відділу на склад — власник лишається той самий)."""
        try:
            with rx.session() as session:
                statement = select(Product).where(Product.id.in_(id_list))
                products = session.exec(statement).all()

                for product in products:
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

    @classmethod
    def update_serial_numbers(cls, serials: Dict[int, str]) -> tuple[bool, str]:
        if not serials:
            return True, ""
        try:
            with rx.session() as session:
                statement = select(Product).where(Product.id.in_(list(serials.keys())))
                products = session.exec(statement).all()

                for product in products:
                    if product.id in serials:
                        product.serial_number = serials[product.id]
                        session.add(product)

                session.commit()
                return True, "Серійні номери оновлено"

        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}"
        except Exception as e:
            return False, f"Ошибка: {str(e)}"


def movement_filter_conditions(
    date_from: str = "",
    date_to: str = "",
    statuses: Optional[List[int]] = None,
) -> list:
    """Список SQLAlchemy-умов фільтрації рухів за датою (рядок ISO) і статусами.
    Спільний для всіх типів руху (поступлення/списання/переміщення/видача/продаж)."""
    conditions = []
    if date_from:
        conditions.append(Movement.date >= date_from)
    if date_to:
        conditions.append(Movement.date <= date_to)
    if statuses:
        conditions.append(Movement.status.in_(statuses))
    return conditions


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
    def get_by_type_paginated(
        cls,
        type: int,
        page: int = 1,
        limit: int = 20,
        date_from: str = "",
        date_to: str = "",
        statuses: Optional[List[int]] = None,
    ) -> tuple[int, List[Movement]]:
        """Сторінкований перелік рухів одного типу з фільтром за датою/статусами.
        Дата — рядок ISO 'YYYY-MM-DD', лексикографічне порівняння коректне."""
        conditions = movement_filter_conditions(date_from, date_to, statuses)

        count_stmt = select(func.count(Movement.id)).where(Movement.type == type)
        for cond in conditions:
            count_stmt = count_stmt.where(cond)

        with rx.session() as session:
            total = session.exec(count_stmt).one()
            total_pages = max(1, math.ceil(total / limit))
            skip = (max(1, page) - 1) * limit

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
            for cond in conditions:
                statement = statement.where(cond)
            statement = statement.order_by(Movement.id.desc()).offset(skip).limit(limit)

            movements = session.exec(statement).all()
            if len(movements) > 0:
                session.expunge_all()
            return total_pages, list(movements)

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
                movement.status = form_data.get("status")
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
            return False, "Ошибка: Единица товара не может быть изменена", -1
        except SQLAlchemyError as e:
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

    @classmethod
    def get_with_products_from_id(
        cls, product_ids: List[int], from_movement_id: int
    ) -> List[Movement]:
        """Движения, в которые входят указанные товары, начиная с from_movement_id
        (включительно), отсортированные по возрастанию id (порядку создания)."""
        if len(product_ids) == 0:
            return []

        statement = (
            select(Movement)
            .join(
                MovementProductsCatalog,
                MovementProductsCatalog.id_movement == Movement.id,
            )
            .join(
                MovementProducts,
                MovementProducts.id_movement_product == MovementProductsCatalog.id,
            )
            .where(MovementProducts.id_product.in_(product_ids))
            .where(Movement.id >= from_movement_id)
            .distinct()
            .order_by(Movement.id)
        )

        with rx.session() as session:
            movements = session.exec(statement).all()

            if len(movements) > 0:
                session.expunge_all()
            return list(movements)

    @classmethod
    def restore_products_to_previous_location(
        cls, product_ids: List[int], current_movement_id: int
    ) -> tuple[bool, str]:
        """Повертає кожну одиницю товару на місце, куди її привів попередній рух —
        рух із максимальним id < current_movement_id, що містить цю одиницю і не
        скасований. За точку призначення береться destination_owner/destination_storage
        того руху (наскрізна нумерація рухів = порядок у часі). Якщо попереднього руху
        немає або в нього не задано місце призначення — одиниця залишається на місці."""
        if len(product_ids) == 0:
            return True, "Нет единиц для возврата"
        try:
            with rx.session() as session:
                for product_id in product_ids:
                    statement = (
                        select(Movement)
                        .join(
                            MovementProductsCatalog,
                            MovementProductsCatalog.id_movement == Movement.id,
                        )
                        .join(
                            MovementProducts,
                            MovementProducts.id_movement_product
                            == MovementProductsCatalog.id,
                        )
                        .where(MovementProducts.id_product == product_id)
                        .where(Movement.id < current_movement_id)
                        .where(Movement.status != MovementsStatus.CANCELED)
                        .order_by(Movement.id.desc())
                        .limit(1)
                    )
                    previous = session.exec(statement).first()
                    if previous is None:
                        continue
                    if (
                        previous.id_destination_owner is None
                        or previous.id_destination_storage is None
                    ):
                        continue

                    product = session.get(Product, product_id)
                    if product is None:
                        continue
                    product.id_owner = previous.id_destination_owner
                    product.id_storage = previous.id_destination_storage
                    session.add(product)

                session.commit()
                return True, "Единицы товара возвращены на предыдущее место"

        except SQLAlchemyError as e:
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
            return False, "Ошибка: Единица товара не может быть изменена", -1
        except SQLAlchemyError as e:
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
        statement = (
            select(PaymentType)
            .where(PaymentType.id == id)
            .where(PaymentType.is_deleted == False)
        )

        with rx.session() as session:
            payment_type = session.exec(statement).one_or_none()

            if payment_type:
                session.expunge(payment_type)
            return payment_type

    @classmethod
    def add_one(cls, payment_type: PaymentType) -> tuple[bool, str, int]:
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
                        "Помилка! Тип оплати з такою назвою вже існує!",
                        -1,
                    )

                session.add(payment_type)
                session.commit()
                session.refresh(payment_type)
                return True, "Тип оплати додано!", payment_type.id

        except IntegrityError as e:
            return False, "Системна помилка! Тип оплати не може бути доданий!", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1

    @classmethod
    def edit_one(cls, payment_type: PaymentType) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                statement = (
                    select(PaymentType)
                    .where(PaymentType.title == payment_type.title)
                    .where(PaymentType.id != payment_type.id)
                    .where(PaymentType.is_deleted == False)
                )
                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Помилка! Тип оплати з такою назвою вже існує!",
                        payment_type.id,
                    )

                payment_type = session.merge(payment_type)
                session.add(payment_type)
                session.commit()
                session.refresh(payment_type)
                return True, "Тип оплати змінено!", payment_type.id

        except IntegrityError as e:
            return False, "Системна помилка! Тип оплати не може бути змінений!", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1

    @classmethod
    def delete_one(cls, id: int) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                payment_type = session.get(PaymentType, id)

                if payment_type is None:
                    return False, "Помилка! Тип оплати не знайдено!"

                payment_type.is_deleted = True
                session.commit()
                return True, "Тип оплати видалено!"

        except IntegrityError as e:
            return False, "Системна помилка! Тип оплати не може бути видалений!"
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1
        except Exception as e:
            return False, "Системна помилка!", -1


class NDSRateDAO:
    @classmethod
    def get_all(cls) -> List[NDSRate]:
        statement = select(NDSRate).where(NDSRate.is_deleted == False)

        with rx.session() as session:
            rates = session.exec(statement).all()

            if len(rates) > 0:
                session.expunge_all()
            return list(rates)

    @classmethod
    def get_by_id(cls, id: int) -> Optional[NDSRate]:
        statement = (
            select(NDSRate)
            .where(NDSRate.id == id)
            .where(NDSRate.is_deleted == False)
        )

        with rx.session() as session:
            rate = session.exec(statement).one_or_none()

            if rate:
                session.expunge(rate)
            return rate

    @classmethod
    def add_one(cls, nds_rate: NDSRate) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                statement = (
                    select(NDSRate)
                    .where(NDSRate.title == nds_rate.title)
                    .where(NDSRate.is_deleted == False)
                )

                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Помилка! Ставка ПДВ з такою назвою вже існує!",
                        -1,
                    )

                session.add(nds_rate)
                session.commit()
                session.refresh(nds_rate)
                return True, "Ставку ПДВ додано!", nds_rate.id

        except IntegrityError as e:
            return False, "Системна помилка! Ставка ПДВ не може бути додана!", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1

    @classmethod
    def edit_one(cls, nds_rate: NDSRate) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                statement = (
                    select(NDSRate)
                    .where(NDSRate.title == nds_rate.title)
                    .where(NDSRate.id != nds_rate.id)
                    .where(NDSRate.is_deleted == False)
                )
                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Помилка! Ставка ПДВ з такою назвою вже існує!",
                        nds_rate.id,
                    )

                nds_rate = session.merge(nds_rate)
                session.add(nds_rate)
                session.commit()
                session.refresh(nds_rate)
                return True, "Ставку ПДВ змінено!", nds_rate.id

        except IntegrityError as e:
            return False, "Системна помилка! Ставка ПДВ не може бути змінена!", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1

    @classmethod
    def delete_one(cls, id: int) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                nds_rate = session.get(NDSRate, id)

                if nds_rate is None:
                    return False, "Помилка! Ставку ПДВ не знайдено!"

                nds_rate.is_deleted = True
                session.commit()
                return True, "Ставку ПДВ видалено!"

        except IntegrityError as e:
            return False, "Системна помилка! Ставка ПДВ не може бути видалена!"
        except SQLAlchemyError as e:
            return False, "Системна помилка!"
        except Exception as e:
            return False, "Системна помилка!"


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
            joinedload(Admission.nds_rate),
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
            joinedload(Admission.nds_rate),
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
    def get_paginated(
        cls,
        page: int = 1,
        limit: int = 20,
        date_from: str = "",
        date_to: str = "",
        statuses: Optional[List[int]] = None,
    ) -> tuple[int, List[Admission]]:
        conditions = movement_filter_conditions(date_from, date_to, statuses)
        movement_ids = select(Movement.id)
        for cond in conditions:
            movement_ids = movement_ids.where(cond)

        with rx.session() as session:
            total = session.exec(
                select(func.count(Admission.id)).where(Admission.id.in_(movement_ids))
            ).one()
            total_pages = max(1, math.ceil(total / limit))
            skip = (max(1, page) - 1) * limit

            statement = (
                select(Admission)
                .options(
                    joinedload(Admission.supplier),
                    joinedload(Admission.payment_type),
                    joinedload(Admission.nds_rate),
                    joinedload(Admission.movement).options(
                        joinedload(Movement.destination_storage),
                        joinedload(Movement.destination_owner),
                    ),
                )
                .where(Admission.id.in_(movement_ids))
                .order_by(Admission.id.desc())
                .offset(skip)
                .limit(limit)
            )
            admissions = session.exec(statement).all()
            if len(admissions) > 0:
                session.expunge_all()
            return total_pages, list(admissions)

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
                joinedload(Admission.nds_rate),
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
    def is_invoice_number_exists(cls, invoice_number: str, exclude_id: Optional[int] = None) -> bool:
        if invoice_number is None or not invoice_number.strip():
            return False

        statement = select(Admission).where(Admission.invoice_number == invoice_number.strip())
        if exclude_id is not None:
            statement = statement.where(Admission.id != exclude_id)

        with rx.session() as session:
            return session.exec(statement).first() is not None

    @classmethod
    def add_one(cls, movement: Admission) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                session.expire_on_commit = False
                session.add(movement)
                session.commit()
                return True, "Постачання успішно додано!", movement.id

        except IntegrityError as e:
            return False, "Помилка! Постачання не може бути додано.", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1

    @classmethod
    def edit_one(cls, admission: Admission) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                session.merge(admission)
                session.commit()
                return True, "Постачання успішно змінено!", admission.id

        except IntegrityError as e:
            return False, "Помилка! Постачання не може бути змінено.", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1

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
                    return False, "Помилка! Постачання не знайдено."

                if len(other_movements_with_current_products) > 0:
                    return (
                        False,
                        "Помилка! Постачання не може бути видалено, оскільки товари вже використовуються в інших рухах.",
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
                return True, "Постачання успішно видалено!"

        except IntegrityError as e:
            return False, "Помилка! Постачання не може бути видалено."
        except SQLAlchemyError as e:
            return False, "Системна помилка!"
        except Exception as e:
            return False, "Системна помилка!"


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
    def get_paginated(
        cls,
        page: int = 1,
        limit: int = 20,
        date_from: str = "",
        date_to: str = "",
        statuses: Optional[List[int]] = None,
    ) -> tuple[int, List[Issue]]:
        conditions = movement_filter_conditions(date_from, date_to, statuses)
        movement_ids = select(Movement.id)
        for cond in conditions:
            movement_ids = movement_ids.where(cond)

        with rx.session() as session:
            total = session.exec(
                select(func.count(Issue.id)).where(Issue.id.in_(movement_ids))
            ).one()
            total_pages = max(1, math.ceil(total / limit))
            skip = (max(1, page) - 1) * limit

            statement = (
                select(Issue)
                .options(
                    joinedload(Issue.movement).options(
                        joinedload(Movement.incoming_storage),
                        joinedload(Movement.incoming_owner),
                        joinedload(Movement.destination_storage),
                    ),
                    joinedload(Issue.recipient),
                )
                .where(Issue.id.in_(movement_ids))
                .order_by(Issue.id.desc())
                .offset(skip)
                .limit(limit)
            )
            issues = session.exec(statement).all()
            if len(issues) > 0:
                session.expunge_all()
            return total_pages, list(issues)

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
            return False, "Ошибка: Выдача не может быть добавлена", -1
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def edit_one(cls, issue: Issue) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                session.expire_on_commit = False
                session.merge(issue)
                session.commit()
                return True, "Выдача успешно изменена", issue.id

        except IntegrityError as e:
            return False, "Ошибка: Выдача не может быть изменена", -1
        except SQLAlchemyError as e:
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
    def get_all_with_all_relationship(cls) -> List[Sale]:
        statement = select(Sale).options(
            joinedload(Sale.movement).options(
                selectinload(Movement.products_catalog).options(
                    joinedload(MovementProductsCatalog.product),
                    selectinload(MovementProductsCatalog.products).options(
                        joinedload(Product.product_catalog),
                    ),
                ),
                joinedload(Movement.incoming_storage),
                joinedload(Movement.incoming_owner),
            ),
            joinedload(Sale.responsible),
        )

        with rx.session() as session:
            sales = session.exec(statement).all()

            if len(sales) > 0:
                session.expunge_all()
            return list(sales)

    @classmethod
    def get_paginated(
        cls,
        page: int = 1,
        limit: int = 20,
        date_from: str = "",
        date_to: str = "",
        statuses: Optional[List[int]] = None,
    ) -> tuple[int, List[Sale]]:
        conditions = movement_filter_conditions(date_from, date_to, statuses)
        movement_ids = select(Movement.id)
        for cond in conditions:
            movement_ids = movement_ids.where(cond)

        with rx.session() as session:
            total = session.exec(
                select(func.count(Sale.id)).where(Sale.id.in_(movement_ids))
            ).one()
            total_pages = max(1, math.ceil(total / limit))
            skip = (max(1, page) - 1) * limit

            statement = (
                select(Sale)
                .options(
                    joinedload(Sale.movement).options(
                        joinedload(Movement.incoming_storage),
                        joinedload(Movement.incoming_owner),
                    ),
                    joinedload(Sale.responsible),
                )
                .where(Sale.id.in_(movement_ids))
                .order_by(Sale.id.desc())
                .offset(skip)
                .limit(limit)
            )
            sales = session.exec(statement).all()
            if len(sales) > 0:
                session.expunge_all()
            return total_pages, list(sales)

    @classmethod
    def get_by_id(cls, id: str) -> Optional[Sale]:
        statement = select(Sale).where(Sale.id == id)

        with rx.session() as session:
            sale = session.exec(statement).one_or_none()

            if sale:
                session.expunge(sale)
            return sale

    @classmethod
    def get_by_id_with_all_relationship(cls, id: str) -> Optional[Sale]:
        statement = (
            select(Sale)
            .options(
                joinedload(Sale.movement).options(
                    selectinload(Movement.products_catalog).options(
                        joinedload(MovementProductsCatalog.product),
                        selectinload(MovementProductsCatalog.products).options(
                            joinedload(Product.product_catalog),
                        ),
                    ),
                    joinedload(Movement.incoming_storage),
                    joinedload(Movement.incoming_owner),
                ),
                joinedload(Sale.responsible),
            )
            .where(Sale.id == id)
        )

        with rx.session() as session:
            sale = session.exec(statement).one_or_none()

            if sale:
                session.expunge(sale)
            return sale

    @classmethod
    def add_one(cls, form_data: dict) -> tuple[bool, str, int]:
        """Створює продаж: будує поліморфний Movement (тип SALE), його позиції
        (MovementProductsCatalog з ціною за позицією) і дочірній запис Sale.
        `movement_products_list` — підсумковий перелік одиниць ТМЦ, `prices` —
        ціна за одиницю за ключем id позиції каталогу."""
        try:
            with rx.session() as session:
                prices: Dict[int, float] = form_data.get("prices", {})

                movement: Movement = Movement(
                    type=MovementsType.SALE,
                    id_user=form_data["id_user"],
                    id_incoming_storage=form_data.get("id_incoming_storage"),
                    id_incoming_owner=form_data.get("id_incoming_owner"),
                    date=form_data.get("date"),
                    comment=form_data.get("comment"),
                    status=form_data.get("status"),
                    total_cost=0.0,
                )

                # Групуємо за колонкою id_product_catalog (завжди завантажена),
                # не чіпаючи ліниву зв'язку product_catalog у відокремлених інстансів.
                # Самі ж одиниці ТМЦ перечитуємо в межах поточної сесії за id —
                # інакше зв'язування відокремлених інстансів дає DetachedInstanceError.
                products_list: List[Product] = form_data.get("movement_products_list", [])
                catalog_to_ids: "OrderedDict[int, List[int]]" = OrderedDict()
                for product in products_list:
                    catalog_to_ids.setdefault(product.id_product_catalog, []).append(
                        product.id
                    )

                all_ids = [pid for ids in catalog_to_ids.values() for pid in ids]
                bound_products = {
                    p.id: p
                    for p in session.exec(
                        select(Product).where(Product.id.in_(all_ids))
                    ).all()
                }

                movement_products_catalog: List[MovementProductsCatalog] = []
                total_cost = 0.0
                for catalog_id, ids in catalog_to_ids.items():
                    price = float(prices.get(catalog_id, 0.0))
                    units = [bound_products[i] for i in ids if i in bound_products]
                    movement_products_catalog.append(
                        MovementProductsCatalog(
                            id_product_catalog=catalog_id,
                            count=len(units),
                            price=price,
                            products=units,
                        )
                    )
                    total_cost += price * len(units)

                movement.products_catalog = movement_products_catalog
                movement.total_cost = total_cost

                sale: Sale = Sale(
                    id_responsible=form_data["id_responsible"],
                    movement=movement,
                )

                session.add(sale)
                session.commit()
                return True, "Продаж успішно додано", sale.id

        except IntegrityError as e:
            return False, "Помилка: Продаж не може бути додано", -1
        except SQLAlchemyError as e:
            return False, f"Помилка: {str(e)}", -1

    @classmethod
    def edit_one(cls, form_data: dict) -> tuple[bool, str, int]:
        """Редагування продажу: змінюються лише статус і коментар руху
        (склад/власник/позиції продажу не редагуються)."""
        try:
            with rx.session() as session:
                sale = session.get(Sale, form_data["id"])
                if sale is None:
                    return False, "Помилка: Продаж не знайдено", -1

                movement = session.get(Movement, form_data["id"])
                if movement is None:
                    return False, "Помилка: Рух товару не знайдено", -1

                if "status" in form_data:
                    movement.status = form_data["status"]
                if "comment" in form_data:
                    movement.comment = form_data["comment"]

                session.commit()
                return True, "Продаж успішно змінено", sale.id

        except IntegrityError as e:
            return False, "Помилка: Продаж не може бути змінено", -1
        except SQLAlchemyError as e:
            return False, f"Помилка: {str(e)}", -1


class RequestDAO:
    @classmethod
    def get_paginated(
        cls,
        page: int = 1,
        limit: int = 20,
        statuses: Optional[List[int]] = None,
        author_login: Optional[str] = None,
    ) -> tuple[int, List[Request]]:
        """Сторінкований перелік заявок. `statuses` — фільтр за статусом,
        `author_login` (якщо задано) обмежує вибірку заявками цього автора
        (для користувача без права бачити всі заявки)."""
        conditions = [Request.is_deleted == False]
        if statuses:
            conditions.append(Request.status.in_(statuses))
        if author_login is not None:
            conditions.append(Request.id_author == author_login)

        count_stmt = select(func.count(Request.id))
        for cond in conditions:
            count_stmt = count_stmt.where(cond)

        with rx.session() as session:
            total = session.exec(count_stmt).one()
            total_pages = max(1, math.ceil(total / limit))
            skip = (max(1, page) - 1) * limit

            statement = select(Request).options(
                joinedload(Request.author).joinedload(User.worker),
                joinedload(Request.responsible),
                joinedload(Request.destination_storage),
            )
            for cond in conditions:
                statement = statement.where(cond)
            statement = statement.order_by(Request.id.desc()).offset(skip).limit(limit)

            requests = session.exec(statement).all()
            if len(requests) > 0:
                session.expunge_all()
            return total_pages, list(requests)

    @classmethod
    def get_open_by_type(cls, type: int) -> List[Request]:
        """Невиконані заявки заданого типу (для формування руху на їх основі):
        статус «Нова», не видалені, ще не зв'язані з рухом. З завантаженими
        отримувачем, призначенням та позиціями каталогу."""
        statement = (
            select(Request)
            .options(
                joinedload(Request.responsible),
                joinedload(Request.destination_storage),
                selectinload(Request.products_catalog).joinedload(
                    RequestProductsCatalog.product
                ),
            )
            .where(Request.is_deleted == False)
            .where(Request.type == type)
            .where(Request.status == RequestStatus.NEW)
            .where(Request.id_movement == None)  # noqa: E711
            .order_by(Request.id.desc())
        )

        with rx.session() as session:
            requests = session.exec(statement).unique().all()
            if len(requests) > 0:
                session.expunge_all()
            return list(requests)

    @classmethod
    def get_by_id_with_relationships(cls, id: int) -> Optional[Request]:
        statement = (
            select(Request)
            .options(
                joinedload(Request.author).joinedload(User.worker),
                joinedload(Request.responsible),
                joinedload(Request.destination_storage),
                joinedload(Request.movement),
                selectinload(Request.products_catalog).joinedload(
                    RequestProductsCatalog.product
                ),
            )
            .where(Request.id == id)
            .where(Request.is_deleted == False)
        )

        with rx.session() as session:
            request = session.exec(statement).unique().one_or_none()
            if request is not None:
                session.expunge_all()
            return request

    @classmethod
    def add_one(cls, request: Request) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                session.expire_on_commit = False
                session.add(request)
                session.commit()
                return True, "Заявку успішно створено!", request.id

        except IntegrityError as e:
            return False, "Помилка! Заявка не може бути створена.", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1

    @classmethod
    def edit_one(cls, form_data: dict) -> tuple[bool, str, int]:
        """Редагування заявки (лише невиконаної): тип/отримувач/призначення/
        коментар + перелік позицій. Позиції повністю перестворюються."""
        try:
            with rx.session() as session:
                request = session.get(Request, form_data["id"])
                if request is None:
                    return False, "Помилка: заявку не знайдено", -1
                if request.status == RequestStatus.COMPLETED:
                    return False, "Помилка: виконану заявку не можна редагувати", -1

                for key in (
                    "type",
                    "id_responsible",
                    "id_destination_storage",
                    "comment",
                ):
                    if key in form_data:
                        setattr(request, key, form_data[key])

                if "positions" in form_data:
                    for old in session.exec(
                        select(RequestProductsCatalog).where(
                            RequestProductsCatalog.id_request == request.id
                        )
                    ).all():
                        session.delete(old)
                    for catalog_id, count, part in form_data["positions"]:
                        session.add(
                            RequestProductsCatalog(
                                id_request=request.id,
                                id_product_catalog=catalog_id,
                                count=count,
                                part_amount=(part or None),
                            )
                        )

                session.commit()
                return True, "Заявку успішно змінено!", request.id

        except IntegrityError as e:
            return False, "Помилка! Заявка не може бути змінена.", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1

    @classmethod
    def mark_completed(cls, id: int, id_movement: int) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                request = session.get(Request, id)
                if request is None:
                    return False, "Помилка: заявку не знайдено"
                request.status = RequestStatus.COMPLETED
                request.id_movement = id_movement
                session.commit()
                return True, "Заявку виконано"

        except SQLAlchemyError as e:
            return False, "Системна помилка!"

    @classmethod
    def revert_completion_by_movement(cls, id_movement: int) -> tuple[bool, str]:
        """Повертає заявку, сформовану в рух `id_movement`, у стан «Нова»
        (та відв'язує від руху) — викликається при скасуванні цього руху."""
        try:
            with rx.session() as session:
                request = session.exec(
                    select(Request).where(Request.id_movement == id_movement)
                ).first()
                if request is None:
                    return True, "Заявку для руху не знайдено"
                request.status = RequestStatus.NEW
                request.id_movement = None
                session.commit()
                return True, "Заявку повернуто у стан «Нова»"

        except SQLAlchemyError as e:
            return False, "Системна помилка!"

    @classmethod
    def delete_one(cls, id: int) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                request = session.get(Request, id)
                if request is None:
                    return False, "Помилка: заявку не знайдено"
                if request.status == RequestStatus.COMPLETED:
                    return False, "Помилка: виконану заявку не можна видалити"
                request.is_deleted = True
                session.commit()
                return True, "Заявку видалено"

        except SQLAlchemyError as e:
            return False, "Системна помилка!"
