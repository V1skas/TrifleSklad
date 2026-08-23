"""Гвард доступності повного редагування руху і транзакційне збереження."""

import pytest
from sqlmodel import select

from TrifleSklad.audit import get_audit_history, parse_changes
from TrifleSklad.declared import MovementsStatus, MovementsType
from TrifleSklad.models import Movement, Product, Sale
from TrifleSklad.services.errors import ServiceError
from TrifleSklad.services.movement_edit import FullEditPayload, MovementEditService
from tests.conftest import grant, make_movement, make_unit

WRITE_OFF_FULL = "write_offs:edit_full"
TRANSFER_FULL = "movements:edit_full"
SALE_FULL = "sales:edit_full"


@pytest.fixture
def write_off(session, catalog, places):
    """Списання однієї подільної одиниці зі складу — базовий сценарій."""
    cable, _ = catalog
    warehouse, _, _, owner, _ = places
    unit = make_unit(session, cable, warehouse, owner, count=100)
    make_movement(
        session,
        MovementsType.ADMISSION,
        [unit],
        destination_storage=warehouse,
        destination_owner=owner,
    )
    movement = make_movement(
        session,
        MovementsType.WRITE_OFF,
        [unit],
        incoming_storage=warehouse,
        incoming_owner=owner,
        date="2026-07-27",
    )
    unit.is_deleted = True
    session.add(unit)
    session.commit()
    return movement, unit


def payload_for(movement, reason="помилка оператора", **kwargs):
    return FullEditPayload(
        movement_id=movement.id,
        movement_type=movement.type,
        reason=reason,
        **kwargs,
    )


# --- гвард -----------------------------------------------------------------


def test_editability_allows_clean_movement(session, rx_session, write_off):
    movement, _ = write_off
    grant(session, "admin", WRITE_OFF_FULL)

    verdict = MovementEditService().editability(movement.id, movement.type, "admin")

    assert verdict.allowed is True


def test_editability_rejects_missing_movement(session, rx_session):
    verdict = MovementEditService().editability(999, MovementsType.WRITE_OFF, "admin")

    assert (verdict.allowed, verdict.reason_code) == (False, "not_found")


def test_editability_rejects_wrong_type(session, rx_session, write_off):
    movement, _ = write_off
    grant(session, "admin", WRITE_OFF_FULL, TRANSFER_FULL)

    verdict = MovementEditService().editability(movement.id, MovementsType.MOVEMENT, "admin")

    assert (verdict.allowed, verdict.reason_code) == (False, "wrong_type")


def test_editability_rejects_canceled_movement(session, rx_session, write_off):
    movement, _ = write_off
    grant(session, "admin", WRITE_OFF_FULL)
    movement.status = MovementsStatus.CANCELED
    session.add(movement)
    session.commit()

    verdict = MovementEditService().editability(movement.id, movement.type, "admin")

    assert (verdict.allowed, verdict.reason_code) == (False, "canceled")


def test_editability_rejects_without_permission(session, rx_session, write_off):
    movement, _ = write_off

    verdict = MovementEditService().editability(movement.id, movement.type, "admin")

    assert (verdict.allowed, verdict.reason_code) == (False, "no_permission")


def test_editability_rejects_expired_window(session, rx_session, write_off):
    movement, _ = write_off
    grant(session, "admin", WRITE_OFF_FULL)
    movement.date = "2020-01-01"
    session.add(movement)
    session.commit()

    verdict = MovementEditService().editability(movement.id, movement.type, "admin")

    assert (verdict.allowed, verdict.reason_code) == (False, "window_expired")


def test_editability_rejects_bad_date(session, rx_session, write_off):
    movement, _ = write_off
    grant(session, "admin", WRITE_OFF_FULL)
    movement.date = "не дата"
    session.add(movement)
    session.commit()

    verdict = MovementEditService().editability(movement.id, movement.type, "admin")

    assert (verdict.allowed, verdict.reason_code) == (False, "bad_date")


