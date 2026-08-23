from collections import OrderedDict
from typing import Dict, List, Optional, Sequence, Tuple

from sqlmodel import Session, select

from TrifleSklad.declared import MovementsStatus, MovementsType, sale_line_cost
from TrifleSklad.models import Movement, MovementProducts, MovementProductsCatalog, Product


class MovementDao:
    """Session-first запити й перебудова складу руху: сесія аргументом, БЕЗ
    commit. Використовується транзакційним шляхом повного редагування
    (`services/movement_edit.py`) — див. пояснення в `dao/product.py`.
    """

    @staticmethod
    def get_unit_ids(session: Session, movement_id: int) -> List[int]:
        """id усіх одиниць, що входять у рух (movements_products_catalog -> movements_products)."""
        statement = (
            select(MovementProducts.id_product)
            .join(
                MovementProductsCatalog,
                MovementProducts.id_movement_product == MovementProductsCatalog.id,
            )
            .where(MovementProductsCatalog.id_movement == movement_id)
            .distinct()
        )
        return list(session.exec(statement).all())

    @staticmethod
    def get_movements_with_units(
        session: Session,
        unit_ids: List[int],
        *,
        after_id: Optional[int] = None,
        exclude_movement_id: Optional[int] = None,
    ) -> List[Movement]:
        """Рухи, що містять будь-яку з указаних одиниць, за зростанням id.
        `after_id` — лише рухи з БІЛЬШИМ id (конфлікт-чек редагування).

        Скасовані рухи виключаються (TS-56): відкат тепер бере джерело з
        шапки руху (`_revert_to_source`/... у `services/movement_posting.py`,
        TS-48-fix), а не реконструює його ланцюжком попередніх рухів, тож
        скасований пізніший рух більше не заважає редагувати більш ранній.
        """
        if not unit_ids:
            return []
        statement = (
            select(Movement)
            .join(MovementProductsCatalog, MovementProductsCatalog.id_movement == Movement.id)
            .join(
                MovementProducts,
                MovementProducts.id_movement_product == MovementProductsCatalog.id,
            )
            .where(MovementProducts.id_product.in_(unit_ids))
            .where(Movement.status != MovementsStatus.CANCELED)
        )
        if after_id is not None:
            statement = statement.where(Movement.id > after_id)
        if exclude_movement_id is not None:
            statement = statement.where(Movement.id != exclude_movement_id)
        return list(session.exec(statement.distinct().order_by(Movement.id)).all())

    @staticmethod
    def first_movement_id_for_unit(session: Session, unit_id: int) -> Optional[int]:
        """Найменший id руху, до якого одиниця взагалі входила. Ознака «осколок
        породжений саме цим рухом»: гвард редагування вже гарантував відсутність
        пізніших рухів, тож «перший == поточний» означає «більше ніде не бере участі»."""
        statement = (
            select(MovementProductsCatalog.id_movement)
            .join(
                MovementProducts,
                MovementProducts.id_movement_product == MovementProductsCatalog.id,
            )
            .where(MovementProducts.id_product == unit_id)
            .order_by(MovementProductsCatalog.id_movement)
            .limit(1)
        )
        return session.exec(statement).first()

    @staticmethod
    def clear_positions(session: Session, movement_id: int) -> None:
        """Видаляє позиції руху разом із рядками зв'язку — самі `products` не
        чіпає (одиниці живуть незалежно від складу руху)."""
        positions = session.exec(
            select(MovementProductsCatalog).where(MovementProductsCatalog.id_movement == movement_id)
        ).all()
        for position in positions:
            # Спершу рвемо зв'язки (secondary-рядки), потім видаляємо позицію:
            # інакше явне видалення рядків зв'язку конфліктує з каскадом
            # relationship і SQLAlchemy лається на «0 rows matched».
            position.products = []
            session.add(position)
        session.flush()
        for position in positions:
            session.delete(position)
        session.flush()

    @staticmethod
    def rebuild_positions(
        session: Session,
        movement: Movement,
        units: Sequence[Product],
        prices: Dict[int, float],
        *,
        catalog_meta: Dict[int, Tuple[bool, int]],
    ) -> float:
        """Перебудовує позиції руху за підсумковим переліком одиниць, групуючи їх
        за `id_product_catalog`; ціна позиції береться з `prices` за id каталогу.

        Повертає `total_cost` за правилами типу руху: продаж — через
        `declared.sale_line_cost` (частина подільної одиниці оплачується
        пропорційно), повернення продажу — сума компенсацій по позиціях, решта
        типів вартості не несуть. Для постачання не використовується — там
        позиції з кількістю й цінами задає користувач у формі.
        """
        grouped: "OrderedDict[int, List[Product]]" = OrderedDict()
        for unit in units:
            grouped.setdefault(unit.id_product_catalog, []).append(unit)

        total_cost = 0.0
        for catalog_id, catalog_units in grouped.items():
            price = float(prices.get(catalog_id, 0.0))
            position = MovementProductsCatalog(
                id_movement=movement.id,
                id_product_catalog=catalog_id,
                count=len(catalog_units),
                price=price,
                products=list(catalog_units),
            )
            session.add(position)

            if movement.type == MovementsType.SALE:
                divisible, capacity = catalog_meta.get(catalog_id, (False, 0))
                total_cost += sale_line_cost(
                    price, [(unit.count, divisible, capacity) for unit in catalog_units]
                )
            elif movement.type == MovementsType.SALE_RETURN:
                total_cost += price

        session.flush()
        return round(total_cost, 2)
