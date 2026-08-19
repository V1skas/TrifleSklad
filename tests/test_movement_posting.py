"""Перевірка таблиці ефектів руху: apply -> revert повертає залишки у вихідний
стан для кожного з 8 типів (стан одиниці = is_deleted + id_storage + id_owner)."""

import pytest

from TrifleSklad.declared import MovementsType
from TrifleSklad.models import SaleReturn
from TrifleSklad.services import movement_posting
from TrifleSklad.services.errors import ServiceError
from tests.conftest import make_movement, make_unit


def state_of(unit):
    return (unit.is_deleted, unit.id_storage, unit.id_owner)


def test_write_off_apply_then_revert_restores_unit(session, catalog, places):
    cable, _ = catalog
    warehouse, _, _, owner, _ = places
    unit = make_unit(session, cable, warehouse, owner, count=100)
    before = state_of(unit)
    movement = make_movement(
        session, MovementsType.WRITE_OFF, [unit], incoming_storage=warehouse, incoming_owner=owner
    )

    movement_posting.apply(session, movement, [unit])
    assert unit.is_deleted is True

    movement_posting.revert(session, movement, [unit.id])
    assert state_of(unit) == before


def test_transfer_apply_moves_unit_and_revert_returns_to_source(session, catalog, places):
    """Відкат переміщення повертає одиницю в джерело самого руху (incoming),
    а не реконструює його ланцюжком попередніх рухів."""
    cable, _ = catalog
    warehouse, warehouse2, _, owner, owner2 = places
    unit = make_unit(session, cable, warehouse, owner, count=100)
    transfer = make_movement(
        session,
        MovementsType.MOVEMENT,
        [unit],
        incoming_storage=warehouse,
        incoming_owner=owner,
        destination_storage=warehouse2,
        destination_owner=owner2,
    )

    movement_posting.apply(session, transfer, [unit])
    assert (unit.id_storage, unit.id_owner) == (warehouse2.id, owner2.id)

    movement_posting.revert(session, transfer, [unit.id])
    assert (unit.id_storage, unit.id_owner) == (warehouse.id, owner.id)


def test_revert_uses_header_not_current_unit_owner(session, catalog, places):
    """Ключовий сценарій фіксу: одиниця «поплила» власником (дані порушують
    інваріант «власник = той, що в шапці»). Відкат усе одно повертає її в
    джерело руху за шапкою, а не намагається відновити чужого власника."""
    cable, _ = catalog
    warehouse, warehouse2, _, owner, owner2 = places
    # Рух заявляє джерело (warehouse, owner), але одиниця фактично лежить в
    # (warehouse2, owner2) — так виглядає розсинхронізована seed-база.
    unit = make_unit(session, cable, warehouse2, owner2, count=100)
    transfer = make_movement(
        session,
        MovementsType.MOVEMENT,
        [unit],
        incoming_storage=warehouse,
        incoming_owner=owner,
        destination_storage=warehouse2,
        destination_owner=owner2,
    )

    movement_posting.revert(session, transfer, [unit.id])

    # Одиниця «підтягнута» до джерела руху — далі validate_source пройде.
    assert (unit.id_storage, unit.id_owner) == (warehouse.id, owner.id)
    movement_posting.validate_source(session, transfer, [unit])


def test_issue_writes_off_consumables_and_moves_uniq(session, catalog, places):
    cable, device = catalog
    warehouse, _, site, owner, owner2 = places
    consumable = make_unit(session, cable, warehouse, owner, count=100)
    serial_unit = make_unit(session, device, warehouse, owner, serial="СН-001")
    issue = make_movement(
        session,
        MovementsType.ISSUE,
        [consumable, serial_unit],
        incoming_storage=warehouse,
        incoming_owner=owner,
        destination_storage=site,
        destination_owner=owner2,
    )

    movement_posting.apply(session, issue, [consumable, serial_unit])

    # Витратний ТМЦ списується на місці, унікальний — переїжджає на площадку.
    assert consumable.is_deleted is True
    assert (consumable.id_storage, consumable.id_owner) == (warehouse.id, owner.id)
    assert serial_unit.is_deleted is False
    assert (serial_unit.id_storage, serial_unit.id_owner) == (site.id, owner2.id)


def test_issue_revert_restores_both_kinds(session, catalog, places):
    cable, device = catalog
    warehouse, _, site, owner, owner2 = places
    consumable = make_unit(session, cable, warehouse, owner, count=100)
    serial_unit = make_unit(session, device, warehouse, owner, serial="СН-001")
    make_movement(
        session,
        MovementsType.ADMISSION,
        [consumable, serial_unit],
        destination_storage=warehouse,
        destination_owner=owner,
    )
    issue = make_movement(
        session,
        MovementsType.ISSUE,
        [consumable, serial_unit],
        incoming_storage=warehouse,
        incoming_owner=owner,
        destination_storage=site,
        destination_owner=owner2,
    )
    before = (state_of(consumable), state_of(serial_unit))

    movement_posting.apply(session, issue, [consumable, serial_unit])
    movement_posting.revert(session, issue, [consumable.id, serial_unit.id])

    assert (state_of(consumable), state_of(serial_unit)) == before


