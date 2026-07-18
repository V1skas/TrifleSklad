import math
from typing import List, Optional, Sequence, Tuple

from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, func, select

from TrifleSklad.dao.product_category import ProductCategoryDao
from TrifleSklad.models import ProductCatalog


class ProductCatalogDao:
    @staticmethod
    def get_by_id(id: int, session: Session, with_del: bool = False) -> Optional[ProductCatalog]:
        statement = select(ProductCatalog).options(joinedload(ProductCatalog.category)).where(ProductCatalog.id == id)
        if not with_del:
            statement = statement.where(ProductCatalog.is_deleted == False)
        return session.exec(statement).unique().one_or_none()

    @staticmethod
    def exists_by_title_unit(title: str, unit: str, session: Session, exclude_id: Optional[int] = None) -> bool:
        statement = (
            select(ProductCatalog)
            .where(ProductCatalog.title == title)
            .where(ProductCatalog.unit == unit)
            .where(ProductCatalog.is_deleted == False)
        )
        if exclude_id is not None:
            statement = statement.where(ProductCatalog.id != exclude_id)
        return session.exec(statement).one_or_none() is not None

    @staticmethod
    def get_list_units(session: Session) -> List[str]:
        statement = select(ProductCatalog.unit).distinct()
        units = session.exec(statement).all()
        return sorted({u.strip() for u in units if u})

    @staticmethod
    def get_count_with_search(session: Session, search_str: Optional[str] = None, category_id: Optional[str] = None) -> int:
        condition = ProductCatalog.title.ilike(f"%{search_str.strip()}%") if search_str and search_str.strip() else True
        statement = select(func.count(ProductCatalog.id)).where(condition).where(ProductCatalog.is_deleted == False)
        if category_id and category_id not in ("", "all"):
            children = ProductCategoryDao.get_children(int(category_id), session)
            ids = [int(category_id)] + [c.id for c in children]
            statement = statement.where(ProductCatalog.id_category.in_(ids))
        return session.exec(statement).one()

    @staticmethod
    def get_page(
        session: Session,
        page: int = 1,
        count_items: int = 0,
        limit: int = 20,
        search_str: Optional[str] = None,
        category_id: Optional[str] = None,
    ) -> Tuple[int, Sequence[ProductCatalog]]:
        condition = ProductCatalog.title.ilike(f"%{search_str.strip()}%") if search_str and search_str.strip() else True
        total_pages = max(math.ceil(count_items / limit), 1)
        skip = (page - 1) * limit

        statement = (
            select(ProductCatalog)
            .options(selectinload(ProductCatalog.category))
            .where(ProductCatalog.is_deleted == False)
            .where(condition)
        )
        if category_id and category_id not in ("", "all"):
            children = ProductCategoryDao.get_children(int(category_id), session)
            ids = [int(category_id)] + [c.id for c in children]
            statement = statement.where(ProductCatalog.id_category.in_(ids))
        statement = statement.offset(skip).limit(limit)

        items = session.exec(statement).all()
        return total_pages, items

    @staticmethod
    def add_one(item: ProductCatalog, session: Session) -> ProductCatalog:
        session.add(item)
        return item

    @staticmethod
    def edit_one(item: ProductCatalog, session: Session) -> ProductCatalog:
        return session.merge(item)
