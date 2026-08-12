from typing import Dict, List, Optional, Sequence

from sqlalchemy.orm import joinedload
from sqlmodel import Session, select

from TrifleSklad.models import Product


class ProductDao:
    """Session-first примітиви над одиницями ТМЦ: сесія аргументом, БЕЗ commit —
    щоб перепроводка руху (revert -> зміни -> apply) виконувалась однією
    транзакцією.

    Легасі-аналоги в `dao_legacy.ProductDAO` відкривають власну сесію й комітять
    усередині, тому в транзакційному шляху редагування непридатні: помилка на
    середині лишила б залишки в розірваному стані.
    """

    @staticmethod
    def get_by_ids(session: Session, ids: List[int], *, with_catalog: bool = True) -> Sequence[Product]:
        """Одиниці за списком id. `is_deleted` НЕ фільтрується: у русі можуть
        бути списані/продані одиниці (напр. склад повернення продажу)."""
        if not ids:
            return []
        statement = select(Product).where(Product.id.in_(ids))
        if with_catalog:
            statement = statement.options(joinedload(Product.product_catalog))
        return session.exec(statement).unique().all()

    @staticmethod
    def soft_delete(session: Session, ids: List[int]) -> None:
        for product in ProductDao.get_by_ids(session, ids, with_catalog=False):
            product.is_deleted = True
            session.add(product)

    @staticmethod
    def restore(session: Session, ids: List[int]) -> None:
        for product in ProductDao.get_by_ids(session, ids, with_catalog=False):
            product.is_deleted = False
            session.add(product)

    @staticmethod
    def relocate(session: Session, ids: List[int], owner_id: int, storage_id: int) -> None:
        for product in ProductDao.get_by_ids(session, ids, with_catalog=False):
            product.id_owner = owner_id
            product.id_storage = storage_id
            session.add(product)

    @staticmethod
    def relocate_storage(session: Session, ids: List[int], storage_id: int) -> None:
        """Змінює лише місце. Для повернення з площадки/відділу (`RETURN`), де
        кожна одиниця зберігає свого власника."""
        for product in ProductDao.get_by_ids(session, ids, with_catalog=False):
            product.id_storage = storage_id
            session.add(product)

    @staticmethod
    def apply_issue_relocation(
        session: Session, units: Sequence[Product], owner_id: int, storage_id: int
    ) -> None:
        """Ефект видачі на площадку/відділ/клієнта: витратний (неунікальний) ТМЦ
        списується на місці, унікальний (серійний) — переїжджає на призначення.
        Та сама бізнес-логіка, що в `dao_legacy.ProductDAO.apply_issue_relocation`."""
        write_off_ids = [
            unit.id for unit in units if unit.product_catalog is not None and not unit.product_catalog.uniq
        ]
        movable_ids = [unit.id for unit in units if unit.id not in write_off_ids]
        if write_off_ids:
            ProductDao.soft_delete(session, write_off_ids)
        if movable_ids:
            ProductDao.relocate(session, movable_ids, owner_id, storage_id)

    @staticmethod
    def set_serial_numbers(session: Session, serials: Dict[int, str]) -> None:
        if not serials:
            return
        for product in ProductDao.get_by_ids(session, list(serials), with_catalog=False):
            product.serial_number = serials[product.id]
            session.add(product)

    @staticmethod
    def split(session: Session, parent_id: int, amount: float) -> Product:
        """Відділяє від подільної одиниці частину `amount`: створює дочірню
        одиницю (`id_parent`) у тому ж місці й зменшує залишок батька.

        ValueError — якщо батька немає або обсяг поза межами (1..count-1).
        """
        parent: Optional[Product] = session.get(Product, parent_id)
        if parent is None:
            raise ValueError(f"Одиницю №{parent_id} не знайдено!")
        if amount < 1 or amount >= parent.count:
            raise ValueError(
                f"Некоректний обсяг відділення для одиниці №{parent_id}: {amount} (залишок {parent.count})!"
            )

        child = Product(
            serial_number=parent.serial_number,
            id_product_catalog=parent.id_product_catalog,
            id_storage=parent.id_storage,
            id_owner=parent.id_owner,
            id_parent=parent.id,
            count=amount,
            is_deleted=parent.is_deleted,
        )
        parent.count -= amount
        session.add(parent)
        session.add(child)
        session.flush()
        child.product_catalog = parent.product_catalog
        return child

    @staticmethod
    def merge_child_into_parent(session: Session, child: Product) -> bool:
        """Зливає осколок назад у батька (`parent.count += child.count`, осколок
        видаляється). Викликається, коли одиницю-осколок прибрали зі складу
        руху, що її й породив, — інакше редагування плодить сміттєві одиниці.

        False (осколок лишається самостійною одиницею), якщо батька немає, він
        видалений або лежить в іншому місці — зливати в такому разі не можна:
        це змінило б залишок у чужій точці зберігання.
        """
        if child.id_parent is None:
            return False
        parent: Optional[Product] = session.get(Product, child.id_parent)
        if parent is None or parent.is_deleted:
            return False
        if parent.id_storage != child.id_storage or parent.id_owner != child.id_owner:
            return False

        parent.count += child.count
        session.add(parent)
        session.delete(child)
        return True
