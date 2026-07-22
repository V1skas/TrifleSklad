import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from TrifleSklad import models
from TrifleSklad.audit import get_audit_history, parse_changes, record_action
from TrifleSklad.audit.actions.product_catalog import ProductCatalogUpdated
from TrifleSklad.audit.actions.role import RoleCreated
from TrifleSklad.audit.actions.storage import StorageCreated
from TrifleSklad.audit.actions.worker import WorkerCreated, WorkerDeleted, WorkerUpdated
from TrifleSklad.audit.labels import diff_related_titles
from TrifleSklad.declared import StorageType


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        session.add(models.User(login="admin", id_worker=1, salt="s", password_hash="h"))
        session.commit()
        yield session


@pytest.fixture
def worker():
    return models.Worker(
        id=1, fio="Іван Іванов", phone_number="111", email="a@a.com", position="Комірник", is_default=False
    )


def test_record_action_writes_row_with_correct_data(session, worker):
    action = WorkerCreated.for_create(worker, session)
    record_action(session, "admin", worker.id, action)
    session.commit()

    rows = session.exec(select(models.AuditLog)).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.id_user == "admin"
    assert row.action == "create"
    assert row.table_name == "workers"
    assert row.record_id == "1"
    assert "Іван Іванов" in row.changes


def test_from_diff_keeps_only_changed_fields(worker, session):
    new_worker = worker.model_copy(update={"fio": "Іван Петров", "is_default": True})

    updated = WorkerUpdated.from_diff(worker, new_worker, session)

    assert set(updated.fields.keys()) == {"fio", "is_default"}
    assert updated.fields["fio"].old == "Іван Іванов"
    assert updated.fields["fio"].new == "Іван Петров"


def test_from_diff_with_no_changes_is_not_recorded(worker, session):
    unchanged = WorkerUpdated.from_diff(worker, worker, session)
    assert unchanged.has_changes() is False

    record_action(session, "admin", worker.id, unchanged)
    session.commit()

    assert get_audit_history(session, "workers", worker.id) == []


def test_parse_changes_roundtrips_typed_object(session, worker):
    action = WorkerCreated.for_create(worker, session)
    record_action(session, "admin", worker.id, action)
    session.commit()

    log = get_audit_history(session, "workers", worker.id)[0]
    parsed = parse_changes(log)

    assert isinstance(parsed, WorkerCreated)
    assert parsed.fields["fio"].new == "Іван Іванов"
    assert parsed.describe() == action.describe()


def test_get_audit_history_orders_newest_first(session, worker):
    record_action(session, "admin", worker.id, WorkerCreated.for_create(worker, session))
    session.commit()
    updated = worker.model_copy(update={"fio": "Змінено"})
    record_action(session, "admin", worker.id, WorkerUpdated.from_diff(worker, updated, session))
    session.commit()
    record_action(session, "admin", worker.id, WorkerDeleted.for_delete(updated, session))
    session.commit()

    history = get_audit_history(session, "workers", worker.id)

    assert [entry.action for entry in history] == ["delete", "update", "create"]


def test_fk_resolver_denormalizes_related_title_not_id(session):
    session.add(models.ProductCategory(id=1, title="Меблі"))
    session.add(models.ProductCategory(id=2, title="Електроніка"))
    session.commit()

    old_item = models.ProductCatalog(id=1, title="Стіл", id_category=1, unit="шт", divisible=False, uniq=False)
    new_item = models.ProductCatalog(id=1, title="Стіл", id_category=2, unit="шт", divisible=False, uniq=False)

    updated = ProductCatalogUpdated.from_diff(old_item, new_item, session)

    assert updated.fields["id_category"].old == "Меблі"
    assert updated.fields["id_category"].new == "Електроніка"


def test_storage_resolvers_use_enum_label_and_worker_fio(session):
    session.add(models.Worker(id=1, fio="Петро Петренко", is_default=False))
    session.commit()
    storage = models.Storage(id=1, type=StorageType.WAREHOUSE, title="Склад №1", id_responsible=1, is_default=False)

    created = StorageCreated.for_create(storage, session)

    assert created.fields["type"].new == "Склад"
    assert created.fields["id_responsible"].new == "Петро Петренко"


def test_diff_related_titles_reports_added_and_removed():
    class Item:
        def __init__(self, id, title):
            self.id = id
            self.title = title

    lines = diff_related_titles([Item(1, "Перегляд")], [Item(1, "Перегляд"), Item(2, "Редагування")])

    assert len(lines) == 1
    assert lines[0].kind == "added"
    assert lines[0].title == "Редагування"


def test_role_created_records_granted_actions(session):
    role = models.Role(id=1, title="Оператор", description=None)

    class FakeAction:
        def __init__(self, id, title):
            self.id = id
            self.title = title

    lines = diff_related_titles([], [FakeAction(1, "Перегляд ролей")])
    action = RoleCreated.for_create(role, session, lines=lines)

    assert action.describe() == ["Назва: Оператор", "Опис: —", "Додано: Перегляд ролей"]