def test_editability_reports_later_movements_as_conflicts(session, rx_session, catalog, places):
    """Одиниця бере участь у пізнішому русі — редагування раннього заблоковане."""
    _, device = catalog
    warehouse, warehouse2, _, owner, owner2 = places
    unit = make_unit(session, device, warehouse, owner, serial="СН-001")
    grant(session, "admin", TRANSFER_FULL)
    first = make_movement(
        session,
        MovementsType.MOVEMENT,
        [unit],
        incoming_storage=warehouse,
        incoming_owner=owner,
        destination_storage=warehouse2,
        destination_owner=owner2,
        date="2026-07-25",
    )
    later = make_movement(
        session,
        MovementsType.MOVEMENT,
        [unit],
        incoming_storage=warehouse2,
        incoming_owner=owner2,
        destination_storage=warehouse,
        destination_owner=owner,
        date="2026-07-26",
    )

    verdict = MovementEditService().editability(first.id, first.type, "admin")

    assert (verdict.allowed, verdict.reason_code) == (False, "conflicts")
    assert [m.id for m in verdict.conflicts] == [later.id]

    # Пізніший рух конфліктів не має — його редагувати можна.
    assert MovementEditService().editability(later.id, later.type, "admin").allowed is True


def test_editability_ignores_canceled_later_movement(session, rx_session, catalog, places):
    """TS-56: скасований пізніший рух не блокує редагування раннього — відкат
    бере джерело з шапки руху, а не реконструює його ланцюжком (TS-48-fix)."""
    _, device = catalog
    warehouse, warehouse2, _, owner, owner2 = places
    unit = make_unit(session, device, warehouse, owner, serial="СН-002")
    grant(session, "admin", TRANSFER_FULL)
    first = make_movement(
        session,
        MovementsType.MOVEMENT,
        [unit],
        incoming_storage=warehouse,
        incoming_owner=owner,
        destination_storage=warehouse2,
        destination_owner=owner2,
        date="2026-07-25",
    )
    later = make_movement(
        session,
        MovementsType.MOVEMENT,
        [unit],
        incoming_storage=warehouse2,
        incoming_owner=owner2,
        destination_storage=warehouse,
        destination_owner=owner,
        date="2026-07-26",
        status=MovementsStatus.CANCELED,
    )

    verdict = MovementEditService().editability(first.id, first.type, "admin")

    assert verdict.allowed is True
    assert later.id not in [m.id for m in verdict.conflicts]
    assert verdict.conflicts == []


# --- збереження ------------------------------------------------------------


def test_save_allows_blank_reason(session, rx_session, write_off):
    """TS-56: причина коригування необов'язкова — порожнє значення не блокує збереження."""
    movement, unit = write_off
    grant(session, "admin", WRITE_OFF_FULL)

    MovementEditService().save_full(
        payload_for(movement, reason="   ", unit_plan=[(unit.id, None)]), "admin"
    )


def test_save_rejects_unit_from_another_source_and_keeps_stock_intact(
    session, rx_session, write_off, catalog, places
):
    """Помилка валідації відкочує ВСЕ, включно з уже виконаним revert."""
    movement, unit = write_off
    cable, _ = catalog
    _, warehouse2, _, owner, _ = places
    foreign = make_unit(session, cable, warehouse2, owner, count=50)
    grant(session, "admin", WRITE_OFF_FULL)

    with pytest.raises(ServiceError, match=f"№{foreign.id}"):
        MovementEditService().save_full(
            payload_for(movement, unit_plan=[(unit.id, None), (foreign.id, None)]), "admin"
        )

    session.expire_all()
    # Списана одиниця лишилась списаною — revert не «просочився» назовні.
    assert session.get(Product, unit.id).is_deleted is True


