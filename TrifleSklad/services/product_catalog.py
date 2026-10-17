from typing import List, Optional, Sequence, Tuple

import reflex as rx

from TrifleSklad.audit import record_action
from TrifleSklad.audit.actions.product_catalog import (
    ProductCatalogCreated,
    ProductCatalogDeleted,
    ProductCatalogUpdated,
)
from TrifleSklad.dao.product_catalog import ProductCatalogDao
from TrifleSklad.models import ProductCatalog
from TrifleSklad.services.errors import ServiceError


class ProductCatalogService:
    def get_by_id(self, id: int, with_del: bool = False) -> Optional[ProductCatalog]:
        try:
            with rx.session() as session:
                item = ProductCatalogDao.get_by_id(id, session, with_del=with_del)
                if item is not None:
                    session.expunge(item)
                return item
        except Exception as e:
            print(f"[ProductCatalogService][get_by_id][ERROR] {e}")
            raise

    def get_list_units(self) -> List[str]:
        try:
            with rx.session() as session:
                return ProductCatalogDao.get_list_units(session)
        except Exception as e:
            print(f"[ProductCatalogService][get_list_units][ERROR] {e}")
            raise

    def get_page(
        self, page: int, limit: int, search_str: Optional[str], category_id: Optional[str]
    ) -> Tuple[int, Sequence[ProductCatalog]]:
        try:
            with rx.session() as session:
                count = ProductCatalogDao.get_count_with_search(session, search_str, category_id)
                total_pages, items = ProductCatalogDao.get_page(
                    session, page=page, count_items=count, limit=limit, search_str=search_str, category_id=category_id
                )
                session.expunge_all()
                return total_pages, items
        except Exception as e:
            print(f"[ProductCatalogService][get_page][ERROR] {e}")
            raise

    def add_one(self, item: ProductCatalog, actor_login: str) -> ProductCatalog:
        try:
            with rx.session() as session:
                if ProductCatalogDao.exists_by_title_unit(item.title, item.unit, session):
                    raise ServiceError("Товар з такою назвою та одиницею виміру вже існує!")
                ProductCatalogDao.add_one(item, session)
                session.flush()
                record_action(session, actor_login, item.id, ProductCatalogCreated.for_create(item, session))
                session.commit()
                session.refresh(item)
                session.expunge(item)
                return item
        except ServiceError:
            raise
        except Exception as e:
            print(f"[ProductCatalogService][add_one][ERROR] {e}")
            raise

    def edit_one(self, item: ProductCatalog, actor_login: str) -> ProductCatalog:
        try:
            with rx.session() as session:
                if ProductCatalogDao.exists_by_title_unit(item.title, item.unit, session, exclude_id=item.id):
                    raise ServiceError("Товар з такою назвою та одиницею виміру вже існує!")
                old_snapshot = ProductCatalogUpdated.snapshot(ProductCatalogDao.get_by_id(item.id, session))
                merged = ProductCatalogDao.edit_one(item, session)
                record_action(
                    session, actor_login, item.id, ProductCatalogUpdated.from_diff(old_snapshot, merged, session)
                )
                session.commit()
                session.refresh(merged)
                session.expunge(merged)
                return merged
        except ServiceError:
            raise
        except Exception as e:
            print(f"[ProductCatalogService][edit_one][ERROR] {e}")
            raise

    def delete_one(self, id: int, actor_login: str) -> bool:
        try:
            with rx.session() as session:
                item = ProductCatalogDao.get_by_id(id, session)
                if item is None:
                    return False
                item.is_deleted = True
                ProductCatalogDao.edit_one(item, session)
                record_action(session, actor_login, id, ProductCatalogDeleted.for_delete(item, session))
                session.commit()
                return True
        except Exception as e:
            print(f"[ProductCatalogService][delete_one][ERROR] {e}")
            return False
