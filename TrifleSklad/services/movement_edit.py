from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple

import reflex as rx
from sqlmodel import Session, select

from TrifleSklad.actions import Action
from TrifleSklad.audit import record_action
from TrifleSklad.audit.actions.movement import movement_actions_for
from TrifleSklad.audit.labels import (
    diff_position_lines,
    diff_unit_lines,
    movement_position_label,
    movement_position_title,
    movement_view,
    snapshot_position_lines,
    snapshot_unit_rows,
)
from TrifleSklad.dao.movement import MovementDao
from TrifleSklad.dao.product import ProductDao
from TrifleSklad.dao.user import UserDao
from TrifleSklad.declared import MOVEMENT_FULL_EDIT_WINDOW_DAYS, MovementsStatus, MovementsType
from TrifleSklad.models import (
    Admission,
    ClientIssue,
    Issue,
    Movement,
    Product,
    ProductCatalog,
    Sale,
    SaleReturn,
)
from TrifleSklad.services import movement_posting
from TrifleSklad.services.errors import ServiceError
from TrifleSklad.utils.clock import now_local

# УВАГА: у транзакційному шляху цього модуля заборонені мутуючі виклики з
# `dao_legacy` — кожен із них відкриває власну сесію й комітить усередині, що
# зруйнувало б атомарність перепроводки (revert -> зміни -> apply). Працюємо
# лише через `dao/*` із сесією аргументом.

# Право «повне редагування» на кожен тип руху.
FULL_EDIT_ACTION: Dict[int, Action] = {
    MovementsType.ADMISSION: Action.ADMISSIONS_EDIT_FULL,
    MovementsType.WRITE_OFF: Action.WRITE_OFFS_EDIT_FULL,
    MovementsType.MOVEMENT: Action.MOVEMENTS_EDIT_FULL,
    MovementsType.ISSUE: Action.ISSUES_EDIT_FULL,
    MovementsType.SALE: Action.SALES_EDIT_FULL,
    MovementsType.RETURN: Action.RETURNS_EDIT_FULL,
    MovementsType.SALE_RETURN: Action.SALE_RETURNS_EDIT_FULL,
    MovementsType.CLIENT_ISSUE: Action.CLIENT_ISSUES_EDIT_FULL,
}

# Дочірня сутність руху; типи без запису тут (списання/переміщення/повернення)
# живуть однією строкою `movements`.
CHILD_MODEL: Dict[int, Any] = {
    MovementsType.ADMISSION: Admission,
    MovementsType.ISSUE: Issue,
    MovementsType.SALE: Sale,
    MovementsType.SALE_RETURN: SaleReturn,
    MovementsType.CLIENT_ISSUE: ClientIssue,
}


@dataclass(frozen=True)
class Editability:
    """Вердикт «чи можна повністю редагувати цей рух» — і для UI (плашка з
    поясненням), і для повторної серверної перевірки при збереженні."""

    allowed: bool
    reason_code: str = ""
    message: str = ""
    conflicts: List[Movement] = field(default_factory=list)


@dataclass
class FullEditPayload:
    """Повний склад правки руху. `unit_plan` — (id одиниці, обсяг відділення або
    None = цілком): реальний поділ подільної одиниці виконується всередині
    транзакції збереження, а не заздалегідь."""

    movement_id: int
    movement_type: int
    reason: str
    header: Dict[str, Any] = field(default_factory=dict)
    child: Dict[str, Any] = field(default_factory=dict)
    unit_plan: List[Tuple[int, Optional[float]]] = field(default_factory=list)
    prices: Dict[int, float] = field(default_factory=dict)
    serials: Dict[int, str] = field(default_factory=dict)