def test_save_removes_unit_from_movement_and_restores_stock(session, rx_session, write_off):
    movement, unit = write_off
    grant(session, "admin", WRITE_OFF_FULL)

    MovementEditService().save_full(payload_for(movement, unit_plan=[]), "admin")

    session.expire_all()
    # Одиницю прибрали зі списання — вона знову на складі.
    assert session.get(Product, unit.id).is_deleted is False


def test_save_adds_unit_to_movement(session, rx_session, write_off, catalog, places):
    movement, unit = write_off
    cable, _ = catalog
    warehouse, _, _, owner, _ = places
    extra = make_unit(session, cable, warehouse, owner, count=40)
    grant(session, "admin", WRITE_OFF_FULL)

    MovementEditService().save_full(
        payload_for(movement, unit_plan=[(unit.id, None), (extra.id, None)]), "admin"
    )

    session.expire_all()
    assert session.get(Product, extra.id).is_deleted is True
    assert session.get(Product, unit.id).is_deleted is True


def test_save_changes_destination_and_relocates_units(session, rx_session, catalog, places):
    _, device = catalog
    warehouse, warehouse2, _, owner, owner2 = places
    unit = make_unit(session, device, warehouse, owner, serial="СН-010")
    grant(session, "admin", TRANSFER_FULL)
    make_movement(
        session,
        MovementsType.ADMISSION,
        [unit],
        destination_storage=warehouse,
        destination_owner=owner,
    )
    transfer = make_movement(
        session,
        MovementsType.MOVEMENT,
        [unit],
        incoming_storage=warehouse,
        incoming_owner=owner,
        destination_storage=warehouse2,
        destination_owner=owner,
        date="2026-07-27",
    )
    unit.id_storage = warehouse2.id
    session.add(unit)
    session.commit()

    MovementEditService().save_full(
        payload_for(
            transfer,
            header={"id_destination_owner": owner2.id, "id_destination_storage": warehouse2.id},
            unit_plan=[(unit.id, None)],
        ),
        "admin",
    )

    session.expire_all()
    moved = session.get(Product, unit.id)
    assert (moved.id_storage, moved.id_owner) == (warehouse2.id, owner2.id)


def test_save_splits_divisible_unit_inside_transaction(session, rx_session, write_off):
    """Часткове списання: у рух іде осколок, батько лишається на складі."""
    movement, unit = write_off
    grant(session, "admin", WRITE_OFF_FULL)

    MovementEditService().save_full(payload_for(movement, unit_plan=[(unit.id, 30)]), "admin")

    session.expire_all()
    parent = session.get(Product, unit.id)
    child = session.exec(select(Product).where(Product.id_parent == unit.id)).one()
    assert parent.count == 70 and parent.is_deleted is False
    assert child.count == 30 and child.is_deleted is True


def test_split_is_rolled_back_when_validation_fails(session, rx_session, write_off, catalog, places):
    movement, unit = write_off
    cable, _ = catalog
    _, warehouse2, _, owner, _ = places
    foreign = make_unit(session, cable, warehouse2, owner, count=50)
    grant(session, "admin", WRITE_OFF_FULL)

    with pytest.raises(ServiceError):
        MovementEditService().save_full(
            payload_for(movement, unit_plan=[(unit.id, 30), (foreign.id, None)]), "admin"
        )

    session.expire_all()
    # Жодного осколка в БД і залишок батька не зачеплено.
    assert session.exec(select(Product).where(Product.id_parent == unit.id)).all() == []
    assert session.get(Product, unit.id).count == 100


def test_save_merges_orphan_split_child_back_into_parent(session, rx_session, write_off):
    movement, unit = write_off
    grant(session, "admin", WRITE_OFF_FULL)
    MovementEditService().save_full(payload_for(movement, unit_plan=[(unit.id, 30)]), "admin")
    session.expire_all()
    child_id = session.exec(select(Product).where(Product.id_parent == unit.id)).one().id

    # Прибираємо осколок зі складу руху — він має злитись назад у батька.
    MovementEditService().save_full(payload_for(movement, unit_plan=[]), "admin")

    session.expire_all()
    assert session.get(Product, child_id) is None
    assert session.get(Product, unit.id).count == 100


