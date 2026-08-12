from collections import OrderedDict
from typing import Dict, List, Optional, Tuple

import reflex as rx
import math

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import select, func, or_, and_, update

from TrifleSklad.audit import record_action
from TrifleSklad.audit.actions.movement import (
    AdmissionCreated,
    AdmissionDeleted,
    AdmissionUpdated,
    ClientIssueCreated,
    ClientIssueUpdated,
    IssueCreated,
    IssueUpdated,
    SaleCreated,
    SaleReturnCreated,
    SaleReturnUpdated,
    SaleUpdated,
    movement_actions_for,
)
from TrifleSklad.audit.actions.request import (
    RequestCreated,
    RequestDeleted,
    RequestUpdated,
    request_position_label,
    request_position_title,
)
from TrifleSklad.audit.actions.nds_rate import NdsRateCreated
from TrifleSklad.audit.actions.owner import OwnerCreated
from TrifleSklad.audit.actions.payment_type import PaymentTypeCreated
from TrifleSklad.audit.actions.storage import StorageCreated
from TrifleSklad.audit.actions.supplier import SupplierCreated
from TrifleSklad.audit.actions.worker import WorkerCreated
from TrifleSklad.audit.base import LineChange
from TrifleSklad.audit.labels import (
    diff_position_lines,
    diff_unit_lines,
    movement_position_label,
    movement_position_title,
    movement_view,
    snapshot_position_lines,
    snapshot_unit_rows,
)
from TrifleSklad.declared import MovementsStatus, MovementsType, RequestStatus, sale_line_cost
from TrifleSklad.models import (
    Admission,
    ClientIssue,
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
    Sale,
    SaleReturn,
    Storage,
    Supplier,
    User,
    Worker,
)


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
    def get_default_id(cls) -> Optional[int]:
        """Id працівника за замовчуванням (отримувач/відповідальний)."""
        statement = (
            select(Worker.id)
            .where(Worker.is_default == True)
            .where(Worker.is_deleted == False)
        )
        with rx.session() as session:
            return session.exec(statement).first()

    @classmethod
    def add_one(cls, form_data: dict, actor_login: str) -> tuple[bool, str, int]:
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

                if worker.is_default:
                    session.exec(
                        update(Worker)
                        .where(Worker.is_deleted == False)
                        .values(is_default=False)
                    )

                session.add(worker)
                session.flush()
                record_action(session, actor_login, worker.id, WorkerCreated.for_create(worker, session))
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

                if worker.is_default:
                    session.exec(
                        update(Worker)
                        .where(Worker.id != worker.id)
                        .where(Worker.is_deleted == False)
                        .values(is_default=False)
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
    def get_self_and_children_ids(cls, category_id: int) -> List[int]:
        """[category_id] + id живих дочірніх категорій. Якщо у категорії немає
        дітей (або вона сама дочірня) — повертає лише [category_id]."""
        statement = (
            select(ProductCategory.id)
            .where(ProductCategory.id_parent == category_id)
            .where(ProductCategory.is_deleted == False)
        )
        with rx.session() as session:
            child_ids = list(session.exec(statement).all())
            return [category_id] + child_ids

    @classmethod
    def has_children(cls, category_id: int) -> bool:
        statement = (
            select(ProductCategory.id)
            .where(ProductCategory.id_parent == category_id)
            .where(ProductCategory.is_deleted == False)
        )
        with rx.session() as session:
            return session.exec(statement).first() is not None

    @classmethod
    def get_top_level_options(cls, exclude_id: Optional[int] = None) -> List[Tuple[str, str]]:
        statement = (
            select(ProductCategory)
            .where(ProductCategory.id_parent == None)
            .where(ProductCategory.is_deleted == False)
            .order_by(ProductCategory.title)
        )
        with rx.session() as session:
            categories = session.exec(statement).all()
            return [
                (str(c.id), c.title) for c in categories if c.id != exclude_id
            ]

    @classmethod
    def get_all_ordered_for_tree(cls) -> List[ProductCategory]:
        """Живі категорії, впорядковані: батько (алфавітно), одразу за ним —
        його діти (алфавітно)."""
        categories = cls.get_all()
        top_level = sorted(
            (c for c in categories if c.id_parent is None), key=lambda c: c.title
        )
        children_by_parent: Dict[int, List[ProductCategory]] = {}
        for c in categories:
            if c.id_parent is not None:
                children_by_parent.setdefault(c.id_parent, []).append(c)
        for children in children_by_parent.values():
            children.sort(key=lambda c: c.title)

        result: List[ProductCategory] = []
        for parent in top_level:
            result.append(parent)
            result.extend(children_by_parent.get(parent.id, []))
        return result

    @classmethod
    def get_hierarchy_options(cls) -> List[Tuple[str, str]]:
        """(id, назва) для всіх категорій, з відступом "— " для дочірніх —
        єдина точка формування підписів для селектів категорій."""
        return [
            (str(c.id), c.title if c.id_parent is None else f"— {c.title}")
            for c in cls.get_all_ordered_for_tree()
        ]

    @classmethod
    def add_one(cls, category: ProductCategory) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                if category.id_parent is not None:
                    parent = session.get(ProductCategory, category.id_parent)
                    if parent is None or parent.is_deleted or parent.id_parent is not None:
                        return (
                            False,
                            "Неможливо обрати підкатегорію як батьківську!",
                            -1,
                        )

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
                if category.id_parent is not None:
                    if category.id_parent == category.id:
                        return (
                            False,
                            "Категорія не може бути батьківською для самої себе!",
                            category.id,
                        )

                    parent = session.get(ProductCategory, category.id_parent)
                    if parent is None or parent.is_deleted or parent.id_parent is not None:
                        return (
                            False,
                            "Неможливо обрати підкатегорію як батьківську!",
                            category.id,
                        )

                    if cls.has_children(category.id):
                        return (
                            False,
                            "Неможливо призначити батьківську категорію: у категорії вже є підкатегорії!",
                            category.id,
                        )

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
    def get_count_with_search(cls, search_str: Optional[str] = None, category_id: Optional[str] = None) -> int:
        if search_str is not None and search_str.strip():
            condition = ProductCatalog.title.ilike(f"%{search_str.strip()}%")
        else:
            condition = True

        statement = select(func.count(ProductCatalog.id)).where(condition).where(ProductCatalog.is_deleted == False)
        if category_id and category_id not in ("", "all"):
            statement = statement.where(
                ProductCatalog.id_category.in_(ProductCategoryDAO.get_self_and_children_ids(int(category_id)))
            )

        with rx.session() as session:
            return session.exec(statement).one()

    @classmethod
    def get_all_with_relationships_by_page(cls, page: int = 1, count_items: int = 0, limit: int = 20, search_str: Optional[str] = None, category_id: Optional[str] = None) -> tuple[int, List[ProductCatalog]]:
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
            )
        if category_id and category_id not in ("", "all"):
            statement = statement.where(
                ProductCatalog.id_category.in_(ProductCategoryDAO.get_self_and_children_ids(int(category_id)))
            )
        statement = statement.offset(skip).limit(limit)

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
    def get_by_title_and_unit(cls, title: str, unit: str) -> Optional[ProductCatalog]:
        """Пошук дубля за парою назва+одиниця виміру (той самий critерій, що й
        у add_one) — для сценарію «такий товар вже є, додати його до поставки?»."""
        statement = (
            select(ProductCatalog)
            .where(ProductCatalog.title == title)
            .where(ProductCatalog.unit == unit)
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
                    .where(ProductCatalog.unit == product.unit)
                    .where(ProductCatalog.is_deleted == False)
                )

                if session.exec(statement).one_or_none() is not None:
                    return False, "Помилка! Товар з такою назвою та одиницею виміру вже існує!", -1

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
                    .where(ProductCatalog.unit == product.unit)
                    .where(ProductCatalog.id != product.id)
                    .where(ProductCatalog.is_deleted == False)
                )
                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Помилка! Товар з такою назвою та одиницею виміру вже існує!",
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
    def get_default_id(cls, type: int) -> Optional[int]:
        """Id місця зберігання за замовчуванням для заданого типу (склад/площадка/відділ)."""
        statement = (
            select(Storage.id)
            .where(Storage.type == type)
            .where(Storage.is_default == True)
            .where(Storage.is_deleted == False)
        )
        with rx.session() as session:
            return session.exec(statement).first()

    @classmethod
    def add_one(cls, storage: Storage, actor_login: str) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                statement = (
                    select(Storage)
                    .where(Storage.title == storage.title)
                    .where(Storage.type == storage.type)
                    .where(Storage.is_deleted == False)
                )

                if session.exec(statement).one_or_none() is not None:
                    return False, "Помилка! Місце зберігання з такою назвою та типом вже існує!", -1

                if storage.is_default:
                    session.exec(
                        update(Storage)
                        .where(Storage.type == storage.type)
                        .where(Storage.is_deleted == False)
                        .values(is_default=False)
                    )

                session.add(storage)
                session.flush()
                record_action(session, actor_login, storage.id, StorageCreated.for_create(storage, session))
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
                    .where(Storage.type == storage.type)
                    .where(Storage.id != storage.id)
                    .where(Storage.is_deleted == False)
                )
                if session.exec(statement).one_or_none() is not None:
                    return (
                        False,
                        "Помилка! Місце зберігання з такою назвою та типом вже існує!",
                        storage.id,
                    )

                if storage.is_default:
                    session.exec(
                        update(Storage)
                        .where(Storage.type == storage.type)
                        .where(Storage.id != storage.id)
                        .where(Storage.is_deleted == False)
                        .values(is_default=False)
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
    def get_default_id(cls) -> Optional[int]:
        """Id власника за замовчуванням."""
        statement = (
            select(Owner.id)
            .where(Owner.is_default == True)
            .where(Owner.is_deleted == False)
        )
        with rx.session() as session:
            return session.exec(statement).first()

    @classmethod
    def add_one(cls, owner: Owner, actor_login: str) -> tuple[bool, str, int]:
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

                if owner.is_default:
                    session.exec(
                        update(Owner)
                        .where(Owner.is_deleted == False)
                        .values(is_default=False)
                    )

                session.add(owner)
                session.flush()
                record_action(session, actor_login, owner.id, OwnerCreated.for_create(owner, session))
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

                if owner.is_default:
                    session.exec(
                        update(Owner)
                        .where(Owner.id != owner.id)
                        .where(Owner.is_deleted == False)
                        .values(is_default=False)
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
    def add_one(cls, supplier: Supplier, actor_login: str) -> tuple[bool, str, int]:
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
                session.flush()
                record_action(session, actor_login, supplier.id, SupplierCreated.for_create(supplier, session))
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
    def get_filtered_paginated_by_owner_storage(
        cls,
        owner_id: int,
        storage_id: int,
        exclude_ids: List[int],
        search: str = "",
        catalog_id: int = -1,
        category_id: int = -1,
        min_remaining: Optional[int] = None,
        fullness: str = "all",
        offset: int = 0,
        limit: int = 30,
    ) -> tuple[List[Product], bool]:
        """Порція доступного ТМЦ для діалогу вибору (нескінченний скрол).

        Фільтри:
        - owner_id == -1 — без фільтра за власником (на місці лежить ТМЦ різних
          власників, напр. повернення з площадки);
        - exclude_ids — одиниці, які вже додані до руху або вже обрані в діалозі;
        - search — за назвою каталогу / серійним номером / id;
        - catalog_id — конкретна позиція каталогу;
        - min_remaining — залишок (Product.count) >= значення;
        - fullness — "full" (count == capacity) / "partial" (count < capacity) / "all".

        Повертає (порція, чи_є_ще): тягнемо limit+1 рядків, щоб дізнатися, чи
        лишилися ще дані, не роблячи окремий COUNT.
        """
        statement = (
            select(Product)
            .join(ProductCatalog, Product.id_product_catalog == ProductCatalog.id)
            .options(joinedload(Product.product_catalog))
            .where(Product.id_storage == storage_id)
            .where(Product.is_deleted == False)
        )
        if owner_id != -1:
            statement = statement.where(Product.id_owner == owner_id)
        if exclude_ids:
            statement = statement.where(Product.id.not_in(exclude_ids))
        if catalog_id != -1:
            statement = statement.where(Product.id_product_catalog == catalog_id)
        if category_id != -1:
            statement = statement.where(
                ProductCatalog.id_category.in_(ProductCategoryDAO.get_self_and_children_ids(category_id))
            )
        if min_remaining is not None:
            statement = statement.where(Product.count >= min_remaining)
        if fullness == "full":
            # Без фіксованої ємності одиниця завжди вважається «повною».
            statement = statement.where(
                or_(
                    Product.count == ProductCatalog.capacity,
                    ProductCatalog.no_fixed_capacity == True,
                )
            )
        elif fullness == "partial":
            statement = statement.where(
                and_(
                    Product.count < ProductCatalog.capacity,
                    ProductCatalog.no_fixed_capacity == False,
                )
            )
        if search:
            term = search.strip()
            if term:
                # Пошук за назвою позиції каталогу / серійним номером / id —
                # доступний одразу, незалежно від того, чи обрано позицію.
                like = f"%{term.lower()}%"
                conditions = [
                    func.lower(ProductCatalog.title).like(like),
                    func.lower(func.coalesce(Product.serial_number, "")).like(like),
                ]
                if term.isdigit():
                    conditions.append(Product.id == int(term))
                statement = statement.where(or_(*conditions))

        statement = statement.order_by(Product.id).offset(offset).limit(limit + 1)

        with rx.session() as session:
            products = list(session.exec(statement).all())
            has_more = len(products) > limit
            if has_more:
                products = products[:limit]
            if len(products) > 0:
                session.expunge_all()
            return products, has_more

    @classmethod
    def get_categories_by_owner_storage(
        cls, owner_id: int, storage_id: int
    ) -> List[tuple[int, str]]:
        """Перелік категорій (id, назва з відступом для дочірніх), у яких є
        доступні одиниці на вказаному місці/власнику — перший крок каскадного
        вибору в діалозі."""
        statement = (
            select(ProductCategory.id, ProductCategory.title, ProductCategory.id_parent)
            .join(ProductCatalog, ProductCatalog.id_category == ProductCategory.id)
            .join(Product, Product.id_product_catalog == ProductCatalog.id)
            .where(Product.id_storage == storage_id)
            .where(Product.is_deleted == False)
        )
        if owner_id != -1:
            statement = statement.where(Product.id_owner == owner_id)
        statement = statement.distinct().order_by(ProductCategory.title)

        with rx.session() as session:
            return [
                (row[0], row[1] if row[2] is None else f"— {row[1]}")
                for row in session.exec(statement).all()
            ]

    @classmethod
    def get_catalog_options_by_owner_storage(
        cls, owner_id: int, storage_id: int, category_id: int = -1
    ) -> List[tuple[int, str]]:
        """Перелік позицій каталогу (id, назва), у яких є доступні одиниці на
        вказаному місці/власнику — для випадаючого фільтра в діалозі вибору.
        category_id != -1 — звузити до конкретної категорії."""
        statement = (
            select(ProductCatalog.id, ProductCatalog.title)
            .join(Product, Product.id_product_catalog == ProductCatalog.id)
            .where(Product.id_storage == storage_id)
            .where(Product.is_deleted == False)
        )
        if owner_id != -1:
            statement = statement.where(Product.id_owner == owner_id)
        if category_id != -1:
            statement = statement.where(
                ProductCatalog.id_category.in_(ProductCategoryDAO.get_self_and_children_ids(category_id))
            )
        statement = statement.distinct().order_by(ProductCatalog.title)

        with rx.session() as session:
            return [(row[0], row[1]) for row in session.exec(statement).all()]

    @classmethod
    def get_units_for_mass_select(
        cls,
        owner_id: int,
        storage_id: int,
        catalog_id: int,
        exclude_ids: List[int],
        full_only: bool,
        capacity: int,
        limit: int,
        no_fixed: bool = False,
    ) -> List[Product]:
        """До `limit` доступних одиниць позиції каталогу для масового вибору за
        кількістю штук. full_only=True (подільне ТМЦ) — лише повні одиниці
        (count == capacity), щоб масовий вибір не «з'їдав» уже розділені рештки.
        no_fixed=True (без фіксованої ємності) — опорної ємності немає, тож усі
        одиниці вважаються повними (фільтр повноти не застосовуємо)."""
        if limit <= 0:
            return []
        statement = (
            select(Product)
            .options(joinedload(Product.product_catalog))
            .where(Product.id_storage == storage_id)
            .where(Product.is_deleted == False)
            .where(Product.id_product_catalog == catalog_id)
        )
        if owner_id != -1:
            statement = statement.where(Product.id_owner == owner_id)
        if exclude_ids:
            statement = statement.where(Product.id.not_in(exclude_ids))
        if full_only and not no_fixed:
            statement = statement.where(Product.count == capacity)
        statement = statement.order_by(Product.id).limit(limit)

        with rx.session() as session:
            products = list(session.exec(statement).all())
            if len(products) > 0:
                session.expunge_all()
            return products

    @classmethod
    def get_units_for_measure(
        cls,
        owner_id: int,
        storage_id: int,
        catalog_id: int,
        exclude_ids: List[int],
        limit: int = 500,
    ) -> List[Product]:
        """Доступні одиниці позиції каталогу для жадібного набору за мірою
        (одиницями виміру), за спаданням залишку (count). Подільне ТМЦ —
        великі одиниці беруться першими, решта добивається розділенням."""
        statement = (
            select(Product)
            .options(joinedload(Product.product_catalog))
            .where(Product.id_storage == storage_id)
            .where(Product.is_deleted == False)
            .where(Product.id_product_catalog == catalog_id)
        )
        if owner_id != -1:
            statement = statement.where(Product.id_owner == owner_id)
        if exclude_ids:
            statement = statement.where(Product.id.not_in(exclude_ids))
        statement = statement.order_by(Product.count.desc()).limit(limit)

        with rx.session() as session:
            products = list(session.exec(statement).all())
            if len(products) > 0:
                session.expunge_all()
            return products

    @classmethod
    def get_stock_totals_by_owner_storage(
        cls,
        owner_id: int,
        storage_id: int,
        catalog_id: int,
        exclude_ids: List[int],
    ) -> tuple[int, int]:
        """Загальна кількість доступного ТМЦ позиції каталогу на місці/власнику
        для діалогу вибору: (кількість одиниць, сумарний залишок count — для
        подільного це сумарний обсяг у одиницях виміру, для решти дорівнює
        кількості одиниць). exclude_ids — одиниці, вже додані до руху (не
        рахуються доступними); поточний вибір у діалозі в exclude_ids не входить."""
        statement = (
            select(func.count(Product.id), func.coalesce(func.sum(Product.count), 0))
            .where(Product.id_storage == storage_id)
            .where(Product.id_product_catalog == catalog_id)
            .where(Product.is_deleted == False)
        )
        if owner_id != -1:
            statement = statement.where(Product.id_owner == owner_id)
        if exclude_ids:
            statement = statement.where(Product.id.not_in(exclude_ids))

        with rx.session() as session:
            units_count, measure_sum = session.exec(statement).one()
            return int(units_count), int(measure_sum)

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
    def get_stock_grouped(
        cls,
        catalog_id: Optional[int] = None,
        storage_id: Optional[int] = None,
        owner_id: Optional[int] = None,
        exclude_types: Optional[List[int]] = None,
        category_id: Optional[int] = None,
        search: Optional[str] = None,
    ) -> List[tuple]:
        """Звіт «Наявність ТМЦ»: позиції каталогу, що зараз лежать на місцях
        зберігання, із сумарною кількістю та числом одиниць. Фільтри —
        за позицією каталогу, категорією, місцем зберігання, власником; exclude_types —
        типи сховищ (склад/площадка/відділ), які треба виключити; search — вільний
        пошук за назвою позиції каталогу або серійним номером одиниці.
        Повертає список кортежів (catalog_id, title, unit, total_count, units_count)."""
        exclude_types = exclude_types or []
        statement = (
            select(
                ProductCatalog.id,
                ProductCatalog.title,
                ProductCatalog.unit,
                func.coalesce(func.sum(Product.count), 0),
                func.count(Product.id),
            )
            .join(Product, Product.id_product_catalog == ProductCatalog.id)
            .join(Storage, Storage.id == Product.id_storage)
            .where(Product.is_deleted == False)
            .where(Storage.is_deleted == False)
            .group_by(ProductCatalog.id, ProductCatalog.title, ProductCatalog.unit)
            .order_by(ProductCatalog.title)
        )
        if catalog_id is not None:
            statement = statement.where(ProductCatalog.id == catalog_id)
        if category_id is not None:
            statement = statement.where(
                ProductCatalog.id_category.in_(ProductCategoryDAO.get_self_and_children_ids(category_id))
            )
        if storage_id is not None:
            statement = statement.where(Product.id_storage == storage_id)
        if owner_id is not None:
            statement = statement.where(Product.id_owner == owner_id)
        if exclude_types:
            statement = statement.where(Storage.type.not_in(exclude_types))
        if search:
            term = search.strip()
            if term:
                like = f"%{term.lower()}%"
                conditions = [
                    func.lower(ProductCatalog.title).like(like),
                    func.lower(func.coalesce(Product.serial_number, "")).like(like),
                ]
                if term.isdigit():
                    conditions.append(Product.id == int(term))
                statement = statement.where(or_(*conditions))

        with rx.session() as session:
            rows = session.exec(statement).all()
            return [
                (row[0], row[1], row[2], int(row[3] or 0), int(row[4] or 0))
                for row in rows
            ]

    @classmethod
    def get_stock_units(
        cls,
        catalog_id: int,
        storage_id: Optional[int] = None,
        owner_id: Optional[int] = None,
        exclude_types: Optional[List[int]] = None,
        search: Optional[str] = None,
    ) -> List[Product]:
        """Окремі одиниці ТМЦ для модалки звіту: всі живі одиниці позиції каталогу
        на місцях зберігання з тими ж фільтрами, що й у згрупованому звіті."""
        exclude_types = exclude_types or []
        statement = (
            select(Product)
            .options(
                joinedload(Product.product_catalog),
                joinedload(Product.storage),
                joinedload(Product.owner),
            )
            .join(Storage, Storage.id == Product.id_storage)
            .where(Product.is_deleted == False)
            .where(Storage.is_deleted == False)
            .where(Product.id_product_catalog == catalog_id)
            .order_by(Product.id)
        )
        if storage_id is not None:
            statement = statement.where(Product.id_storage == storage_id)
        if owner_id is not None:
            statement = statement.where(Product.id_owner == owner_id)
        if exclude_types:
            statement = statement.where(Storage.type.not_in(exclude_types))
        if search:
            term = search.strip()
            if term:
                like = f"%{term.lower()}%"
                conditions = [
                    func.lower(func.coalesce(Product.serial_number, "")).like(like),
                ]
                if term.isdigit():
                    conditions.append(Product.id == int(term))
                statement = statement.where(or_(*conditions))

        with rx.session() as session:
            products = session.exec(statement).all()
            if len(products) > 0:
                session.expunge_all()
            return list(products)

    @classmethod
    def get_by_id_with_relationships(cls, id: int) -> Optional[Product]:
        """Одиниця ТМЦ з підвантаженими каталогом/місцем/власником — для детальної
        сторінки одиниці. На відміну від get_stock_units не фільтрує is_deleted:
        спожита одиниця теж має історію (доступна за прямим id з діалогу поставки)."""
        statement = (
            select(Product)
            .options(
                joinedload(Product.product_catalog),
                joinedload(Product.storage),
                joinedload(Product.owner),
            )
            .where(Product.id == id)
        )

        with rx.session() as session:
            product = session.exec(statement).one_or_none()

            if product:
                session.expunge(product)
            return product

    @classmethod
    def get_units_count(
        cls, search: Optional[str] = None, catalog_id: Optional[int] = None
    ) -> int:
        """Кількість живих одиниць ТМЦ для пагінації переліку одиниць.
        search — за назвою каталогу / серійним номером / id."""
        statement = (
            select(func.count(Product.id))
            .join(ProductCatalog, Product.id_product_catalog == ProductCatalog.id)
            .where(Product.is_deleted == False)
        )
        if catalog_id is not None:
            statement = statement.where(Product.id_product_catalog == catalog_id)
        if search is not None and search.strip():
            term = search.strip()
            like = f"%{term.lower()}%"
            conditions = [
                func.lower(ProductCatalog.title).like(like),
                func.lower(func.coalesce(Product.serial_number, "")).like(like),
            ]
            if term.isdigit():
                conditions.append(Product.id == int(term))
            statement = statement.where(or_(*conditions))

        with rx.session() as session:
            return session.exec(statement).one()

    @classmethod
    def get_units_paginated(
        cls,
        page: int = 1,
        limit: int = 20,
        count_items: int = 0,
        search: Optional[str] = None,
        catalog_id: Optional[int] = None,
    ) -> tuple[int, List[Product]]:
        """Сторінка живих одиниць ТМЦ (із каталогом/місцем/власником) для переліку
        одиниць у звіті. Сортування — за id (новіші зверху)."""
        total_pages = max(1, math.ceil(count_items / limit))
        skip = (max(1, page) - 1) * limit

        statement = (
            select(Product)
            .join(ProductCatalog, Product.id_product_catalog == ProductCatalog.id)
            .options(
                joinedload(Product.product_catalog),
                joinedload(Product.storage),
                joinedload(Product.owner),
            )
            .where(Product.is_deleted == False)
        )
        if catalog_id is not None:
            statement = statement.where(Product.id_product_catalog == catalog_id)
        if search is not None and search.strip():
            term = search.strip()
            like = f"%{term.lower()}%"
            conditions = [
                func.lower(ProductCatalog.title).like(like),
                func.lower(func.coalesce(Product.serial_number, "")).like(like),
            ]
            if term.isdigit():
                conditions.append(Product.id == int(term))
            statement = statement.where(or_(*conditions))

        statement = statement.order_by(Product.id.desc()).offset(skip).limit(limit)

        with rx.session() as session:
            items = session.exec(statement).all()
            session.expunge_all()
            return total_pages, list(items)

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
    incoming_storage: Optional[str] = None,
    destination_storage: Optional[str] = None,
    incoming_owner: Optional[str] = None,
    destination_owner: Optional[str] = None,
) -> list:
    """Список SQLAlchemy-умов фільтрації рухів за датою (рядок ISO), статусами та
    (контекстно) складом/власником відправлення/призначення.
    Спільний для всіх типів руху (поступлення/списання/переміщення/видача/продаж).
    Значення складу/власника — рядок id; "" / "all" / None означають «без фільтра»."""
    conditions = []
    if date_from:
        conditions.append(Movement.date >= date_from)
    if date_to:
        conditions.append(Movement.date <= date_to)
    if statuses:
        conditions.append(Movement.status.in_(statuses))

    def _add(column, value):
        if value and value not in ("", "all"):
            try:
                conditions.append(column == int(value))
            except (TypeError, ValueError):
                pass

    _add(Movement.id_incoming_storage, incoming_storage)
    _add(Movement.id_destination_storage, destination_storage)
    _add(Movement.id_incoming_owner, incoming_owner)
    _add(Movement.id_destination_owner, destination_owner)
    return conditions


def _reconcile_catalog_instances(movement: Movement) -> None:
    """Кілька позицій однієї позиції каталогу (напр. ТМЦ без фіксованої ємності,
    доданий двічі) можуть нести РІЗНІ detached-екземпляри ProductCatalog з
    однаковим PK — діалог перечитує список каталогу на кожній вставці. SQLAlchemy
    не дозволяє два об'єкти з однаковою identity в одній сесії (InvalidRequestError
    під час `session.add`). Зводимо всі посилання `.product` до єдиного екземпляра
    на кожен id перед збереженням."""
    seen: dict = {}
    for pc in movement.products_catalog or []:
        if pc.product is None:
            continue
        pid = pc.product.id
        if pid in seen:
            pc.product = seen[pid]
        else:
            seen[pid] = pc.product


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
        incoming_storage: Optional[str] = None,
        destination_storage: Optional[str] = None,
        incoming_owner: Optional[str] = None,
        destination_owner: Optional[str] = None,
    ) -> tuple[int, List[Movement]]:
        """Сторінкований перелік рухів одного типу з фільтром за датою/статусами
        та складом/власником. Дата — рядок ISO 'YYYY-MM-DD'."""
        conditions = movement_filter_conditions(
            date_from, date_to, statuses,
            incoming_storage, destination_storage, incoming_owner, destination_owner,
        )

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
    def add_one(cls, form_data: dict, actor_login: str) -> tuple[bool, str, int]:
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
                session.flush()

                Created, _, _ = movement_actions_for(movement.type)
                position_lines = diff_position_lines(
                    None, movement.products_catalog, session,
                    key=lambda x: x.id_product_catalog,
                    title=movement_position_title, label=movement_position_label,
                )
                record_action(
                    session, actor_login, movement.id, Created.for_create(movement, session, lines=position_lines)
                )

                session.commit()

                return True, "Движение товара успешно добавлено", movement.id

        except IntegrityError as e:
            return False, "Ошибка: Движение товара не может быть добавлено", -1
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def edit_one(cls, form_data: dict, actor_login: str) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                movement = session.get(Movement, form_data["id"])

                if movement is None:
                    return False, "Ошибка: Движение товара не найдено", -1

                _, Updated, _ = movement_actions_for(movement.type)
                old_snapshot = Updated.snapshot(movement)

                for key, value in form_data.items():
                    setattr(movement, key, value)

                record_action(
                    session, actor_login, movement.id, Updated.from_diff(old_snapshot, movement, session)
                )

                session.commit()
                session.refresh(movement)
                return True, "Движение товара успешно изменено", movement.id

        except IntegrityError as e:
            return False, "Ошибка: Единица товара не может быть изменена", -1
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def cancel_movement(cls, id: int, actor_login: str) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                movement = session.get(Movement, id)

                if movement is None:
                    return False, "Ошибка: Движение товара не найдено"

                _, Updated, _ = movement_actions_for(movement.type)
                old_snapshot = Updated.snapshot(movement)

                movement.status = MovementsStatus.CANCELED

                record_action(
                    session, actor_login, movement.id, Updated.from_diff(old_snapshot, movement, session)
                )

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
    def get_history_by_product_id(cls, product_id: int) -> List[Movement]:
        """Історія руху однієї одиниці ТМЦ: усі рухи, до яких вона входить
        (через MovementProducts), із підвантаженими місцями/власниками, у порядку
        створення (id за зростанням). Для детальної сторінки одиниці."""
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
            .options(
                joinedload(Movement.incoming_storage),
                joinedload(Movement.destination_storage),
                joinedload(Movement.incoming_owner),
                joinedload(Movement.destination_owner),
            )
            .where(MovementProducts.id_product == product_id)
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
        """Повертає одиниці в джерело самого руху `current_movement_id` —
        `id_incoming_storage`/`id_incoming_owner`.

        Під інваріантом «у русі лише ТМЦ того складу й власника, що в шапці»
        (забезпечується діалогом вибору при створенні) шапка й є достовірним
        «звідки» для кожної одиниці. Раніше метод реконструював попереднє місце
        обходом ланцюжка рухів — це ламалося на даних, що порушують інваріант.
        Для повернення (RETURN) `id_incoming_owner` не задано — тоді змінюється
        лише склад, кожна одиниця зберігає свого власника."""
        if len(product_ids) == 0:
            return True, "Нет единиц для возврата"
        try:
            with rx.session() as session:
                movement = session.get(Movement, current_movement_id)
                if movement is None:
                    return False, "Помилка: рух не знайдено"
                for product_id in product_ids:
                    product = session.get(Product, product_id)
                    if product is None:
                        continue
                    product.id_storage = movement.id_incoming_storage
                    if movement.id_incoming_owner is not None:
                        product.id_owner = movement.id_incoming_owner
                    session.add(product)

                session.commit()
                return True, "Единицы товара возвращены в источник движения"

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
    def get_default_id(cls) -> Optional[int]:
        """Id типу оплати за замовчуванням."""
        statement = (
            select(PaymentType.id)
            .where(PaymentType.is_default == True)
            .where(PaymentType.is_deleted == False)
        )
        with rx.session() as session:
            return session.exec(statement).first()

    @classmethod
    def add_one(cls, payment_type: PaymentType, actor_login: str) -> tuple[bool, str, int]:
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

                if payment_type.is_default:
                    session.exec(
                        update(PaymentType)
                        .where(PaymentType.is_deleted == False)
                        .values(is_default=False)
                    )

                session.add(payment_type)
                session.flush()
                record_action(
                    session, actor_login, payment_type.id, PaymentTypeCreated.for_create(payment_type, session)
                )
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

                if payment_type.is_default:
                    session.exec(
                        update(PaymentType)
                        .where(PaymentType.id != payment_type.id)
                        .where(PaymentType.is_deleted == False)
                        .values(is_default=False)
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
    def get_default_id(cls) -> Optional[int]:
        """Id ставки ПДВ за замовчуванням."""
        statement = (
            select(NDSRate.id)
            .where(NDSRate.is_default == True)
            .where(NDSRate.is_deleted == False)
        )
        with rx.session() as session:
            return session.exec(statement).first()

    @classmethod
    def add_one(cls, nds_rate: NDSRate, actor_login: str) -> tuple[bool, str, int]:
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
                session.flush()
                record_action(session, actor_login, nds_rate.id, NdsRateCreated.for_create(nds_rate, session))
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
        incoming_storage: Optional[str] = None,
        destination_storage: Optional[str] = None,
        incoming_owner: Optional[str] = None,
        destination_owner: Optional[str] = None,
        supplier: Optional[str] = None,
    ) -> tuple[int, List[Admission]]:
        conditions = movement_filter_conditions(
            date_from, date_to, statuses,
            incoming_storage, destination_storage, incoming_owner, destination_owner,
        )
        movement_ids = select(Movement.id)
        for cond in conditions:
            movement_ids = movement_ids.where(cond)

        # Фільтр за постачальником — на таблиці Admission.
        admission_conditions = []
        if supplier and supplier not in ("", "all"):
            try:
                admission_conditions.append(Admission.id_supplier == int(supplier))
            except (TypeError, ValueError):
                pass

        with rx.session() as session:
            count_stmt = select(func.count(Admission.id)).where(
                Admission.id.in_(movement_ids)
            )
            for cond in admission_conditions:
                count_stmt = count_stmt.where(cond)
            total = session.exec(count_stmt).one()
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
            )
            for cond in admission_conditions:
                statement = statement.where(cond)
            statement = (
                statement.order_by(Admission.id.desc()).offset(skip).limit(limit)
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
    def add_one(cls, movement: Admission, actor_login: str) -> tuple[bool, str, int]:
        try:
            _reconcile_catalog_instances(movement.movement)
            with rx.session() as session:
                session.expire_on_commit = False
                session.add(movement)
                session.flush()

                position_lines = diff_position_lines(
                    None, movement.movement.products_catalog, session,
                    key=lambda x: x.id_product_catalog,
                    title=movement_position_title, label=movement_position_label,
                )
                record_action(
                    session, actor_login, movement.id,
                    AdmissionCreated.for_create(movement_view(movement), session, lines=position_lines),
                )

                session.commit()
                return True, "Постачання успішно додано!", movement.id

        except IntegrityError as e:
            return False, "Помилка! Постачання не може бути додано.", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1

    @classmethod
    def edit_one(
        cls,
        admission: Admission,
        actor_login: str,
        reason: str = "",
        removed_line_ids: Optional[List[int]] = None,
    ) -> tuple[bool, str, int]:
        """Редагування постачання. `reason` — обов'язкова причина коригування при
        повному редагуванні (йде в аудит). `removed_line_ids` — позиції, які
        користувач прибрав із переліку у формі: видаляються тут, у тій самій
        транзакції (раніше рядок зникав із БД одразу при кліку, ще до збереження).

        Одиниці, що випали зі складу позицій, видаляються фізично: постачання —
        це рух, який їх породив, тож інакше вони лишились би в залишках без
        жодного руху (session.merge прибирає лише рядки зв'язку)."""
        try:
            _reconcile_catalog_instances(admission.movement)
            with rx.session() as session:
                old_admission = session.get(Admission, admission.id)
                if old_admission is None:
                    return False, "Помилка! Постачання не знайдено.", -1
                old_snapshot = AdmissionUpdated.snapshot(movement_view(old_admission))
                old_positions = snapshot_position_lines(old_admission.movement.products_catalog)
                old_units = [
                    product
                    for position in old_admission.movement.products_catalog
                    for product in position.products
                ]
                old_unit_rows = snapshot_unit_rows(old_units)

                for line_id in removed_line_ids or []:
                    flag, text = cls._delete_line_in_session(session, line_id)
                    if not flag:
                        return False, text, -1

                merged = session.merge(admission)
                session.flush()

                kept_unit_ids = {
                    product.id
                    for position in merged.movement.products_catalog
                    for product in position.products
                }
                for unit in old_units:
                    if unit.id not in kept_unit_ids:
                        session.delete(session.get(Product, unit.id))
                session.flush()

                new_unit_rows = snapshot_unit_rows(
                    [
                        product
                        for position in merged.movement.products_catalog
                        for product in position.products
                    ]
                )
                position_lines = diff_position_lines(
                    old_positions, merged.movement.products_catalog, session,
                    key=lambda x: x.id_product_catalog,
                    title=movement_position_title, label=movement_position_label,
                )
                record_action(
                    session, actor_login, merged.id,
                    AdmissionUpdated.from_diff(
                        old_snapshot,
                        movement_view(merged),
                        session,
                        reason=reason,
                        lines=position_lines + diff_unit_lines(old_unit_rows, new_unit_rows, session),
                    ),
                )

                session.commit()
                return True, "Постачання успішно змінено!", admission.id

        except IntegrityError as e:
            return False, "Помилка! Постачання не може бути змінено.", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1

    @classmethod
    def can_edit_products(cls, id: int) -> bool:
        """Чи можна редагувати перелік ТМЦ цього поставлення — той самий
        конфлікт-чек, що й у delete_one: жодна з одиниць цього поставлення не
        повинна фігурувати в іншому русі (напр. вже переміщена/списана)."""
        with rx.session() as session:
            movements_products_catalog = session.exec(
                select(MovementProductsCatalog).where(
                    MovementProductsCatalog.id_movement == id
                )
            ).all()
            if not movements_products_catalog:
                return True
            products_in_movement = session.exec(
                select(MovementProducts).where(
                    MovementProducts.id_movement_product.in_(
                        [mpc.id for mpc in movements_products_catalog]
                    )
                )
            ).all()
            other_movements_with_current_products = session.exec(
                select(MovementProducts)
                .where(
                    MovementProducts.id_product.in_(
                        [pim.id_product for pim in products_in_movement]
                    )
                )
                .where(
                    MovementProducts.id_movement_product.not_in(
                        [mpc.id for mpc in movements_products_catalog]
                    )
                )
            ).all()
            return len(other_movements_with_current_products) == 0

    @staticmethod
    def _delete_line_in_session(
        session, id_movement_products_catalog: int, *, actor_login: Optional[str] = None
    ) -> tuple[bool, str]:
        """Видаляє рядок переліку ТМЦ поставлення разом з його одиницями у ПЕРЕДАНІЙ
        сесії (без commit) — за умови, що жодна одиниця рядка не фігурує в іншому
        русі. `actor_login` заданий — пише окремий запис аудиту (самостійне
        видалення позиції); None — виклик усередині edit_one, де аудит формується
        одним записом на все збереження."""
        mpc: Optional[MovementProductsCatalog] = session.get(
            MovementProductsCatalog, id_movement_products_catalog
        )
        if mpc is None:
            return False, "Помилка! Позицію не знайдено."

        products_in_line: List[MovementProducts] = session.exec(
            select(MovementProducts).where(MovementProducts.id_movement_product == mpc.id)
        ).all()
        products: List[Product] = session.exec(
            select(Product).where(Product.id.in_([p.id_product for p in products_in_line]))
        ).all()

        other_movements_with_current_products = session.exec(
            select(MovementProducts)
            .where(MovementProducts.id_product.in_([p.id for p in products]))
            .where(MovementProducts.id_movement_product != mpc.id)
        ).all()
        if len(other_movements_with_current_products) > 0:
            return (
                False,
                "Помилка! Позицію не можна видалити, оскільки товар вже використовується в іншому русі.",
            )

        if actor_login is not None:
            removed_line = LineChange(
                kind="removed",
                title=movement_position_title(mpc, session),
                old=movement_position_label(mpc, session),
            )
            record_action(session, actor_login, mpc.id_movement, AdmissionUpdated(lines=[removed_line]))

        for item in products_in_line:
            session.delete(item)
        for item in products:
            session.delete(item)
        session.delete(mpc)
        session.flush()
        return True, "Позицію видалено!"

    @classmethod
    def delete_product_line(cls, id_movement_products_catalog: int, actor_login: str) -> tuple[bool, str]:
        """Видаляє один рядок переліку ТМЦ поставлення (позицію каталогу разом
        з усіма її одиницями) — за умови, що жодна з одиниць цього рядка не
        фігурує в іншому русі. Використовується при редагуванні поставлення."""
        try:
            with rx.session() as session:
                flag, text = cls._delete_line_in_session(
                    session, id_movement_products_catalog, actor_login=actor_login
                )
                if not flag:
                    return False, text
                session.commit()
                return True, text

        except IntegrityError:
            return False, "Помилка! Позицію не може бути видалено."
        except SQLAlchemyError:
            return False, "Системна помилка!"

    @classmethod
    def delete_one(cls, id: int, actor_login: str) -> tuple[bool, str]:
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

                deleted_action = AdmissionDeleted.for_delete(
                    movement_view(admission), session,
                    lines=[
                        LineChange(
                            kind="removed",
                            title=movement_position_title(mpc, session),
                            old=movement_position_label(mpc, session),
                        )
                        for mpc in movements_products_catalog
                    ],
                )
                record_action(session, actor_login, id, deleted_action)

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
        incoming_storage: Optional[str] = None,
        incoming_owner: Optional[str] = None,
        site: Optional[str] = None,
        recipient: Optional[str] = None,
    ) -> tuple[int, List[Issue]]:
        # Місце призначення видачі (площадка/відділ) — це destination_storage руху.
        conditions = movement_filter_conditions(
            date_from, date_to, statuses,
            incoming_storage=incoming_storage,
            destination_storage=site,
            incoming_owner=incoming_owner,
        )
        movement_ids = select(Movement.id)
        for cond in conditions:
            movement_ids = movement_ids.where(cond)

        # Фільтр за відповідальним (отримувачем) — на таблиці Issue.
        issue_conditions = []
        if recipient and recipient not in ("", "all"):
            try:
                issue_conditions.append(Issue.id_recipient == int(recipient))
            except (TypeError, ValueError):
                pass

        with rx.session() as session:
            count_stmt = select(func.count(Issue.id)).where(Issue.id.in_(movement_ids))
            for cond in issue_conditions:
                count_stmt = count_stmt.where(cond)
            total = session.exec(count_stmt).one()
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
            )
            for cond in issue_conditions:
                statement = statement.where(cond)
            statement = (
                statement.order_by(Issue.id.desc()).offset(skip).limit(limit)
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
    def add_one(cls, issue: Issue, actor_login: str) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                session.expire_on_commit = False
                session.add(issue)
                session.flush()

                position_lines = diff_position_lines(
                    None, issue.movement.products_catalog, session,
                    key=lambda x: x.id_product_catalog,
                    title=movement_position_title, label=movement_position_label,
                )
                record_action(
                    session, actor_login, issue.id,
                    IssueCreated.for_create(movement_view(issue), session, lines=position_lines),
                )

                session.commit()
                return True, "Выдача успешно добавлена", issue.id

        except IntegrityError as e:
            return False, "Ошибка: Выдача не может быть добавлена", -1
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}", -1

    @classmethod
    def edit_one(cls, issue: Issue, actor_login: str) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                session.expire_on_commit = False
                old_issue = session.get(Issue, issue.id)
                if old_issue is None:
                    return False, "Ошибка: Выдача не найдена", -1
                old_snapshot = IssueUpdated.snapshot(movement_view(old_issue))

                merged = session.merge(issue)

                record_action(
                    session, actor_login, merged.id,
                    IssueUpdated.from_diff(old_snapshot, movement_view(merged), session),
                )

                session.commit()
                return True, "Выдача успешно изменена", issue.id

        except IntegrityError as e:
            return False, "Ошибка: Выдача не может быть изменена", -1
        except SQLAlchemyError as e:
            return False, f"Ошибка: {str(e)}", -1


