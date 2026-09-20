"""TS-57 раунд 3: вартість одиниці при постачанні + приховування вичерпаних
позицій каталогу у діалозі вибору (exclude_ids)."""

from TrifleSklad.dao_legacy import ProductDAO
from TrifleSklad.declared import MovementsType
from tests.conftest import make_movement, make_unit


def test_acquisition_cost_from_admission_price(rx_session, session, catalog, places):
    _, device = catalog  # неподільна унікальна позиція (capacity=0)
    warehouse, _, _, owner, _ = places
    unit = make_unit(session, device, warehouse, owner, serial="SN-1")
    make_movement(
        session, MovementsType.ADMISSION, [unit],
        destination_storage=warehouse, destination_owner=owner, price=125.0,
    )
    assert ProductDAO.get_acquisition_cost(unit.id) == 125.0


def test_acquisition_cost_manual_override_wins(rx_session, session, catalog, places):
    _, device = catalog
    warehouse, _, _, owner, _ = places
    unit = make_unit(session, device, warehouse, owner, serial="SN-2")
    unit.price = 77.5
    session.add(unit)
    session.commit()
    make_movement(
        session, MovementsType.ADMISSION, [unit],
        destination_storage=warehouse, destination_owner=owner, price=125.0,
    )
    # Ручний override Product.price має пріоритет над базовою ціною позиції.
    assert ProductDAO.get_acquisition_cost(unit.id) == 77.5


def test_acquisition_cost_divisible_is_full_not_proportional(rx_session, session, catalog, places):
    cable, _ = catalog  # подільна з фіксованою ємністю (capacity=100)
    warehouse, _, _, owner, _ = places
    unit = make_unit(session, cable, warehouse, owner, count=50)  # лишилась половина
    make_movement(
        session, MovementsType.ADMISSION, [unit],
        destination_storage=warehouse, destination_owner=owner, price=200.0,
    )
    # Повна вартість постачання, а не пропорційно залишку.
    assert ProductDAO.get_acquisition_cost(unit.id) == 200.0


def test_acquisition_cost_split_child_takes_root_full(rx_session, session, catalog, places):
    cable, _ = catalog
    warehouse, _, _, owner, _ = places
    root = make_unit(session, cable, warehouse, owner, count=70)  # корінь після поділу
    make_movement(
        session, MovementsType.ADMISSION, [root],
        destination_storage=warehouse, destination_owner=owner, price=200.0,
    )
    # Осколок поділу (частина від кореня) — сам не пов'язаний із постачанням.
    child = make_unit(session, cable, warehouse, owner, count=30, parent_id=root.id)
    # Обидва дають повну вартість кореня з постачання.
    assert ProductDAO.get_acquisition_cost(root.id) == 200.0
    assert ProductDAO.get_acquisition_cost(child.id) == 200.0


def test_acquisition_cost_none_without_admission(rx_session, session, catalog, places):
    _, device = catalog
    warehouse, _, _, owner, _ = places
    unit = make_unit(session, device, warehouse, owner, serial="SN-3")
    # Одиниця без постачання й без override — вартість невідома.
    assert ProductDAO.get_acquisition_cost(unit.id) is None


def test_catalog_options_hide_exhausted(rx_session, session, catalog, places):
    cable, device = catalog
    warehouse, _, _, owner, _ = places
    cable_unit = make_unit(session, cable, warehouse, owner, count=100)
    device_unit = make_unit(session, device, warehouse, owner, serial="SN-4")

    all_opts = ProductDAO.get_catalog_options_by_owner_storage(owner.id, warehouse.id)
    assert {row[0] for row in all_opts} == {cable.id, device.id}

    # Виключаємо всі одиниці кабелю — позиція зникає зі списку.
    without_cable = ProductDAO.get_catalog_options_by_owner_storage(
        owner.id, warehouse.id, -1, [cable_unit.id]
    )
    assert {row[0] for row in without_cable} == {device.id}

    # Виключаємо все — список порожній.
    empty = ProductDAO.get_catalog_options_by_owner_storage(
        owner.id, warehouse.id, -1, [cable_unit.id, device_unit.id]
    )
    assert empty == []