def test_save_recomputes_total_cost_for_sale_with_partial_unit(session, rx_session, catalog, places):
    """Частина подільної одиниці оплачується пропорційно ємності."""
    cable, _ = catalog
    warehouse, _, _, owner, _ = places
    unit = make_unit(session, cable, warehouse, owner, count=100)
    grant(session, "admin", SALE_FULL)
    sale = make_movement(
        session,
        MovementsType.SALE,
        [],
        incoming_storage=warehouse,
        incoming_owner=owner,
        date="2026-07-27",
    )
    session.add(Sale(id=sale.id, id_responsible=1, client_info=""))
    session.commit()

    MovementEditService().save_full(
        payload_for(sale, unit_plan=[(unit.id, 25)], prices={cable.id: 400.0}), "admin"
    )

    session.expire_all()
    # 25 м зі 100 м за ціною 400 за цілу бухту -> 100.
    assert session.get(Movement, sale.id).total_cost == 100.0


# --- аудит -----------------------------------------------------------------


def test_audit_records_reason_and_unit_lines(session, rx_session, write_off, catalog, places):
    movement, unit = write_off
    cable, _ = catalog
    warehouse, _, _, owner, _ = places
    extra = make_unit(session, cable, warehouse, owner, count=40)
    grant(session, "admin", WRITE_OFF_FULL)

    MovementEditService().save_full(
        payload_for(
            movement, reason="накладна прийшла з іншим переліком", unit_plan=[(extra.id, None)]
        ),
        "admin",
    )

    session.expire_all()
    logs = get_audit_history(session, "write_offs", movement.id)
    assert len(logs) == 1
    action = parse_changes(logs[0])
    assert action.reason == "накладна прийшла з іншим переліком"
    titles = [line.title for line in action.lines]
    assert any(f"Одиниця №{extra.id}" in title for title in titles)
    assert any(f"Одиниця №{unit.id}" in title for title in titles)


def test_audit_aggregates_unit_lines_above_limit(session, rx_session, catalog, places):
    from TrifleSklad.audit.labels import UNIT_LINES_LIMIT, diff_unit_lines, snapshot_unit_rows

    cable, _ = catalog
    warehouse, _, _, owner, _ = places
    units = [make_unit(session, cable, warehouse, owner, count=1) for _ in range(UNIT_LINES_LIMIT + 1)]

    lines = diff_unit_lines([], snapshot_unit_rows(units), session)

    assert len(lines) == 1
    assert lines[0].kind == "added"
    assert lines[0].new == f"{UNIT_LINES_LIMIT + 1} шт."


# --- покриття за типами ТМЦ (подільний / унікальний / витратний) ------------

ISSUE_FULL = "issues:edit_full"


def _plain_consumable(session):
    """Неподільний неунікальний ТМЦ без серійного номера (напр. лампа)."""
    from TrifleSklad import models

    cat = models.ProductCatalog(
        title="Лампа", unit="шт", divisible=False, uniq=False, capacity=0, count=0
    )
    session.add(cat)
    session.commit()
    return cat


