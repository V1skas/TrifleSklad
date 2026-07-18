from typing import Dict, List, Optional, Sequence, Tuple

from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, select

from TrifleSklad.models import ProductCategory


class ProductCategoryDao:
    @staticmethod
    def get_all(session: Session, with_del: bool = False) -> Sequence[ProductCategory]:
        statement = select(ProductCategory)
        if not with_del:
            statement = statement.where(ProductCategory.is_deleted == False)
        return session.exec(statement).all()

    @staticmethod
    def get_by_id(id: int, session: Session, with_del: bool = False) -> Optional[ProductCategory]:
        statement = select(ProductCategory).options(joinedload(ProductCategory.products)).where(ProductCategory.id == id)
        if not with_del:
            statement = statement.where(ProductCategory.is_deleted == False)
        return session.exec(statement).unique().one_or_none()

    @staticmethod
    def exists_by_title(title: str, session: Session, exclude_id: Optional[int] = None) -> bool:
        statement = select(ProductCategory).where(ProductCategory.title == title).where(ProductCategory.is_deleted == False)
        if exclude_id is not None:
            statement = statement.where(ProductCategory.id != exclude_id)
        return session.exec(statement).one_or_none() is not None

    @staticmethod
    def has_children(category_id: int, session: Session) -> bool:
        statement = (
            select(ProductCategory.id)
            .where(ProductCategory.id_parent == category_id)
            .where(ProductCategory.is_deleted == False)
        )
        return session.exec(statement).first() is not None

    @staticmethod
    def get_children(category_id: int, session: Session) -> Sequence[ProductCategory]:
        statement = (
            select(ProductCategory)
            .where(ProductCategory.id_parent == category_id)
            .where(ProductCategory.is_deleted == False)
        )
        return session.exec(statement).all()

    @staticmethod
    def get_top_level_options(session: Session, exclude_id: Optional[int] = None) -> List[Tuple[str, str]]:
        statement = (
            select(ProductCategory)
            .where(ProductCategory.id_parent == None)
            .where(ProductCategory.is_deleted == False)
            .order_by(ProductCategory.title)
        )
        categories = session.exec(statement).all()
        return [(str(c.id), c.title) for c in categories if c.id != exclude_id]

    @staticmethod
    def get_all_ordered_for_tree(session: Session) -> List[ProductCategory]:
        """Живі категорії, впорядковані: батько (алфавітно), одразу за ним —
        його діти (алфавітно)."""
        categories = ProductCategoryDao.get_all(session)
        top_level = sorted((c for c in categories if c.id_parent is None), key=lambda c: c.title)
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

    @staticmethod
    def get_hierarchy_options(session: Session) -> List[Tuple[str, str]]:
        """(id, назва) для всіх категорій, з відступом "— " для дочірніх —
        єдина точка формування підписів для селектів категорій."""
        return [
            (str(c.id), c.title if c.id_parent is None else f"— {c.title}")
            for c in ProductCategoryDao.get_all_ordered_for_tree(session)
        ]

    @staticmethod
    def add_one(item: ProductCategory, session: Session) -> ProductCategory:
        session.add(item)
        return item

    @staticmethod
    def edit_one(item: ProductCategory, session: Session) -> ProductCategory:
        return session.merge(item)