def test_sale_apply_marks_sold_and_revert_restores(session, catalog, places):
    _, device = catalog
    warehouse, _, _, owner, _ = places
    unit = make_unit(session, device, warehouse, owner, serial="СН-002")
    before = state_of(unit)
    sale = make_movement(
        session, MovementsType.SALE, [unit], incoming_storage=warehouse, incoming_owner=owner, price=500.0
    )

    movement_posting.apply(session, sale, [unit])
    assert unit.is_deleted is True

    movement_posting.revert(session, sale, [unit.id])
    assert state_of(unit) == before


def test_return_changes_storage_but_keeps_owner(session, catalog, places):
    _, device = catalog
    warehouse, _, site, owner, _ = places
    unit = make_unit(session, device, site, owner, serial="СН-003")
    returning = make_movement(
        session,
        MovementsType.RETURN,
        [unit],
        incoming_storage=site,
        destination_storage=warehouse,
    )

    movement_posting.apply(session, returning, [unit])

    assert unit.id_storage == warehouse.id
    assert unit.id_owner == owner.id


def test_sale_return_restores_sold_unit_and_revert_sells_it_back(session, catalog, places):
    _, device = catalog
    warehouse, _, _, owner, _ = places
    unit = make_unit(session, device, warehouse, owner, serial="СН-004", is_deleted=True)
    sale_return = make_movement(
        session,
        MovementsType.SALE_RETURN,
        [unit],
        destination_storage=warehouse,
        destination_owner=owner,
        price=300.0,
    )

    movement_posting.apply(session, sale_return, [unit])
    assert unit.is_deleted is False
    assert unit.id_storage == warehouse.id

    movement_posting.revert(session, sale_return, [unit.id])
    assert unit.is_deleted is True


def test_client_issue_behaves_like_issue(session, catalog, places):
    cable, _ = catalog
    warehouse, _, site, owner, owner2 = places
    consumable = make_unit(session, cable, warehouse, owner, count=100)
    client_issue = make_movement(
        session,
        MovementsType.CLIENT_ISSUE,
        [consumable],
        incoming_storage=warehouse,
        incoming_owner=owner,
        destination_storage=site,
        destination_owner=owner2,
    )

    movement_posting.apply(session, client_issue, [consumable])

    assert consumable.is_deleted is True


def test_admission_apply_places_units_at_destination(session, catalog, places):
    cable, _ = catalog
    warehouse, _, _, owner, _ = places
    unit = make_unit(session, cable, warehouse, owner, count=100)
    admission = make_movement(
        session,
        MovementsType.ADMISSION,
        [unit],
        destination_storage=warehouse,
        destination_owner=owner,
    )

    movement_posting.apply(session, admission, [unit])

    assert (unit.id_storage, unit.id_owner) == (warehouse.id, owner.id)


def test_validate_source_rejects_unit_from_another_storage(session, catalog, places):
    cable, _ = catalog
    warehouse, warehouse2, _, owner, _ = places
    foreign = make_unit(session, cable, warehouse2, owner, count=100)
    movement = make_movement(
        session, MovementsType.WRITE_OFF, [], incoming_storage=warehouse, incoming_owner=owner
    )

    with pytest.raises(ServiceError) as excinfo:
        movement_posting.validate_source(session, movement, [foreign])

    assert f"№{foreign.id}" in str(excinfo.value)


def test_validate_source_ignores_owner_for_return(session, catalog, places):
    """Повернення не задає власника — перевіряється лише склад."""
    _, device = catalog
    warehouse, _, site, owner, owner2 = places
    unit = make_unit(session, device, site, owner2, serial="СН-005")
    returning = make_movement(
        session,
        MovementsType.RETURN,
        [unit],
        incoming_storage=site,
        incoming_owner=owner,
        destination_storage=warehouse,
    )

    movement_posting.validate_source(session, returning, [unit])


def test_validate_source_for_sale_return_requires_unit_from_that_sale(session, catalog, places):
    _, device = catalog
    warehouse, _, _, owner, _ = places
    sold = make_unit(session, device, warehouse, owner, serial="СН-006", is_deleted=True)
    stranger = make_unit(session, device, warehouse, owner, serial="СН-007", is_deleted=True)
    sale = make_movement(
        session, MovementsType.SALE, [sold], incoming_storage=warehouse, incoming_owner=owner
    )
    sale_return = make_movement(
        session, MovementsType.SALE_RETURN, [sold], destination_storage=warehouse, destination_owner=owner
    )
    session.add(SaleReturn(id=sale_return.id, id_sale=sale.id))
    session.commit()

    movement_posting.validate_source(session, sale_return, [sold])

    with pytest.raises(ServiceError):
        movement_posting.validate_source(session, sale_return, [stranger])