class ClientIssueDAO:
    @classmethod
    def get_all(cls) -> List[ClientIssue]:
        statement = select(ClientIssue)

        with rx.session() as session:
            client_issues = session.exec(statement).all()

            if len(client_issues) > 0:
                session.expunge_all()
            return list(client_issues)

    @classmethod
    def get_all_with_all_relationship(cls) -> List[ClientIssue]:
        statement = select(ClientIssue).options(
            joinedload(ClientIssue.movement).options(
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
            joinedload(ClientIssue.recipient),
        )

        with rx.session() as session:
            client_issues = session.exec(statement).all()

            if len(client_issues) > 0:
                session.expunge_all()
            return list(client_issues)

    @classmethod
    def get_paginated(
        cls,
        page: int = 1,
        limit: int = 20,
        date_from: str = "",
        date_to: str = "",
        statuses: Optional[List[int]] = None,
        incoming_storage: Optional[str] = None,
        incoming_owner: Optional[str] = None,
        recipient: Optional[str] = None,
        contract_number: Optional[str] = None,
    ) -> tuple[int, List[ClientIssue]]:
        conditions = movement_filter_conditions(
            date_from, date_to, statuses,
            incoming_storage=incoming_storage,
            incoming_owner=incoming_owner,
        )
        movement_ids = select(Movement.id)
        for cond in conditions:
            movement_ids = movement_ids.where(cond)

        client_issue_conditions = []
        if recipient and recipient not in ("", "all"):
            try:
                client_issue_conditions.append(ClientIssue.id_recipient == int(recipient))
            except (TypeError, ValueError):
                pass
        if contract_number:
            client_issue_conditions.append(ClientIssue.contract_number.contains(contract_number))

        with rx.session() as session:
            count_stmt = select(func.count(ClientIssue.id)).where(ClientIssue.id.in_(movement_ids))
            for cond in client_issue_conditions:
                count_stmt = count_stmt.where(cond)
            total = session.exec(count_stmt).one()
            total_pages = max(1, math.ceil(total / limit))
            skip = (max(1, page) - 1) * limit

            statement = (
                select(ClientIssue)
                .options(
                    joinedload(ClientIssue.movement).options(
                        joinedload(Movement.incoming_storage),
                        joinedload(Movement.incoming_owner),
                        joinedload(Movement.destination_storage),
                    ),
                    joinedload(ClientIssue.recipient),
                )
                .where(ClientIssue.id.in_(movement_ids))
            )
            for cond in client_issue_conditions:
                statement = statement.where(cond)
            statement = (
                statement.order_by(ClientIssue.id.desc()).offset(skip).limit(limit)
            )
            client_issues = session.exec(statement).all()
            if len(client_issues) > 0:
                session.expunge_all()
            return total_pages, list(client_issues)

    @classmethod
    def get_by_id(cls, id: str) -> Optional[ClientIssue]:
        statement = select(ClientIssue).where(ClientIssue.id == id)

        with rx.session() as session:
            client_issue = session.exec(statement).one_or_none()

            if client_issue:
                session.expunge(client_issue)
            return client_issue

    @classmethod
    def get_by_id_with_all_relationship(cls, id: str) -> Optional[ClientIssue]:
        statement = (
            select(ClientIssue)
            .options(
                joinedload(ClientIssue.movement).options(
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
                joinedload(ClientIssue.recipient),
            )
            .where(ClientIssue.id == id)
        )

        with rx.session() as session:
            client_issue = session.exec(statement).one_or_none()

            if client_issue:
                session.expunge(client_issue)
            return client_issue

    @classmethod
    def get_by_id_with_movement_product_storage_owner_recipient(
        cls, id: str
    ) -> Optional[ClientIssue]:
        statement = (
            select(ClientIssue)
            .options(
                joinedload(ClientIssue.movement).options(
                    selectinload(Movement.products_catalog).options(
                        joinedload(MovementProductsCatalog.product),
                        selectinload(MovementProductsCatalog.products),
                    ),
                    joinedload(Movement.incoming_storage),
                    joinedload(Movement.incoming_owner),
                    joinedload(Movement.destination_storage),
                ),
                joinedload(ClientIssue.recipient),
            )
            .where(ClientIssue.id == id)
        )

        with rx.session() as session:
            client_issue = session.exec(statement).one_or_none()

            if client_issue:
                session.expunge(client_issue)
            return client_issue

    @classmethod
    def add_one(cls, client_issue: ClientIssue, actor_login: str) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                session.expire_on_commit = False
                session.add(client_issue)
                session.flush()

                position_lines = diff_position_lines(
                    None, client_issue.movement.products_catalog, session,
                    key=lambda x: x.id_product_catalog,
                    title=movement_position_title, label=movement_position_label,
                )
                record_action(
                    session, actor_login, client_issue.id,
                    ClientIssueCreated.for_create(movement_view(client_issue), session, lines=position_lines),
                )

                session.commit()
                return True, "Видача клієнту успішно додана", client_issue.id

        except IntegrityError as e:
            return False, "Помилка: видача клієнту не може бути додана", -1
        except SQLAlchemyError as e:
            return False, f"Помилка: {str(e)}", -1

    @classmethod
    def edit_one(cls, client_issue: ClientIssue, actor_login: str) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                session.expire_on_commit = False
                old_client_issue = session.get(ClientIssue, client_issue.id)
                if old_client_issue is None:
                    return False, "Помилка: видачу клієнту не знайдено", -1
                old_snapshot = ClientIssueUpdated.snapshot(movement_view(old_client_issue))

                merged = session.merge(client_issue)

                record_action(
                    session, actor_login, merged.id,
                    ClientIssueUpdated.from_diff(old_snapshot, movement_view(merged), session),
                )

                session.commit()
                return True, "Видача клієнту успішно змінена", client_issue.id

        except IntegrityError as e:
            return False, "Помилка: видача клієнту не може бути змінена", -1
        except SQLAlchemyError as e:
            return False, f"Помилка: {str(e)}", -1


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
        incoming_storage: Optional[str] = None,
        incoming_owner: Optional[str] = None,
        responsible: Optional[str] = None,
    ) -> tuple[int, List[Sale]]:
        conditions = movement_filter_conditions(
            date_from, date_to, statuses,
            incoming_storage=incoming_storage,
            incoming_owner=incoming_owner,
        )
        movement_ids = select(Movement.id)
        for cond in conditions:
            movement_ids = movement_ids.where(cond)

        # Фільтр за відповідальним — на таблиці Sale.
        sale_conditions = []
        if responsible and responsible not in ("", "all"):
            try:
                sale_conditions.append(Sale.id_responsible == int(responsible))
            except (TypeError, ValueError):
                pass

        with rx.session() as session:
            count_stmt = select(func.count(Sale.id)).where(Sale.id.in_(movement_ids))
            for cond in sale_conditions:
                count_stmt = count_stmt.where(cond)
            total = session.exec(count_stmt).one()
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
            )
            for cond in sale_conditions:
                statement = statement.where(cond)
            statement = (
                statement.order_by(Sale.id.desc()).offset(skip).limit(limit)
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
    def add_one(cls, form_data: dict, actor_login: str) -> tuple[bool, str, int]:
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

                # Подільність/ємність позицій каталогу — для пропорційного
                # розрахунку вартості частини подільного ТМЦ (sale_line_cost).
                catalog_meta = {
                    c.id: (c.divisible, c.capacity)
                    for c in session.exec(
                        select(ProductCatalog).where(
                            ProductCatalog.id.in_(list(catalog_to_ids.keys()))
                        )
                    ).all()
                }

                movement_products_catalog: List[MovementProductsCatalog] = []
                total_cost = 0.0
                for catalog_id, ids in catalog_to_ids.items():
                    price = float(prices.get(catalog_id, 0.0))
                    units = [bound_products[i] for i in ids if i in bound_products]
                    divisible, capacity = catalog_meta.get(catalog_id, (False, 0))
                    line_units = [(u.count or 0, divisible, capacity) for u in units]
                    movement_products_catalog.append(
                        MovementProductsCatalog(
                            id_product_catalog=catalog_id,
                            count=len(units),
                            price=price,
                            products=units,
                        )
                    )
                    total_cost += sale_line_cost(price, line_units)

                movement.products_catalog = movement_products_catalog
                movement.total_cost = total_cost

                sale: Sale = Sale(
                    id_responsible=form_data["id_responsible"],
                    client_info=form_data.get("client_info"),
                    movement=movement,
                )

                session.add(sale)
                session.flush()

                position_lines = diff_position_lines(
                    None, movement.products_catalog, session,
                    key=lambda x: x.id_product_catalog,
                    title=movement_position_title, label=movement_position_label,
                )
                record_action(
                    session, actor_login, sale.id,
                    SaleCreated.for_create(movement_view(sale), session, lines=position_lines),
                )

                session.commit()
                return True, "Продаж успішно додано", sale.id

        except IntegrityError as e:
            return False, "Помилка: Продаж не може бути додано", -1
        except SQLAlchemyError as e:
            return False, f"Помилка: {str(e)}", -1

    @classmethod
    def edit_one(cls, form_data: dict, actor_login: str) -> tuple[bool, str, int]:
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

                old_snapshot = SaleUpdated.snapshot(movement_view(sale))

                if "status" in form_data:
                    movement.status = form_data["status"]
                if "comment" in form_data:
                    movement.comment = form_data["comment"]
                if "client_info" in form_data:
                    sale.client_info = form_data["client_info"]

                record_action(
                    session, actor_login, sale.id,
                    SaleUpdated.from_diff(old_snapshot, movement_view(sale), session),
                )

                session.commit()
                return True, "Продаж успішно змінено", sale.id

        except IntegrityError as e:
            return False, "Помилка: Продаж не може бути змінено", -1
        except SQLAlchemyError as e:
            return False, f"Помилка: {str(e)}", -1


class SaleReturnDAO:
    """Повернення продажу: проданий ТМЦ (одиниці is_deleted=True) приймається
    назад на склад. Загальна компенсована вартість — Movement.total_cost,
    компенсація за позицію — MovementProductsCatalog.price."""

    @classmethod
    def get_paginated(
        cls,
        page: int = 1,
        limit: int = 20,
        date_from: str = "",
        date_to: str = "",
        statuses: Optional[List[int]] = None,
        destination_storage: Optional[str] = None,
    ) -> tuple[int, List[SaleReturn]]:
        conditions = movement_filter_conditions(
            date_from, date_to, statuses,
            destination_storage=destination_storage,
        )
        movement_ids = select(Movement.id).where(Movement.type == MovementsType.SALE_RETURN)
        for cond in conditions:
            movement_ids = movement_ids.where(cond)

        with rx.session() as session:
            count_stmt = select(func.count(SaleReturn.id)).where(
                SaleReturn.id.in_(movement_ids)
            )
            total = session.exec(count_stmt).one()
            total_pages = max(1, math.ceil(total / limit))
            skip = (max(1, page) - 1) * limit

            statement = (
                select(SaleReturn)
                .options(
                    joinedload(SaleReturn.movement).options(
                        joinedload(Movement.destination_storage),
                    ),
                )
                .where(SaleReturn.id.in_(movement_ids))
                .order_by(SaleReturn.id.desc())
                .offset(skip)
                .limit(limit)
            )
            returns = session.exec(statement).all()
            if len(returns) > 0:
                session.expunge_all()
            return total_pages, list(returns)

    @classmethod
    def get_by_id_with_all_relationship(cls, id: int) -> Optional[SaleReturn]:
        statement = (
            select(SaleReturn)
            .options(
                joinedload(SaleReturn.movement).options(
                    selectinload(Movement.products_catalog).options(
                        joinedload(MovementProductsCatalog.product),
                        selectinload(MovementProductsCatalog.products).options(
                            joinedload(Product.product_catalog),
                        ),
                    ),
                    joinedload(Movement.destination_storage),
                ),
                joinedload(SaleReturn.sale).options(
                    joinedload(Sale.movement),
                ),
            )
            .where(SaleReturn.id == id)
        )
        with rx.session() as session:
            sale_return = session.exec(statement).one_or_none()
            if sale_return:
                session.expunge(sale_return)
            return sale_return

    @classmethod
    def get_returnable_sales(cls) -> List[Sale]:
        """Продажі (не скасовані), у яких є хоча б одна ще не повернена одиниця
        (Product.is_deleted == True) — для селектора у формі повернення."""
        sold_sale_ids = (
            select(Movement.id)
            .join(
                MovementProductsCatalog,
                MovementProductsCatalog.id_movement == Movement.id,
            )
            .join(
                MovementProducts,
                MovementProducts.id_movement_product == MovementProductsCatalog.id,
            )
            .join(Product, Product.id == MovementProducts.id_product)
            .where(Movement.type == MovementsType.SALE)
            .where(Movement.status != MovementsStatus.CANCELED)
            .where(Product.is_deleted == True)
        )
        statement = (
            select(Sale)
            .options(joinedload(Sale.movement))
            .where(Sale.id.in_(sold_sale_ids))
            .order_by(Sale.id.desc())
        )
        with rx.session() as session:
            sales = session.exec(statement).all()
            if len(sales) > 0:
                session.expunge_all()
            return list(sales)

    @classmethod
    def get_sale_units(cls, sale_id: int) -> List[Product]:
        """Одиниці продажу, які ще не повернені (актуальний is_deleted == True),
        з підвантаженим product_catalog. Згруповані по позиції каталогу зовні."""
        statement = (
            select(Product)
            .options(joinedload(Product.product_catalog))
            .join(MovementProducts, MovementProducts.id_product == Product.id)
            .join(
                MovementProductsCatalog,
                MovementProductsCatalog.id == MovementProducts.id_movement_product,
            )
            .where(MovementProductsCatalog.id_movement == sale_id)
            .where(Product.is_deleted == True)
            .order_by(Product.id_product_catalog, Product.id)
        )
        with rx.session() as session:
            products = session.exec(statement).all()
            if len(products) > 0:
                session.expunge_all()
            return list(products)

    @classmethod
    def get_sale_units_for_edit(cls, sale_id: int, movement_id: int) -> List[Product]:
        """Одиниці продажу, доступні при РЕДАГУВАННІ повернення: ще не повернені
        (is_deleted == True) ПЛЮС ті, що вже входять у це саме повернення (вони
        зараз is_deleted == False, але мають лишатися в переліку для вибору)."""
        already_in_movement = (
            select(MovementProducts.id_product)
            .join(
                MovementProductsCatalog,
                MovementProductsCatalog.id == MovementProducts.id_movement_product,
            )
            .where(MovementProductsCatalog.id_movement == movement_id)
        )
        statement = (
            select(Product)
            .options(joinedload(Product.product_catalog))
            .join(MovementProducts, MovementProducts.id_product == Product.id)
            .join(
                MovementProductsCatalog,
                MovementProductsCatalog.id == MovementProducts.id_movement_product,
            )
            .where(MovementProductsCatalog.id_movement == sale_id)
            .where(
                or_(
                    Product.is_deleted == True,
                    Product.id.in_(already_in_movement),
                )
            )
            .distinct()
            .order_by(Product.id_product_catalog, Product.id)
        )
        with rx.session() as session:
            products = session.exec(statement).all()
            if len(products) > 0:
                session.expunge_all()
            return list(products)

    @classmethod
    def add_one(cls, form_data: dict, actor_login: str) -> tuple[bool, str, int]:
        """Створює повернення продажу: Movement (тип SALE_RETURN) із позиціями
        (price = компенсація за позицію, total_cost = Σ компенсацій) і дочірній
        SaleReturn. Повернені одиниці відновлюються (undelete) і переміщуються на
        склад призначення; власник кожної одиниці зберігається."""
        try:
            with rx.session() as session:
                # compensations: id позиції каталогу -> компенсація за позицію.
                compensations: Dict[int, float] = form_data.get("compensations", {})
                product_ids: List[int] = form_data.get("product_ids", [])

                bound_products = {
                    p.id: p
                    for p in session.exec(
                        select(Product).where(Product.id.in_(product_ids))
                    ).all()
                }

                catalog_to_ids: "OrderedDict[int, List[int]]" = OrderedDict()
                for pid in product_ids:
                    product = bound_products.get(pid)
                    if product is None:
                        continue
                    catalog_to_ids.setdefault(
                        product.id_product_catalog, []
                    ).append(pid)

                # Останній власник = власник, із яким ТМЦ було продано
                # (`id_incoming_owner` вихідного продажу; усі одиниці продажу
                # фільтрувалися за ним). Призначаємо його руху-поверненню.
                sale_movement = session.get(Movement, form_data["id_sale"])
                last_owner = (
                    sale_movement.id_incoming_owner
                    if sale_movement is not None
                    else None
                )

                movement: Movement = Movement(
                    type=MovementsType.SALE_RETURN,
                    id_user=form_data["id_user"],
                    id_destination_storage=form_data.get("id_destination_storage"),
                    id_incoming_owner=last_owner,
                    id_destination_owner=last_owner,
                    date=form_data.get("date"),
                    comment=form_data.get("comment"),
                    status=form_data.get("status"),
                    total_cost=0.0,
                )

                movement_products_catalog: List[MovementProductsCatalog] = []
                total_cost = 0.0
                for catalog_id, ids in catalog_to_ids.items():
                    compensation = float(compensations.get(catalog_id, 0.0))
                    units = [bound_products[i] for i in ids if i in bound_products]
                    movement_products_catalog.append(
                        MovementProductsCatalog(
                            id_product_catalog=catalog_id,
                            count=len(units),
                            price=compensation,
                            products=units,
                        )
                    )
                    total_cost += compensation

                movement.products_catalog = movement_products_catalog
                movement.total_cost = round(total_cost, 2)

                sale_return: SaleReturn = SaleReturn(
                    id_sale=form_data["id_sale"],
                    movement=movement,
                )

                # Повертаємо одиниці у залишки на склад призначення; власником
                # призначаємо останнього власника (з яким ТМЦ було продано).
                destination_storage = form_data.get("id_destination_storage")
                for pid, product in bound_products.items():
                    product.is_deleted = False
                    if destination_storage is not None:
                        product.id_storage = destination_storage
                    if last_owner is not None:
                        product.id_owner = last_owner
                    session.add(product)

                session.add(sale_return)
                session.flush()

                position_lines = diff_position_lines(
                    None, movement.products_catalog, session,
                    key=lambda x: x.id_product_catalog,
                    title=movement_position_title, label=movement_position_label,
                )
                record_action(
                    session, actor_login, sale_return.id,
                    SaleReturnCreated.for_create(movement_view(sale_return), session, lines=position_lines),
                )

                session.commit()
                return True, "Повернення продажу успішно додано", sale_return.id

        except IntegrityError as e:
            return False, "Помилка: Повернення продажу не може бути додано", -1
        except SQLAlchemyError as e:
            return False, f"Помилка: {str(e)}", -1

    @classmethod
    def edit_one(cls, form_data: dict, actor_login: str) -> tuple[bool, str, int]:
        """Редагування повернення продажу: лише статус і коментар руху."""
        try:
            with rx.session() as session:
                sale_return = session.get(SaleReturn, form_data["id"])
                if sale_return is None:
                    return False, "Помилка: Повернення не знайдено", -1

                movement = session.get(Movement, form_data["id"])
                if movement is None:
                    return False, "Помилка: Рух товару не знайдено", -1

                old_snapshot = SaleReturnUpdated.snapshot(movement_view(sale_return))

                if "status" in form_data:
                    movement.status = form_data["status"]
                if "comment" in form_data:
                    movement.comment = form_data["comment"]

                record_action(
                    session, actor_login, sale_return.id,
                    SaleReturnUpdated.from_diff(old_snapshot, movement_view(sale_return), session),
                )

                session.commit()
                return True, "Повернення продажу успішно змінено", sale_return.id

        except IntegrityError as e:
            return False, "Помилка: Повернення продажу не може бути змінено", -1
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
    def add_one(cls, request: Request, actor_login: str) -> tuple[bool, str, int]:
        try:
            with rx.session() as session:
                session.expire_on_commit = False
                session.add(request)
                session.flush()

                new_positions = [
                    (rpc.id_product_catalog, rpc.count, rpc.part_amount)
                    for rpc in (request.products_catalog or [])
                ]
                position_lines = diff_position_lines(
                    None, new_positions, session,
                    key=lambda x: x[0], title=request_position_title, label=request_position_label,
                )
                record_action(
                    session, actor_login, request.id,
                    RequestCreated.for_create(request, session, lines=position_lines),
                )

                session.commit()
                return True, "Заявку успішно створено!", request.id

        except IntegrityError as e:
            return False, "Помилка! Заявка не може бути створена.", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1

    @classmethod
    def edit_one(cls, form_data: dict, actor_login: str) -> tuple[bool, str, int]:
        """Редагування заявки (лише невиконаної): тип/отримувач/призначення/
        коментар + перелік позицій. Позиції повністю перестворюються."""
        try:
            with rx.session() as session:
                request = session.get(Request, form_data["id"])
                if request is None:
                    return False, "Помилка: заявку не знайдено", -1
                if request.status == RequestStatus.COMPLETED:
                    return False, "Помилка: виконану заявку не можна редагувати", -1

                old_snapshot = RequestUpdated.snapshot(request)

                for key in (
                    "type",
                    "id_responsible",
                    "id_destination_storage",
                    "comment",
                ):
                    if key in form_data:
                        setattr(request, key, form_data[key])

                position_lines: List = []
                if "positions" in form_data:
                    old_rows = session.exec(
                        select(RequestProductsCatalog).where(
                            RequestProductsCatalog.id_request == request.id
                        )
                    ).all()
                    old_positions = [(r.id_product_catalog, r.count, r.part_amount) for r in old_rows]
                    for old in old_rows:
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
                    position_lines = diff_position_lines(
                        old_positions, form_data["positions"], session,
                        key=lambda x: x[0], title=request_position_title, label=request_position_label,
                    )

                record_action(
                    session, actor_login, request.id,
                    RequestUpdated.from_diff(old_snapshot, request, session, lines=position_lines),
                )

                session.commit()
                return True, "Заявку успішно змінено!", request.id

        except IntegrityError as e:
            return False, "Помилка! Заявка не може бути змінена.", -1
        except SQLAlchemyError as e:
            return False, "Системна помилка!", -1

    @classmethod
    def mark_completed(cls, id: int, id_movement: int, actor_login: str) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                request = session.get(Request, id)
                if request is None:
                    return False, "Помилка: заявку не знайдено"
                old_snapshot = RequestUpdated.snapshot(request)
                request.status = RequestStatus.COMPLETED
                request.id_movement = id_movement
                record_action(
                    session, actor_login, request.id, RequestUpdated.from_diff(old_snapshot, request, session)
                )
                session.commit()
                return True, "Заявку виконано"

        except SQLAlchemyError as e:
            return False, "Системна помилка!"

    @classmethod
    def get_id_by_movement(cls, id_movement: int) -> Optional[int]:
        """id заявки, сформованої в цей рух, або None. Для інформаційного рядка
        «Рух сформовано за заявкою №N» на сторінці редагування руху."""
        with rx.session() as session:
            return session.exec(
                select(Request.id).where(Request.id_movement == id_movement)
            ).first()

    @classmethod
    def revert_completion_by_movement(cls, id_movement: int, actor_login: str) -> tuple[bool, str]:
        """Повертає заявку, сформовану в рух `id_movement`, у стан «Нова»
        (та відв'язує від руху) — викликається при скасуванні цього руху."""
        try:
            with rx.session() as session:
                request = session.exec(
                    select(Request).where(Request.id_movement == id_movement)
                ).first()
                if request is None:
                    return True, "Заявку для руху не знайдено"
                old_snapshot = RequestUpdated.snapshot(request)
                request.status = RequestStatus.NEW
                request.id_movement = None
                record_action(
                    session, actor_login, request.id, RequestUpdated.from_diff(old_snapshot, request, session)
                )
                session.commit()
                return True, "Заявку повернуто у стан «Нова»"

        except SQLAlchemyError as e:
            return False, "Системна помилка!"

    @classmethod
    def delete_one(cls, id: int, actor_login: str) -> tuple[bool, str]:
        try:
            with rx.session() as session:
                request = session.get(Request, id)
                if request is None:
                    return False, "Помилка: заявку не знайдено"
                if request.status == RequestStatus.COMPLETED:
                    return False, "Помилка: виконану заявку не можна видалити"
                deleted_action = RequestDeleted.for_delete(request, session)
                request.is_deleted = True
                record_action(session, actor_login, id, deleted_action)
                session.commit()
                return True, "Заявку видалено"

        except SQLAlchemyError as e:
            return False, "Системна помилка!"
