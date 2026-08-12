from dataclasses import dataclass
from typing import Callable, Dict, List, Sequence

from sqlmodel import Session, select

from TrifleSklad.dao.product import ProductDao
from TrifleSklad.declared import MovementsType
from TrifleSklad.models import Movement, MovementProducts, MovementProductsCatalog, Product, SaleReturn
from TrifleSklad.services.errors import ServiceError

# УВАГА: у цьому модулі (як і в services/movement_edit.py) заборонені мутуючі
# виклики з `dao_legacy` — кожен із них відкриває власну сесію й комітить, що
# розриває єдину транзакцію перепроводки. Лише `dao/*` із сесією аргументом.

# Перевірка джерела: де саме має фізично лежати одиниця, щоб її можна було
# включити до руху (після revert старого ефекту).
SOURCE_STORAGE_OWNER = "storage_owner"
SOURCE_STORAGE = "storage"
SOURCE_NONE = "none"
SOURCE_SOLD_UNITS = "sold_units"


@dataclass(frozen=True)
class MovementEffect:
    """Ефект руху на залишки: як його відкотити і як застосувати наново.
    Точне віддзеркалення семантики `Add*State.add_one` / `View*State.on_click_cancel`."""

    revert: Callable[[Session, Movement, List[int]], None]
    apply: Callable[[Session, Movement, Sequence[Product]], None]
    source_check: str


def _revert_noop(_session: Session, _movement: Movement, _old_unit_ids: List[int]) -> None:
    """Постачання: одиниці породжені самим рухом, відкочувати місце нема куди."""


def _revert_restore(session: Session, _movement: Movement, old_unit_ids: List[int]) -> None:
    ProductDao.restore(session, old_unit_ids)


def _revert_to_source(session: Session, movement: Movement, old_unit_ids: List[int]) -> None:
    """Повертає одиниці в джерело самого руху — `id_incoming_storage`/`id_incoming_owner`.

    Під інваріантом «у русі лише ТМЦ того складу й власника, що в шапці» (він
    забезпечується діалогом вибору при створенні) шапка й є достовірним «звідки»
    для кожної одиниці. Це замінює колишній обхід ланцюжка попередніх рухів,
    який ламався на даних, що порушують інваріант. У `save_full` revert
    виконується ДО перезапису шапки,
    тож тут читається стара шапка — вірно і для правки, і для скасування.
    """
    ProductDao.relocate(
        session, old_unit_ids, movement.id_incoming_owner, movement.id_incoming_storage
    )


def _revert_to_source_storage(session: Session, movement: Movement, old_unit_ids: List[int]) -> None:
    """Як `_revert_to_source`, але для повернення (RETURN): власник не задається —
    кожна одиниця зберігає свого, змінюється лише склад."""
    ProductDao.relocate_storage(session, old_unit_ids, movement.id_incoming_storage)


def _revert_restore_and_source(
    session: Session, movement: Movement, old_unit_ids: List[int]
) -> None:
    """Видача/видача клієнту: спершу повернути списані витратні одиниці
    (`is_deleted=False`), потім усі — назад у джерело руху."""
    ProductDao.restore(session, old_unit_ids)
    ProductDao.relocate(
        session, old_unit_ids, movement.id_incoming_owner, movement.id_incoming_storage
    )


def _revert_soft_delete(session: Session, _movement: Movement, old_unit_ids: List[int]) -> None:
    """Повернення продажу: одиниці повертаються у стан «продано»."""
    ProductDao.soft_delete(session, old_unit_ids)


def _apply_relocate(session: Session, movement: Movement, units: Sequence[Product]) -> None:
    ProductDao.relocate(
        session,
        [unit.id for unit in units],
        movement.id_destination_owner,
        movement.id_destination_storage,
    )


def _apply_relocate_storage(session: Session, movement: Movement, units: Sequence[Product]) -> None:
    ProductDao.relocate_storage(session, [unit.id for unit in units], movement.id_destination_storage)


def _apply_soft_delete(session: Session, _movement: Movement, units: Sequence[Product]) -> None:
    ProductDao.soft_delete(session, [unit.id for unit in units])


def _apply_issue_relocation(session: Session, movement: Movement, units: Sequence[Product]) -> None:
    ProductDao.apply_issue_relocation(
        session, units, movement.id_destination_owner, movement.id_destination_storage
    )


