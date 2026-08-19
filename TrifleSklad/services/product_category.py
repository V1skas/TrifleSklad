from typing import Optional, Sequence

import reflex as rx

from TrifleSklad.audit import record_action
from TrifleSklad.audit.actions.category import CategoryCreated, CategoryDeleted, CategoryUpdated
from TrifleSklad.dao.product_category import ProductCategoryDao
from TrifleSklad.dao_legacy import ProductCatalogDAO
from TrifleSklad.models import ProductCategory
from TrifleSklad.services.errors import ServiceError


class ProductCategoryService:
    def get_list_items(self) -> Sequence[ProductCategory]:
        try:
            with rx.session() as session:
                items = ProductCategoryDao.get_all_ordered_for_tree(session)
                session.expunge_all()
                return items
        except Exception as e:
            print(f"[ProductCategoryService][get_list_items][ERROR] {e}")
            raise

    def get_by_id(self, id: int) -> Optional[ProductCategory]:
        try:
            with rx.session() as session:
                item = ProductCategoryDao.get_by_id(id, session)
                if item is not None:
                    session.expunge(item)
                return item
        except Exception as e:
            print(f"[ProductCategoryService][get_by_id][ERROR] {e}")
            raise

    def get_top_level_options(self, exclude_id: Optional[int] = None):
        try:
            with rx.session() as session:
                return ProductCategoryDao.get_top_level_options(session, exclude_id=exclude_id)
        except Exception as e:
            print(f"[ProductCategoryService][get_top_level_options][ERROR] {e}")
            raise

    def get_hierarchy_options(self):
        try:
            with rx.session() as session:
                return ProductCategoryDao.get_hierarchy_options(session)
        except Exception as e:
            print(f"[ProductCategoryService][get_hierarchy_options][ERROR] {e}")
            raise

    def get_children(self, category_id: int) -> Sequence[ProductCategory]:
        try:
            with rx.session() as session:
                items = ProductCategoryDao.get_children(category_id, session)
                session.expunge_all()
                return items
        except Exception as e:
            print(f"[ProductCategoryService][get_children][ERROR] {e}")
            raise

    def _validate_parent(self, session, item: ProductCategory) -> None:
        if item.id_parent is None:
            return
        if item.id_parent == item.id:
            raise ServiceError("Категорія не може бути батьківською для самої себе!")
        parent = ProductCategoryDao.get_by_id(item.id_parent, session)
        if parent is None or parent.id_parent is not None:
            raise ServiceError("Неможливо обрати підкатегорію як батьківську!")
        if item.id is not None and ProductCategoryDao.has_children(item.id, session):
            raise ServiceError("Неможливо призначити батьківську категорію: у категорії вже є підкатегорії!")

    def add_one(self, item: ProductCategory, actor_login: str) -> ProductCategory:
        try:
            with rx.session() as session:
                self._validate_parent(session, item)
                if ProductCategoryDao.exists_by_title(item.title, session):
                    raise ServiceError("Категорія з такою назвою вже існує!")
                ProductCategoryDao.add_one(item, session)
                session.flush()
                record_action(session, actor_login, item.id, CategoryCreated.for_create(item, session))
                session.commit()
                session.refresh(item)
                session.expunge(item)
                return item
        except ServiceError:
            raise
        except Exception as e:
            print(f"[ProductCategoryService][add_one][ERROR] {e}")
            raise

    def edit_one(self, item: ProductCategory, actor_login: str) -> ProductCategory:
        try:
            with rx.session() as session:
                self._validate_parent(session, item)
                if ProductCategoryDao.exists_by_title(item.title, session, exclude_id=item.id):
                    raise ServiceError("Категорія з такою назвою вже існує!")
                old_snapshot = CategoryUpdated.snapshot(ProductCategoryDao.get_by_id(item.id, session))
                merged = ProductCategoryDao.edit_one(item, session)
                record_action(
                    session, actor_login, item.id, CategoryUpdated.from_diff(old_snapshot, merged, session)
                )
                session.commit()
                session.refresh(merged)
                session.expunge(merged)
                return merged
        except ServiceError:
            raise
        except Exception as e:
            print(f"[ProductCategoryService][edit_one][ERROR] {e}")
            raise

    def delete_one(self, id: int, actor_login: str) -> bool:
        try:
            # Тимчасові залежності від dao_legacy — заміняться на нативний
            # ProductCatalogDao, коли products переїде на нові шари (в цій же хвилі).
            if len(ProductCatalogDAO.get_by_category(id)) > 0:
                raise ServiceError("Неможливо видалити категорію, у яку входить ТМЦ з каталогу!")
            with rx.session() as session:
                if ProductCategoryDao.has_children(id, session):
                    raise ServiceError("Неможливо видалити категорію, у якої є підкатегорії!")
                item = ProductCategoryDao.get_by_id(id, session)
                if item is None:
                    return False
                item.is_deleted = True
                ProductCategoryDao.edit_one(item, session)
                record_action(session, actor_login, id, CategoryDeleted.for_delete(item, session))
                session.commit()
                return True
        except ServiceError:
            raise
        except Exception as e:
            print(f"[ProductCategoryService][delete_one][ERROR] {e}")
            return False