def test_edit_transfer_preserves_count_owner_and_serial_for_each_type(
    session, rx_session, catalog, places
):
    """Переміщення веде і подільний (зберігає count), і унікальний (зберігає s/n)
    ТМЦ на нове призначення. Правка проходить через revert проведеного стану."""
    from TrifleSklad.services import movement_posting

    cable, device = catalog
    warehouse, warehouse2, _, owner, owner2 = places
    divisible = make_unit(session, cable, warehouse, owner, count=100)
    serial = make_unit(session, device, warehouse, owner, serial="СН-100")
    grant(session, "admin", TRANSFER_FULL)
    transfer = make_movement(
        session,
        MovementsType.MOVEMENT,
        [divisible, serial],
        incoming_storage=warehouse,
        incoming_owner=owner,
        destination_storage=warehouse2,
        destination_owner=owner,
        date="2026-07-27",
    )
    # Проводимо рух: одиниці на призначенні (як у реальному житті перед правкою).
    movement_posting.apply(session, transfer, [divisible, serial])
    session.commit()

    MovementEditService().save_full(
        payload_for(
            transfer,
            header={
                "id_incoming_storage": warehouse.id,
                "id_incoming_owner": owner.id,
                "id_destination_storage": warehouse2.id,
                "id_destination_owner": owner2.id,
            },
            unit_plan=[(divisible.id, None), (serial.id, None)],
            serials={serial.id: "СН-100"},
        ),
        "admin",
    )

    session.expire_all()
    d = session.get(Product, divisible.id)
    s = session.get(Product, serial.id)
    assert (d.id_storage, d.id_owner, d.count, d.is_deleted) == (warehouse2.id, owner2.id, 100, False)
    assert (s.id_storage, s.id_owner, s.serial_number, s.is_deleted) == (
        warehouse2.id,
        owner2.id,
        "СН-100",
        False,
    )


def test_edit_issue_writes_off_consumables_and_moves_unique(session, rx_session, catalog, places):
    """Видача: витратний (подільний і простий неунікальний) списується на місці,
    унікальний (серійний) переїжджає на площадку. Правка зберігає цю різницю."""
    from TrifleSklad.services import movement_posting

    cable, device = catalog
    lamp = _plain_consumable(session)
    warehouse, _, site, owner, owner2 = places
    divisible = make_unit(session, cable, warehouse, owner, count=100)
    plain = make_unit(session, lamp, warehouse, owner)
    serial = make_unit(session, device, warehouse, owner, serial="СН-5")
    grant(session, "admin", ISSUE_FULL)
    issue = make_movement(
        session,
        MovementsType.ISSUE,
        [divisible, plain, serial],
        incoming_storage=warehouse,
        incoming_owner=owner,
        destination_storage=site,
        destination_owner=owner2,
        date="2026-07-27",
    )
    from TrifleSklad.models import Issue

    session.add(Issue(id=issue.id, id_recipient=1))
    session.commit()
    movement_posting.apply(session, issue, [divisible, plain, serial])
    session.commit()

    # Правка шапки (отримувач) без зміни складу — round-trip revert+apply.
    MovementEditService().save_full(
        payload_for(
            issue,
            header={
                "id_incoming_storage": warehouse.id,
                "id_incoming_owner": owner.id,
                "id_destination_storage": site.id,
                "id_destination_owner": owner2.id,
            },
            child={"id_recipient": 1},
            unit_plan=[(divisible.id, None), (plain.id, None), (serial.id, None)],
            serials={serial.id: "СН-5"},
        ),
        "admin",
    )

    session.expire_all()
    d = session.get(Product, divisible.id)
    p = session.get(Product, plain.id)
    s = session.get(Product, serial.id)
    # Витратні списані на місці (джерело), унікальний переміщений на площадку.
    assert d.is_deleted is True and (d.id_storage, d.id_owner) == (warehouse.id, owner.id)
    assert p.is_deleted is True and (p.id_storage, p.id_owner) == (warehouse.id, owner.id)
    assert s.is_deleted is False and (s.id_storage, s.id_owner) == (site.id, owner2.id)
    assert s.serial_number == "СН-5"


