from TrifleSklad.dao_legacy import ProductDAO
from TrifleSklad.declared import MovementsType
from TrifleSklad.models import Product
from tests.conftest import make_movement, make_unit


def test_set_excluded_flags(rx_session, session, catalog, places):
    cable, device = catalog
    warehouse, warehouse2, site, owner, owner2 = places
    unit1 = make_unit(session, device, warehouse, owner)
    unit2 = make_unit(session, device, warehouse, owner)

    flag, _ = ProductDAO.set_excluded_flags({unit1.id: True, unit2.id: False})
    assert flag

    session.expire_all()
    assert session.get(Product, unit1.id).excluded_from_accounting is True
    assert session.get(Product, unit2.id).excluded_from_accounting is False


def test_set_excluded_flags_empty_mapping_is_noop(rx_session):
    flag, _ = ProductDAO.set_excluded_flags({})
    assert flag


def test_apply_excluded_flags_for_movement_inherits_split_child(rx_session, session, catalog, places):
    cable, device = catalog
    warehouse, warehouse2, site, owner, owner2 = places
    # Батько лишається поза рухом — його частину відділили при поверненні.
    parent = make_unit(session, cable, warehouse, owner, count=10)
    child = make_unit(session, cable, warehouse, owner, count=3, parent_id=parent.id)
    movement = make_movement(
        session,
        MovementsType.RETURN,
        [child],
        incoming_storage=site,
        destination_storage=warehouse,
    )

    # excluded_by_id знає лише про БАТЬКА (той, кого користувач бачив у
    # віджеті до поділу) — осколок має успадкувати його позначку.
    flag, _ = ProductDAO.apply_excluded_flags_for_movement(movement.id, {parent.id: True})
    assert flag

    session.expire_all()
    assert session.get(Product, child.id).excluded_from_accounting is True
    # Батько не входить у рух — його власна позначка не займана.
    assert session.get(Product, parent.id).excluded_from_accounting is False


def test_apply_excluded_flags_for_movement_direct_id(rx_session, session, catalog, places):
    cable, device = catalog
    warehouse, warehouse2, site, owner, owner2 = places
    unit = make_unit(session, device, warehouse, owner)
    movement = make_movement(
        session,
        MovementsType.RETURN,
        [unit],
        incoming_storage=site,
        destination_storage=warehouse,
    )

    flag, _ = ProductDAO.apply_excluded_flags_for_movement(movement.id, {unit.id: True})
    assert flag

    session.expire_all()
    assert session.get(Product, unit.id).excluded_from_accounting is True
