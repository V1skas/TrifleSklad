"""TS-57: фільтр списків руху за позиціями каталогу, що входять до руху.

Перевіряє корельований EXISTS-предикат `movement_filter_conditions(catalog_ids=...)`
через обидва шляхи запиту: прямий по таблиці Movement (`MovementDAO.get_by_type_paginated`,
яким ідуть write_off/movements/returns) і через підзапит `movement_ids`
(`IssueDAO.get_paginated`, спільний шаблон для admission/issue/client_issue/sale/sale_returns).
Семантика — «містить будь-яку з обраних позицій» (OR)."""

from TrifleSklad import models
from TrifleSklad.dao_legacy import IssueDAO, MovementDAO
from TrifleSklad.declared import MovementsType
from tests.conftest import make_movement, make_unit


def test_movement_dao_filters_by_contained_catalog(rx_session, session, catalog, places):
    cable, device = catalog
    warehouse, _, _, owner, _ = places
    cable_unit = make_unit(session, cable, warehouse, owner, count=100)
    device_unit = make_unit(session, device, warehouse, owner, serial="SN-1")
    m_cable = make_movement(
        session, MovementsType.WRITE_OFF, [cable_unit],
        incoming_storage=warehouse, incoming_owner=owner,
    )
    m_device = make_movement(
        session, MovementsType.WRITE_OFF, [device_unit],
        incoming_storage=warehouse, incoming_owner=owner,
    )

    _, only_cable = MovementDAO.get_by_type_paginated(
        MovementsType.WRITE_OFF, catalog_ids=[cable.id]
    )
    assert [m.id for m in only_cable] == [m_cable.id]

    _, only_device = MovementDAO.get_by_type_paginated(
        MovementsType.WRITE_OFF, catalog_ids=[device.id]
    )
    assert [m.id for m in only_device] == [m_device.id]

    _, both = MovementDAO.get_by_type_paginated(
        MovementsType.WRITE_OFF, catalog_ids=[cable.id, device.id]
    )
    assert {m.id for m in both} == {m_cable.id, m_device.id}

    # Порожній / без фільтра — повертає всі рухи типу.
    _, empty_filter = MovementDAO.get_by_type_paginated(
        MovementsType.WRITE_OFF, catalog_ids=[]
    )
    assert {m.id for m in empty_filter} == {m_cable.id, m_device.id}

    _, unfiltered = MovementDAO.get_by_type_paginated(MovementsType.WRITE_OFF)
    assert {m.id for m in unfiltered} == {m_cable.id, m_device.id}


def test_typed_dao_filters_by_contained_catalog_via_subquery(rx_session, session, catalog, places):
    cable, device = catalog
    warehouse, _, site, owner, _ = places
    cable_unit = make_unit(session, cable, warehouse, owner, count=100)
    device_unit = make_unit(session, device, warehouse, owner, serial="SN-2")
    m_cable = make_movement(
        session, MovementsType.ISSUE, [cable_unit],
        incoming_storage=warehouse, incoming_owner=owner, destination_storage=site,
    )
    m_device = make_movement(
        session, MovementsType.ISSUE, [device_unit],
        incoming_storage=warehouse, incoming_owner=owner, destination_storage=site,
    )
    session.add(models.Issue(id=m_cable.id, id_recipient=1))
    session.add(models.Issue(id=m_device.id, id_recipient=1))
    session.commit()

    _, only_device = IssueDAO.get_paginated(catalog_ids=[device.id])
    assert [i.id for i in only_device] == [m_device.id]

    _, unfiltered = IssueDAO.get_paginated()
    assert {i.id for i in unfiltered} == {m_cable.id, m_device.id}