def test_edit_split_divisible_moves_part_and_keeps_remainder(session, rx_session, catalog, places):
    """Правка переміщення: подільну одиницю поділили — частина їде, залишок
    лишається в джерелі. count розподіляється точно."""
    from TrifleSklad.services import movement_posting

    cable, _ = catalog
    warehouse, warehouse2, _, owner, _ = places
    divisible = make_unit(session, cable, warehouse, owner, count=100)
    grant(session, "admin", TRANSFER_FULL)
    transfer = make_movement(
        session,
        MovementsType.MOVEMENT,
        [divisible],
        incoming_storage=warehouse,
        incoming_owner=owner,
        destination_storage=warehouse2,
        destination_owner=owner,
        date="2026-07-27",
    )
    movement_posting.apply(session, transfer, [divisible])
    session.commit()

    MovementEditService().save_full(
        payload_for(
            transfer,
            header={
                "id_incoming_storage": warehouse.id,
                "id_incoming_owner": owner.id,
                "id_destination_storage": warehouse2.id,
                "id_destination_owner": owner.id,
            },
            unit_plan=[(divisible.id, 30.0)],
        ),
        "admin",
    )

    session.expire_all()
    parent = session.get(Product, divisible.id)
    child = session.exec(select(Product).where(Product.id_parent == divisible.id)).one()
    # Залишок 70 — у джерелі; відділені 30 — на призначенні.
    assert (parent.id_storage, parent.count) == (warehouse.id, 70)
    assert (child.id_storage, child.count) == (warehouse2.id, 30)


def test_edit_updates_serial_number(session, rx_session, catalog, places):
    """Правка може змінити серійний номер унікальної одиниці."""
    from TrifleSklad.services import movement_posting

    _, device = catalog
    warehouse, warehouse2, _, owner, _ = places
    serial = make_unit(session, device, warehouse, owner, serial="СН-OLD")
    grant(session, "admin", TRANSFER_FULL)
    transfer = make_movement(
        session,
        MovementsType.MOVEMENT,
        [serial],
        incoming_storage=warehouse,
        incoming_owner=owner,
        destination_storage=warehouse2,
        destination_owner=owner,
        date="2026-07-27",
    )
    movement_posting.apply(session, transfer, [serial])
    session.commit()

    MovementEditService().save_full(
        payload_for(
            transfer,
            header={
                "id_incoming_storage": warehouse.id,
                "id_incoming_owner": owner.id,
                "id_destination_storage": warehouse2.id,
                "id_destination_owner": owner.id,
            },
            unit_plan=[(serial.id, None)],
            serials={serial.id: "СН-NEW"},
        ),
        "admin",
    )

    session.expire_all()
    assert session.get(Product, serial.id).serial_number == "СН-NEW"


def test_edit_transfer_moves_no_fixed_capacity_divisible_with_fractional_count(
    session, rx_session, places
):
    """Подільний ТМЦ БЕЗ фіксованої ємності (capacity=0, дробовий count):
    переміщення веде його на призначення, зберігаючи дробовий залишок."""
    from TrifleSklad import models
    from TrifleSklad.services import movement_posting

    cat = models.ProductCatalog(
        title="Кабель наливний", unit="м", divisible=True, uniq=False,
        capacity=0, no_fixed_capacity=True, count=0,
    )
    session.add(cat)
    session.commit()
    warehouse, warehouse2, _, owner, owner2 = places
    unit = make_unit(session, cat, warehouse, owner, count=0.75)
    grant(session, "admin", TRANSFER_FULL)
    transfer = make_movement(
        session,
        MovementsType.MOVEMENT,
        [unit],
        incoming_storage=warehouse,
        incoming_owner=owner,
        destination_storage=warehouse2,
        destination_owner=owner,
        date="2026-07-27",
    )
    movement_posting.apply(session, transfer, [unit])
    session.commit()

    MovementEditService().save_full(
        payload_for(
            transfer,
            header={
                "id_incoming_storage": warehouse.id,
                "id_incoming_owner": owner.id,
                "id_destination_storage": warehouse2.id,
                "id_destination_owner": owner2.id,
            },
            unit_plan=[(unit.id, None)],
        ),
        "admin",
    )

    session.expire_all()
    u = session.get(Product, unit.id)
    assert (u.id_storage, u.id_owner, u.count, u.is_deleted) == (warehouse2.id, owner2.id, 0.75, False)