class MovementEditService:
    def editability(self, movement_id: int, movement_type: int, actor_login: str) -> Editability:
        """Розрахунок доступності повного редагування для сторінки редагування.
        Той самий гвард повторюється всередині `save_full` у транзакції
        збереження — щоб його не можна було обійти прямим викликом події."""
        try:
            with rx.session() as session:
                movement: Optional[Movement] = session.get(Movement, movement_id)
                return self._editability(session, movement, movement_type, actor_login)
        except Exception as e:
            print(f"[MovementEditService][editability][ERROR] {e}")
            return Editability(False, "error", "Не вдалося перевірити доступність редагування.")

    def _editability(
        self,
        session: Session,
        movement: Optional[Movement],
        movement_type: int,
        actor_login: str,
    ) -> Editability:
        if movement is None:
            return Editability(False, "not_found", "Рух не знайдено.")
        if movement.type != movement_type:
            return Editability(False, "wrong_type", "Рух належить до іншого типу операції.")
        if movement.status == MovementsStatus.CANCELED:
            return Editability(False, "canceled", "Скасований рух не редагується.")

        required = FULL_EDIT_ACTION.get(movement_type)
        # Права читаємо з БД, а не з AppState — клієнтський стан не є джерелом
        # істини для серверної перевірки.
        if required is None or required.value not in UserDao.get_effective_actions(actor_login, session):
            return Editability(
                False, "no_permission", "У Вас немає права на повне редагування цієї операції."
            )

        try:
            movement_date = date.fromisoformat(movement.date)
        except (TypeError, ValueError):
            return Editability(False, "bad_date", "Некоректна дата руху — повне редагування недоступне.")
        days = (now_local().date() - movement_date).days
        if days > MOVEMENT_FULL_EDIT_WINDOW_DAYS:
            return Editability(
                False,
                "window_expired",
                f"Минув строк повного редагування ({MOVEMENT_FULL_EDIT_WINDOW_DAYS} дн. від дати руху).",
            )

        unit_ids = MovementDao.get_unit_ids(session, movement.id)
        conflicts = MovementDao.get_movements_with_units(
            session, unit_ids, after_id=movement.id, exclude_movement_id=movement.id
        )
        if conflicts:
            return Editability(
                False,
                "conflicts",
                "Одиниці ТМЦ цього руху беруть участь у пізніших рухах — повне редагування "
                "недоступне. Спочатку скасуйте пізніші рухи.",
                conflicts,
            )
        return Editability(True)

    def save_full(self, payload: FullEditPayload, actor_login: str) -> int:
        """Повна перепроводка руху в ОДНІЙ транзакції:
        revert старого ефекту -> зміна шапки й складу -> перевірка джерела ->
        перебудова позицій -> apply нового ефекту -> аудит -> commit.

        Помилка на будь-якому кроці відкочує все, включно з осколками, що їх
        створив поділ подільних одиниць.
        """
        reason = payload.reason.strip()
        if not reason:
            raise ServiceError("Вкажіть причину коригування!")

        try:
            with rx.session() as session:
                movement: Optional[Movement] = session.get(Movement, payload.movement_id)
                verdict = self._editability(session, movement, payload.movement_type, actor_login)
                if not verdict.allowed:
                    raise ServiceError(verdict.message)

                child_model = CHILD_MODEL.get(payload.movement_type)
                child = session.get(child_model, movement.id) if child_model is not None else None
                if child_model is not None and child is None:
                    raise ServiceError("Дочірній запис руху не знайдено!")

                _, Updated, _ = movement_actions_for(movement.type)
                audit_target = child if child is not None else movement

                # Знімки ДО будь-яких мутацій: інакше diff порівнює об'єкти самі
                # з собою (identity map — той самий Python-об'єкт у сесії).
                old_unit_ids = MovementDao.get_unit_ids(session, movement.id)
                old_units = list(ProductDao.get_by_ids(session, old_unit_ids))
                old_snapshot = Updated.snapshot(movement_view(audit_target))
                old_positions = snapshot_position_lines(movement.products_catalog)
                old_unit_rows = snapshot_unit_rows(old_units)
                # Кандидати на злиття треба відібрати ДО clear_positions: після
                # неї зв'язок осколка з цим рухом уже видалено, і ознака
                # «породжений саме цим рухом» не обчислюється.
                own_split_ids = self._own_split_children(session, movement, old_units)

                movement_posting.revert(session, movement, old_unit_ids)

                for name, value in payload.header.items():
                    setattr(movement, name, value)
                if child is not None:
                    for name, value in payload.child.items():
                        setattr(child, name, value)
                session.add(movement)
                session.flush()

                units = self._resolve_unit_plan(session, payload.unit_plan)
                movement_posting.validate_source(session, movement, units)

                MovementDao.clear_positions(session, movement.id)
                movement.total_cost = MovementDao.rebuild_positions(
                    session,
                    movement,
                    units,
                    payload.prices,
                    catalog_meta=self._catalog_meta(session, units),
                )

                self._merge_orphan_split_children(session, own_split_ids, old_units, units)
                ProductDao.set_serial_numbers(session, payload.serials)
                movement_posting.apply(session, movement, units)

                session.refresh(movement)
                position_lines = diff_position_lines(
                    old_positions,
                    movement.products_catalog,
                    session,
                    key=lambda line: line.id_product_catalog,
                    title=movement_position_title,
                    label=movement_position_label,
                )
                unit_lines = diff_unit_lines(old_unit_rows, snapshot_unit_rows(units), session)
                record_action(
                    session,
                    actor_login,
                    movement.id,
                    Updated.from_diff(
                        old_snapshot,
                        movement_view(child if child is not None else movement),
                        session,
                        reason=reason,
                        lines=position_lines + unit_lines,
                    ),
                )
                session.commit()
                return movement.id

        except ServiceError:
            raise
        except Exception as e:
            print(f"[MovementEditService][save_full][ERROR] {e}")
            raise ServiceError("Системна помилка при збереженні руху!")

    def _resolve_unit_plan(
        self, session: Session, unit_plan: List[Tuple[int, Optional[float]]]
    ) -> List[Product]:
        """Перетворює план складу на конкретні одиниці. Поділ подільної одиниці
        виконується тут, у межах транзакції: при помилці далі осколок відкотиться
        разом з усім іншим (на відміну від `resolve_movement_products`, який
        ділить одразу з власним commit)."""
        units: List[Product] = []
        for unit_id, amount in unit_plan:
            if amount is None:
                unit = session.get(Product, unit_id)
                if unit is None:
                    raise ServiceError(f"Одиницю №{unit_id} не знайдено!")
                units.append(unit)
                continue
            try:
                units.append(ProductDao.split(session, unit_id, amount))
            except ValueError as e:
                raise ServiceError(str(e))
        session.flush()
        return units

    def _catalog_meta(self, session: Session, units: Sequence[Product]) -> Dict[int, Tuple[bool, int]]:
        """id каталогу -> (подільний, ємність) — для пропорційної вартості
        частини подільної одиниці в продажу (`declared.sale_line_cost`)."""
        catalog_ids = {unit.id_product_catalog for unit in units}
        if not catalog_ids:
            return {}
        rows = session.exec(select(ProductCatalog).where(ProductCatalog.id.in_(catalog_ids))).all()
        return {row.id: (row.divisible, row.capacity) for row in rows}

    def _own_split_children(
        self, session: Session, movement: Movement, old_units: Sequence[Product]
    ) -> set:
        """id осколків, породжених саме цим рухом. Ознака — найменший рух одиниці
        дорівнює поточному: гвард уже виключив пізніші рухи, тож це рівносильно
        «одиниця більше ніде не фігурує». Обчислювати ДО `clear_positions`."""
        return {
            unit.id
            for unit in old_units
            if unit.id_parent is not None
            and MovementDao.first_movement_id_for_unit(session, unit.id) == movement.id
        }

    def _merge_orphan_split_children(
        self,
        session: Session,
        own_split_ids: set,
        old_units: Sequence[Product],
        units: Sequence[Product],
    ) -> None:
        """Осколок, який породив саме цей рух і який прибрали зі складу, зливаємо
        назад у батька — інакше редагування плодить сміттєві одиниці в залишках."""
        kept_ids = {unit.id for unit in units}
        for unit in old_units:
            if unit.id in kept_ids or unit.id not in own_split_ids:
                continue
            ProductDao.merge_child_into_parent(session, unit)
        session.flush()
