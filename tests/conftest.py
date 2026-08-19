from typing import List, Optional

import pytest
import reflex as rx
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from TrifleSklad import models
from TrifleSklad.declared import MovementsStatus, MovementsType


@pytest.fixture
def engine():
    # StaticPool — щоб усі з'єднання ділили ОДНУ in-memory БД: сервіси
    # відкривають власні сесії через rx.session(), а тест перевіряє результат
    # своєю сесією.
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    with Session(engine) as session:
        session.add(models.User(login="admin", id_worker=1, salt="s", password_hash="h"))
        session.commit()
        yield session


@pytest.fixture
def rx_session(engine, monkeypatch):
    """Підміняє rx.session() на сесію тестового engine — щоб сервіси, які самі
    володіють транзакцією (`with rx.session()`), працювали з in-memory БД."""
    monkeypatch.setattr(rx, "session", lambda: Session(engine))
    return engine


def grant(session: Session, login: str, *codes: str) -> None:
    """Видає користувачу прямі права (users_actions) — для перевірки гвардів."""
    for code in codes:
        action = models.Action(code=code, title=code, description="")
        session.add(action)
        session.commit()
        session.add(models.UsersActions(id_user=login, id_action=action.id))
    session.commit()


@pytest.fixture
def catalog(session):
    """Дві позиції каталогу: витратна подільна (кабель) і унікальна серійна."""
    cable = models.ProductCatalog(
        title="Кабель", unit="м", divisible=True, uniq=False, capacity=100, count=0
    )
    device = models.ProductCatalog(
        title="Роутер", unit="шт", divisible=False, uniq=True, capacity=0, count=0
    )
    session.add_all([cable, device])
    session.commit()
    return cable, device


@pytest.fixture
def places(session):
    """Склад-джерело, склад-призначення, площадка і власник."""
    warehouse = models.Storage(title="Склад №1", type=1)
    warehouse2 = models.Storage(title="Склад №2", type=1)
    site = models.Storage(title="Площадка", type=2)
    owner = models.Owner(title="Власник")
    owner2 = models.Owner(title="Власник 2")
    session.add_all([warehouse, warehouse2, site, owner, owner2])
    session.commit()
    return warehouse, warehouse2, site, owner, owner2


def make_unit(
    session: Session,
    catalog: models.ProductCatalog,
    storage: models.Storage,
    owner: models.Owner,
    *,
    count: float = 1,
    serial: str = "",
    is_deleted: bool = False,
    parent_id: Optional[int] = None,
) -> models.Product:
    unit = models.Product(
        serial_number=serial,
        id_product_catalog=catalog.id,
        id_storage=storage.id,
        id_owner=owner.id,
        id_parent=parent_id,
        count=count,
        is_deleted=is_deleted,
    )
    session.add(unit)
    session.commit()
    return unit


def make_movement(
    session: Session,
    type: int,
    units: List[models.Product],
    *,
    incoming_storage: Optional[models.Storage] = None,
    incoming_owner: Optional[models.Owner] = None,
    destination_storage: Optional[models.Storage] = None,
    destination_owner: Optional[models.Owner] = None,
    date: str = "2026-07-20",
    status: int = MovementsStatus.CREATED,
    price: float = 0.0,
) -> models.Movement:
    """Рух із позиціями, згрупованими за каталогом (як це роблять Add*State)."""
    movement = models.Movement(
        type=type,
        id_user="admin",
        id_incoming_storage=incoming_storage.id if incoming_storage else None,
        id_incoming_owner=incoming_owner.id if incoming_owner else None,
        id_destination_storage=destination_storage.id if destination_storage else None,
        id_destination_owner=destination_owner.id if destination_owner else None,
        date=date,
        comment="",
        status=status,
        total_cost=0.0,
    )
    session.add(movement)
    session.commit()

    by_catalog: dict = {}
    for unit in units:
        by_catalog.setdefault(unit.id_product_catalog, []).append(unit)
    for catalog_id, catalog_units in by_catalog.items():
        session.add(
            models.MovementProductsCatalog(
                id_movement=movement.id,
                id_product_catalog=catalog_id,
                count=len(catalog_units),
                price=price,
                products=list(catalog_units),
            )
        )
    session.commit()
    session.refresh(movement)
    return movement


__all__ = ["MovementsType", "make_movement", "make_unit"]