def _apply_sale_return(session: Session, movement: Movement, units: Sequence[Product]) -> None:
    """Повернення продажу: одиниці перестають бути проданими й лягають на склад
    призначення з власником, з яким їх було продано."""
    unit_ids = [unit.id for unit in units]
    ProductDao.restore(session, unit_ids)
    ProductDao.relocate(
        session, unit_ids, movement.id_destination_owner, movement.id_destination_storage
    )


_EFFECTS: Dict[int, MovementEffect] = {
    MovementsType.ADMISSION: MovementEffect(_revert_noop, _apply_relocate, SOURCE_NONE),
    MovementsType.WRITE_OFF: MovementEffect(_revert_restore, _apply_soft_delete, SOURCE_STORAGE_OWNER),
    MovementsType.MOVEMENT: MovementEffect(
        _revert_to_source, _apply_relocate, SOURCE_STORAGE_OWNER
    ),
    MovementsType.ISSUE: MovementEffect(
        _revert_restore_and_source, _apply_issue_relocation, SOURCE_STORAGE_OWNER
    ),
    # Продаж місця не змінює — відкочується лише ознака «продано»
    # (так само, як ViewSaleState.on_click_cancel).
    MovementsType.SALE: MovementEffect(_revert_restore, _apply_soft_delete, SOURCE_STORAGE_OWNER),
    MovementsType.RETURN: MovementEffect(
        _revert_to_source_storage, _apply_relocate_storage, SOURCE_STORAGE
    ),
    MovementsType.SALE_RETURN: MovementEffect(
        _revert_soft_delete, _apply_sale_return, SOURCE_SOLD_UNITS
    ),
    MovementsType.CLIENT_ISSUE: MovementEffect(
        _revert_restore_and_source, _apply_issue_relocation, SOURCE_STORAGE_OWNER
    ),
}


def effect_for(movement_type: int) -> MovementEffect:
    effect = _EFFECTS.get(movement_type)
    if effect is None:
        raise ServiceError("Невідомий тип руху — перепроводка неможлива!")
    return effect


def revert(session: Session, movement: Movement, old_unit_ids: List[int]) -> None:
    """Відкочує ефект руху на залишки. Виконується ПЕРЕД `validate_source`:
    одиниця, що лишається у складі, повертається в джерело саме тут."""
    effect_for(movement.type).revert(session, movement, old_unit_ids)
    session.flush()


def apply(session: Session, movement: Movement, units: Sequence[Product]) -> None:
    """Застосовує ефект руху до підсумкового переліку одиниць."""
    effect_for(movement.type).apply(session, movement, units)
    session.flush()


def _sold_unit_ids(session: Session, sale_id: int) -> set:
    statement = (
        select(MovementProducts.id_product)
        .join(
            MovementProductsCatalog,
            MovementProducts.id_movement_product == MovementProductsCatalog.id,
        )
        .where(MovementProductsCatalog.id_movement == sale_id)
    )
    return set(session.exec(statement).all())


def validate_source(session: Session, movement: Movement, units: Sequence[Product]) -> None:
    """Перевіряє, що кожна одиниця підсумкового складу фактично перебуває в
    джерелі руху (стан ПІСЛЯ revert). Захищає від правки шапки, яка зробила б
    історію суперечливою: одиниця в русі, якої в тому місці ніколи не було.

    ServiceError із переліком id одиниць-порушниць.
    """
    check = effect_for(movement.type).source_check
    if check == SOURCE_NONE:
        return

    if check == SOURCE_SOLD_UNITS:
        sale_return: SaleReturn = session.get(SaleReturn, movement.id)
        if sale_return is None or sale_return.id_sale is None:
            raise ServiceError("Не вказано продаж, за яким оформлюється повернення!")
        allowed = _sold_unit_ids(session, sale_return.id_sale)
        wrong = [unit.id for unit in units if unit.id not in allowed]
        if wrong:
            raise ServiceError(
                "Ці одиниці не входять до обраного продажу: " + ", ".join(f"№{i}" for i in wrong) + "!"
            )
        return

    wrong = []
    for unit in units:
        if unit.is_deleted:
            wrong.append(unit.id)
        elif unit.id_storage != movement.id_incoming_storage:
            wrong.append(unit.id)
        elif check == SOURCE_STORAGE_OWNER and unit.id_owner != movement.id_incoming_owner:
            wrong.append(unit.id)
    if wrong:
        raise ServiceError(
            "Ці одиниці не перебувають у вибраному джерелі руху: "
            + ", ".join(f"№{i}" for i in wrong)
            + "! Оберіть одиниці, що фактично там знаходяться."
        )
