import csv
import io
import pytest
from sqlmodel import Session

from TrifleSklad import models
from TrifleSklad.dao_legacy import MovementDAO
from TrifleSklad.declared import MovementsStatus, MovementsType
from TrifleSklad.states.catalog_movements_report import CatalogMovementsReportState
from tests.conftest import make_movement, make_unit


def test_catalog_movement_stats_and_prices(session: Session, rx_session, catalog, places):
    cable, device = catalog
    warehouse, warehouse2, site, owner, _ = places

    # 1. Постачання
    unit_cable = make_unit(session, cable, warehouse, owner, count=100.0)
    unit_device = make_unit(session, device, warehouse, owner, count=1.0, serial="SN-01")

    m_adm = make_movement(
        session,
        MovementsType.ADMISSION,
        [unit_cable],
        incoming_storage=warehouse,
        incoming_owner=owner,
        date="2026-08-01",
        price=120.0,
    )
    # Друге постачання кабелю з іншою ціною
    unit_cable2 = make_unit(session, cable, warehouse, owner, count=50.0)
    make_movement(
        session,
        MovementsType.ADMISSION,
        [unit_cable2],
        incoming_storage=warehouse,
        incoming_owner=owner,
        date="2026-08-10",
        price=150.0,
    )

    # Постачання роутера
    make_movement(
        session,
        MovementsType.ADMISSION,
        [unit_device],
        incoming_storage=warehouse,
        incoming_owner=owner,
        date="2026-08-02",
        price=800.0,
    )

    # Скасоване постачання (не повинно враховуватись)
    unit_canceled = make_unit(session, cable, warehouse, owner, count=30.0)
    make_movement(
        session,
        MovementsType.ADMISSION,
        [unit_canceled],
        incoming_storage=warehouse,
        incoming_owner=owner,
        date="2026-08-15",
        status=MovementsStatus.CANCELED,
        price=200.0,
    )

    # 2. Видача кабелю
    make_movement(
        session,
        MovementsType.ISSUE,
        [unit_cable],
        incoming_storage=warehouse,
        incoming_owner=owner,
        destination_storage=site,
        date="2026-08-12",
    )

    # Перевірка get_catalog_admission_prices
    prices = MovementDAO.get_catalog_admission_prices([cable.id, device.id])
    cable_prices = [p for p, _ in prices.get(cable.id, [])]
    assert cable_prices == [150.0, 120.0]  # Найсвіжіша першою, скасована (200.0) відсутня

    device_prices = [p for p, _ in prices.get(device.id, [])]
    assert device_prices == [800.0]

    # Перевірка get_catalog_movement_stats
    stats = MovementDAO.get_catalog_movement_stats([cable.id, device.id])

    cable_stats = stats.get(cable.id, {})
    assert cable_stats.get(MovementsType.ADMISSION) == (2, 150.0)  # 2 одиниці, 100 + 50 = 150 м
    assert cable_stats.get(MovementsType.ISSUE) == (1, 100.0)

    device_stats = stats.get(device.id, {})
    assert device_stats.get(MovementsType.ADMISSION) == (1, 1.0)


def test_get_movements_by_catalog_and_csv(session: Session, rx_session, catalog, places, monkeypatch):
    cable, _ = catalog
    warehouse, _, site, owner, _ = places

    unit = make_unit(session, cable, warehouse, owner, count=100.0)
    m_adm = make_movement(
        session,
        MovementsType.ADMISSION,
        [unit],
        incoming_storage=warehouse,
        incoming_owner=owner,
        date="2026-08-01",
        price=120.0,
    )

    worker = models.Worker(fio="Іваненко І.І.")
    session.add(worker)
    session.commit()

    m_iss = make_movement(
        session,
        MovementsType.ISSUE,
        [unit],
        incoming_storage=warehouse,
        incoming_owner=owner,
        destination_storage=site,
        date="2026-08-05",
    )
    issue_extra = models.Issue(id=m_iss.id, id_recipient=worker.id)
    session.add(issue_extra)
    session.commit()

    # Перевірка MovementDAO.get_movements_by_catalog
    total_pages, lines = MovementDAO.get_movements_by_catalog(cable.id, limit=None)
    assert len(lines) == 2

    # Останній за id першим: видача, потім постачання
    iss_line, adm_line = lines[0], lines[1]
    assert iss_line.movement.id == m_iss.id
    assert iss_line.recipient == "Іваненко І.І."
    assert adm_line.movement.id == m_adm.id
    assert adm_line.price == 120.0
    assert adm_line.line_cost == 120.0

    # Перевірка роботи State та експорту CSV
    state = CatalogMovementsReportState()
    state.selected_catalog_id = cable.id
    state.selected_title = cable.title
    state._load_movements(cable.id, cable.title)

    assert state.dialog_unit == "м"
    assert state.dialog_delivered == "1 од. (100 м)"
    assert state.dialog_issued == "1 од. (100 м)"
    assert state.dialog_price_history == "120.00 грн"
    assert len(state.movement_rows) == 2
    # Перевіряємо колонку вартості одиниці в movement_rows (індекс 6)
    assert state.movement_rows[0][6] == "—"  # Видача — прочерк
    assert state.movement_rows[1][6] == "120.00"  # Постачання — 120.00

    # Тест експорту CSV
    event_spec = state.export_csv()
    assert event_spec is not None
