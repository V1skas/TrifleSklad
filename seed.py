"""Наповнення бази тестовими даними для локальної розробки.

Повністю очищує локальну SQLite-БД (reflex.db) і наповнює її великим
об'ємом взаємопов'язаних тестових даних — усі довідники + декілька сотень
рухів ТМЦ (постачання/списання/переміщення/видача/продаж/повернення/заявки),
щоб було зручно тестувати пагінацію, фільтри та детальні перегляди.

Запуск: uv run seed.py

Логін після наповнення: admin / new_admin (Супер-Адміністратор, усі права) —
той самий, що й раніше, зберігається навмисно (див. пам'ять сесії).

Скрипт НЕ використовує dao_legacy.py напряму (щоб уникнути плутанини з
відокремленими інстансами між сесіями), а відтворює ту саму бізнес-логіку, що
й відповідні DAO-методи (перевірено читанням їхнього коду), працюючи власними,
явно керованими сесіями по фазах.
"""

import random
import shutil
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import reflex as rx
from sqlmodel import select
from sqlalchemy.orm import selectinload

from TrifleSklad.declared import (
    MovementsStatus,
    MovementsType,
    RequestStatus,
    StorageType,
    sale_line_cost,
)
from TrifleSklad.models import (
    Action,
    Admission,
    ClientIssue,
    Issue,
    Movement,
    MovementProductsCatalog,
    NDSRate,
    Owner,
    PaymentType,
    Product,
    ProductCatalog,
    ProductCategory,
    Request,
    RequestProductsCatalog,
    Role,
    Sale,
    SaleReturn,
    Storage,
    Supplier,
    User,
    Worker,
)
from TrifleSklad.services.auth import generate_password_hash
from TrifleSklad.utils.clock import now_local
from update import sync_actions

RNG = random.Random(42)
DB_PATH = Path("reflex.db")


# ============================================================================
# Довідкові дані (без залежності від бібліотек типу Faker — руками, укр.)
# ============================================================================

FIRST_NAMES_M = [
    "Олександр", "Іван", "Микола", "Андрій", "Сергій", "Дмитро", "Володимир",
    "Роман", "Тарас", "Богдан", "Максим", "Віктор", "Юрій", "Павло", "Артем",
]
FIRST_NAMES_F = [
    "Олена", "Марія", "Наталія", "Тетяна", "Оксана", "Ірина", "Юлія",
    "Світлана", "Анна", "Катерина", "Людмила", "Вікторія",
]
LAST_NAMES = [
    "Коваленко", "Бондаренко", "Ткаченко", "Кравченко", "Олійник", "Шевченко",
    "Мельник", "Гончаренко", "Полтавець", "Захарченко", "Савченко", "Руденко",
    "Марченко", "Лисенко", "Данилюк", "Сидоренко", "Пономаренко", "Кушнір",
    "Гриценко", "Іщенко",
]
POSITIONS = [
    "Комірник", "Менеджер зі збуту", "Бухгалтер", "Начальник складу",
    "Оператор ПК", "Логіст", "Технік", "Продавець-консультант",
    "Керівник відділу", "Кладовщик",
]

CITIES = ["Київ", "Харків", "Одеса", "Дніпро", "Львів", "Запоріжжя", "Вінниця", "Полтава"]
STREETS = ["вул. Гагаріна", "вул. Шевченка", "просп. Перемоги", "вул. Соборна", "вул. Промислова", "вул. Індустріальна"]

def rand_address() -> str:
    return f"м. {RNG.choice(CITIES)}, {RNG.choice(STREETS)} {RNG.randint(1, 200)}"


CATEGORY_TREE: Dict[str, List[str]] = {
    "Електроінструмент": ["Дрилі та шуруповерти", "Кутошліфувальні машини"],
    "Кабельна продукція": ["Силовий кабель", "Кабель зв'язку"],
    "Кріпильні вироби": [],
    "Будівельні матеріали": ["Сипучі матеріали", "Лакофарбові матеріали"],
    "Оргтехніка": [],
    "Меблі": [],
    "Спецодяг та ЗІЗ": [],
    "Сантехніка": [],
}

# (title, unit, kind) — kind: "divisible" | "uniq" | "plain"
CATALOG_ITEMS: List[Tuple[str, str, str]] = [
    ("Кабель ВВГ 3x2.5", "м", "divisible"),
    ("Кабель ВВГ 3x1.5", "м", "divisible"),
    ("Кабель UTP cat.5e", "м", "divisible"),
    ("Труба ПВХ 20мм", "м", "divisible"),
    ("Труба ПВХ 32мм", "м", "divisible"),
    ("Пісок будівельний", "кг", "divisible"),
    ("Цемент М400", "кг", "divisible"),
    ("Фарба інтер'єрна біла", "л", "divisible"),
    ("Ґрунтовка універсальна", "л", "divisible"),
    ("Стрічка ізоляційна", "м", "divisible"),
    ("Шпагат будівельний", "м", "divisible"),
    ("Дріт в'язальний", "кг", "divisible"),
    ("Перфоратор Bosch GBH", "шт", "uniq"),
    ("Шуруповерт Makita DDF", "шт", "uniq"),
    ("Кутошліфувальна машина Interskol", "шт", "uniq"),
    ("Зварювальний апарат Патон", "шт", "uniq"),
    ("Ноутбук Dell Latitude", "шт", "uniq"),
    ("Монітор Samsung 24\"", "шт", "uniq"),
    ("Принтер HP LaserJet", "шт", "uniq"),
    ("Генератор бензиновий", "шт", "uniq"),
    ("Драбина алюмінієва 3м", "шт", "uniq"),
    ("Компресор повітряний", "шт", "uniq"),
    ("Стіл офісний", "шт", "plain"),
    ("Стілець офісний", "шт", "plain"),
    ("Шафа металева", "шт", "plain"),
    ("Каска захисна", "шт", "plain"),
    ("Рукавиці робочі", "пара", "plain"),
    ("Окуляри захисні", "шт", "plain"),
    ("Саморіз 3.5x25", "шт", "plain"),
    ("Дюбель 6x40", "шт", "plain"),
    ("Болт М8x40", "шт", "plain"),
    ("Гайка М8", "шт", "plain"),
    ("Розетка накладна", "шт", "plain"),
    ("Вимикач одноклавішний", "шт", "plain"),
    ("Лампа LED 10Вт", "шт", "plain"),
    ("Змішувач для кухні", "шт", "plain"),
    ("Кран кульовий 1/2\"", "шт", "plain"),
    ("Фітинг кутовий", "шт", "plain"),
    ("Валик малярний", "шт", "plain"),
    ("Пензель малярний", "шт", "plain"),
]

OWNER_NAMES = [
    "ТОВ «Алваріум»", "ПП «Технобуд»", "ТОВ «Електросвіт»", "ФОП Коваленко О.В.",
    "ТОВ «Мегабуд»", "ТОВ «Промресурс»", "ПП «Інтерсервіс»", "ТОВ «South Trade»",
]

SUPPLIER_NAMES = [
    "ТОВ «Епіцентр К»", "ТОВ «Метал Групп»", "ПП «Кабельний завод»",
    "ТОВ «Будматеріали Плюс»", "ТОВ «Електропостач»", "ФОП Гриценко Р.М.",
    "ТОВ «Інструмент Сервіс»", "ТОВ «Оптторг»", "ПП «Технокомплект»",
    "ТОВ «Прайм Дистриб'юшн»",
]

STORAGE_DEFS: List[Tuple[str, int]] = [
    ("Головний склад №1", StorageType.WAREHOUSE),
    ("Склад Гагарина 7", StorageType.WAREHOUSE),
    ("Склад металопрокату", StorageType.WAREHOUSE),
    ("Резервний склад", StorageType.WAREHOUSE),
    ("Склад електрики", StorageType.WAREHOUSE),
    ("Склад інструменту", StorageType.WAREHOUSE),
    ("Площадка Об'єкт-1", StorageType.TECHNICAL_SITE),
    ("Площадка Об'єкт-2", StorageType.TECHNICAL_SITE),
    ("Площадка Об'єкт-3", StorageType.TECHNICAL_SITE),
    ("Площадка Об'єкт-4", StorageType.TECHNICAL_SITE),
    ("Бухгалтерія", StorageType.DEPARTMENT),
    ("IT-відділ", StorageType.DEPARTMENT),
    ("Відділ логістики", StorageType.DEPARTMENT),
    ("Клієнт: Будмайстер", StorageType.CLIENT),
]

PAYMENT_TYPE_NAMES = ["Готівка", "Безготівковий розрахунок", "Банківська картка", "Відстрочка платежу", "Бартер"]
NDS_RATE_DEFS = [("Без ПДВ", 0.0), ("ПДВ 7%", 7.0), ("ПДВ 14%", 14.0), ("ПДВ 20%", 20.0)]

ROLE_DEFS: List[Tuple[str, str, List[str]]] = [
    ("Комірник", "Робота зі складом і рухом ТМЦ", ["admissions", "write_offs", "movements", "products", "categories"]),
    ("Бухгалтер", "Довідники та звітність", ["payment_types", "nds_rates", "suppliers", "reports"]),
    ("Менеджер продажів", "Продажі та заявки", ["sales", "sale_returns", "requests", "owners"]),
    ("Оператор видачі", "Видача ТМЦ", ["issues", "client_issues", "returns", "workers"]),
    ("Спостерігач", "Перегляд без редагування (усі *:list/*:view)", ["*:list", "*:view"]),
]


# ============================================================================
# Фаза 0: скидання БД
# ============================================================================

# Порядок — діти перед батьками (щоб не зачепити FK, навіть якщо вони
# ввімкнені); alembic_version НЕ чіпаємо — схема лишається як є (реплей усього
# ланцюжка міграцій з нуля падає на поточній версії SQLAlchemy/Alembic через
# несумісність у старій міграції 68cec538ba45 — окрема, не пов'язана з цим
# скриптом проблема; тому замість "видалити файл БД і накатити міграції
# заново" ми просто чистимо рядки в наявній, вже коректно змігрованій схемі).
TABLES_IN_DELETE_ORDER = [
    "users_actions", "users_roles", "roles_actions",
    "movements_products",
    "requests_products_catalog",
    "sale_returns", "client_issues", "issues", "sales", "admissions",
    "movements_products_catalog",
    "movements",
    "requests",
    "products",
    "products_catalog",
    "product_categories",
    "storages",
    "suppliers",
    "owners",
    "payment_types",
    "nds_rates",
    "auth_tokens",
    "users",
    "workers",
    "roles",
    "actions",
]


def reset_database() -> None:
    import sqlite3

    if not DB_PATH.exists():
        print("[seed] reflex.db не знайдено — застосовуємо міграції на чистій БД...")
        result = subprocess.run(["uv", "run", "reflex", "db", "migrate"], capture_output=True, text=True)
        if result.returncode != 0:
            print(result.stdout)
            print(result.stderr)
            print("[seed] Помилка застосування міграцій. Зупинка.")
            sys.exit(1)

    backup = DB_PATH.with_name(f"reflex.db.bak-preseed-{now_local().strftime('%Y%m%d_%H%M%S')}")
    shutil.copy2(DB_PATH, backup)
    print(f"[seed] Бекап поточної БД: {backup}")

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        for table in TABLES_IN_DELETE_ORDER:
            cur.execute(f"DELETE FROM {table}")
        # sqlite_sequence існує лише якщо є хоч одна таблиця з AUTOINCREMENT
        # (а не просто INTEGER PRIMARY KEY) — тут таких немає, це нормально.
        if cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'"
        ).fetchone():
            cur.execute("DELETE FROM sqlite_sequence")
        conn.commit()
    finally:
        conn.close()
    print("[seed] Дані очищено (схема й міграції лишились як були).")


# ============================================================================
# Фаза 1: базовий бутстрап (actions, admin worker/user/role) — як deploy.py,
# але логін/пароль admin/new_admin (усталений у цьому проєкті dev-логін).
# ============================================================================

def bootstrap_core() -> Dict[str, int]:
    with rx.session() as session:
        sync_actions(session)

        worker = Worker(fio="Головний Адміністратор", position="Системний адміністратор")
        session.add(worker)
        session.commit()
        session.refresh(worker)

        salt = "seed_salt_0000000000000000000000"[:32]
        user = User(
            login="admin",
            id_worker=worker.id,
            salt=salt,
            password_hash=generate_password_hash("new_admin", salt),
        )
        session.add(user)

        admin_role = Role(title="Супер-Адміністратор", description="Повний доступ до всіх функцій системи")
        all_actions = session.exec(select(Action)).all()
        admin_role.actions = all_actions
        session.add(admin_role)
        user.roles = [admin_role]

        session.commit()
        print(f"[seed] Bootstrap: admin/new_admin, {len(all_actions)} прав.")
        return {"admin_worker_id": worker.id, "admin_role_id": admin_role.id, "n_actions": len(all_actions)}


# ============================================================================
# Фаза 2: довідники (категорії, каталог ТМЦ, власники, постачальники, склади,
# типи оплат, ставки ПДВ, співробітники, ролі, користувачі)
# ============================================================================

class LookupContext:
    def __init__(self):
        self.category_ids: List[int] = []
        self.catalog_items: List[Dict] = []  # {id, title, unit, divisible, uniq, capacity}
        self.owner_ids: List[int] = []
        self.supplier_ids: List[int] = []
        self.storages: List[Dict] = []  # {id, type, title}
        self.payment_type_ids: List[int] = []
        self.nds_rate_ids: Dict[float, int] = {}
        self.worker_ids: List[int] = []
        self.role_ids: Dict[str, int] = {}
        self.user_logins: List[str] = []


def seed_lookup_data(admin_worker_id: int) -> LookupContext:
    ctx = LookupContext()

    with rx.session() as session:
        # --- категорії (з декількома підкатегоріями) ---
        for parent_title, children in CATEGORY_TREE.items():
            parent = ProductCategory(title=parent_title)
            session.add(parent)
            session.flush()
            ctx.category_ids.append(parent.id)
            for child_title in children:
                child = ProductCategory(title=child_title, id_parent=parent.id)
                session.add(child)
                session.flush()
                ctx.category_ids.append(child.id)
        session.commit()
        print(f"[seed] Категорій: {len(ctx.category_ids)}")

        # --- каталог ТМЦ ---
        for title, unit, kind in CATALOG_ITEMS:
            divisible = kind == "divisible"
            uniq = kind == "uniq"
            capacity = RNG.choice([50, 100, 200, 500, 1000]) if divisible else 0
            item = ProductCatalog(
                title=title,
                unit=unit,
                divisible=divisible,
                uniq=uniq,
                capacity=capacity,
                id_category=RNG.choice(ctx.category_ids),
            )
            session.add(item)
            session.flush()
            ctx.catalog_items.append({
                "id": item.id, "title": title, "unit": unit,
                "divisible": divisible, "uniq": uniq, "capacity": capacity,
            })
        session.commit()
        print(f"[seed] Позицій каталогу: {len(ctx.catalog_items)}")

        # --- власники ---
        for i, name in enumerate(OWNER_NAMES):
            owner = Owner(title=name, description=f"Тестовий власник №{i + 1}", is_default=(i == 0))
            session.add(owner)
            session.flush()
            ctx.owner_ids.append(owner.id)
        session.commit()
        print(f"[seed] Власників: {len(ctx.owner_ids)}")

        # --- постачальники ---
        for i, name in enumerate(SUPPLIER_NAMES):
            supplier = Supplier(
                title=name,
                address=rand_address(),
                email=f"supplier{i + 1}@example.com",
                contact_person=f"{RNG.choice(FIRST_NAMES_M + FIRST_NAMES_F)} {RNG.choice(LAST_NAMES)}",
                contact_phone=f"+380{RNG.randint(500000000, 999999999)}",
                edrpou=str(RNG.randint(10000000, 99999999)),
            )
            session.add(supplier)
            session.flush()
            ctx.supplier_ids.append(supplier.id)
        session.commit()
        print(f"[seed] Постачальників: {len(ctx.supplier_ids)}")

        # --- співробітники (включно з тим, хто вже є — admin worker) ---
        ctx.worker_ids.append(admin_worker_id)
        for i in range(24):
            is_male = RNG.random() < 0.5
            first = RNG.choice(FIRST_NAMES_M if is_male else FIRST_NAMES_F)
            last = RNG.choice(LAST_NAMES)
            worker = Worker(
                fio=f"{last} {first}",
                position=RNG.choice(POSITIONS),
                phone_number=f"+380{RNG.randint(500000000, 999999999)}",
                email=f"worker{i + 1}@example.com",
            )
            session.add(worker)
            session.flush()
            ctx.worker_ids.append(worker.id)
        session.commit()
        print(f"[seed] Співробітників: {len(ctx.worker_ids)}")

        # --- склади (id_responsible — реальний worker) ---
        for title, storage_type in STORAGE_DEFS:
            storage = Storage(
                type=storage_type,
                title=title,
                address=rand_address(),
                id_responsible=RNG.choice(ctx.worker_ids),
                is_default=False,
            )
            session.add(storage)
            session.flush()
            ctx.storages.append({"id": storage.id, "type": storage_type, "title": title})
        # перший склад кожного типу — за замовчуванням
        seen_types = set()
        for s in ctx.storages:
            if s["type"] not in seen_types:
                seen_types.add(s["type"])
                obj = session.get(Storage, s["id"])
                obj.is_default = True
                session.add(obj)
        session.commit()
        print(f"[seed] Складів/площадок/відділів: {len(ctx.storages)}")

        # --- типи оплат ---
        for i, name in enumerate(PAYMENT_TYPE_NAMES):
            pt = PaymentType(title=name, is_default=(i == 0))
            session.add(pt)
            session.flush()
            ctx.payment_type_ids.append(pt.id)
        session.commit()
        print(f"[seed] Типів оплат: {len(ctx.payment_type_ids)}")

        # --- ставки ПДВ ---
        for name, rate in NDS_RATE_DEFS:
            nds = NDSRate(title=name, rate=rate)
            session.add(nds)
            session.flush()
            ctx.nds_rate_ids[rate] = nds.id
        session.commit()
        print(f"[seed] Ставок ПДВ: {len(ctx.nds_rate_ids)}")

        # --- ролі ---
        all_actions = session.exec(select(Action)).all()
        for title, description, prefixes in ROLE_DEFS:
            role = Role(title=title, description=description)
            if "*:list" in prefixes:
                matched = [a for a in all_actions if a.code.endswith(":list") or a.code.endswith(":view")]
            else:
                matched = [a for a in all_actions if any(a.code.startswith(p + ":") for p in prefixes)]
            role.actions = matched
            session.add(role)
            session.flush()
            ctx.role_ids[title] = role.id
        session.commit()
        print(f"[seed] Ролей: {len(ctx.role_ids)}")

        # --- користувачі (додатково до admin) ---
        role_titles = list(ctx.role_ids.keys())
        chosen_workers = RNG.sample(ctx.worker_ids[1:], k=min(16, len(ctx.worker_ids) - 1))
        for i, worker_id in enumerate(chosen_workers):
            login = f"user{i + 1}"
            salt = generate_password_hash("salt_seed", str(i))[:32]
            user = User(
                login=login,
                id_worker=worker_id,
                salt=salt,
                password_hash=generate_password_hash("password", salt),
            )
            role = session.get(Role, ctx.role_ids[RNG.choice(role_titles)])
            user.roles = [role]
            session.add(user)
            ctx.user_logins.append(login)
        session.commit()
        print(f"[seed] Користувачів (крім admin): {len(ctx.user_logins)} (пароль усіх: password)")

    return ctx


# ============================================================================
# Фаза 3: постачання (наповнює склади одиницями ТМЦ)
# ============================================================================

class StockPool:
    """product_id -> {catalog_id, storage_id, owner_id, divisible, uniq, capacity}"""

    def __init__(self):
        self.units: Dict[int, Dict] = {}

    def add(self, product_id: int, catalog_id: int, storage_id: int, owner_id: int, meta: Dict):
        self.units[product_id] = {
            "catalog_id": catalog_id, "storage_id": storage_id, "owner_id": owner_id,
            "divisible": meta["divisible"], "uniq": meta["uniq"], "capacity": meta["capacity"],
        }

    def remove(self, product_id: int):
        self.units.pop(product_id, None)

    def relocate(self, product_id: int, storage_id: int, owner_id: Optional[int] = None):
        if product_id in self.units:
            self.units[product_id]["storage_id"] = storage_id
            if owner_id is not None:
                self.units[product_id]["owner_id"] = owner_id

    def by_storage_type(self, storages: List[Dict], storage_type: int, min_count: int = 1) -> List[int]:
        type_storage_ids = {s["id"] for s in storages if s["type"] == storage_type}
        ids = [pid for pid, u in self.units.items() if u["storage_id"] in type_storage_ids]
        return ids if len(ids) >= min_count else []


def _admission_line_totals(count: int, price: float, rate: float, flag_nds: bool) -> float:
    if not rate:
        return round(count * price, 2)
    if flag_nds:
        return round(count * price, 2)
    base = count * price
    nds = base * rate / 100
    return round(base + nds, 2)


def seed_admissions(ctx: LookupContext, pool: StockPool, admin_login: str, n: int = 90) -> None:
    warehouse_ids = [s["id"] for s in ctx.storages if s["type"] == StorageType.WAREHOUSE]
    start_date = now_local().date() - timedelta(days=200)
    used_invoice_numbers = set()

    with rx.session() as session:
        for i in range(n):
            supplier_id = RNG.choice(ctx.supplier_ids)
            storage_id = RNG.choice(warehouse_ids)
            owner_id = RNG.choice(ctx.owner_ids)
            payment_type_id = RNG.choice(ctx.payment_type_ids)
            date = (start_date + timedelta(days=RNG.randint(0, 199))).isoformat()
            flag_nds = RNG.random() < 0.4
            rate = RNG.choice([0.0, 7.0, 14.0, 20.0])
            nds_rate_id = ctx.nds_rate_ids[rate] if rate else RNG.choice([None, ctx.nds_rate_ids[0.0]])

            invoice_number = f"INV-{2000 + i}-{RNG.randint(100, 999)}"
            while invoice_number in used_invoice_numbers:
                invoice_number = f"INV-{2000 + i}-{RNG.randint(100, 999)}"
            used_invoice_numbers.add(invoice_number)

            n_lines = RNG.randint(1, 4)
            chosen_catalog = RNG.sample(ctx.catalog_items, k=min(n_lines, len(ctx.catalog_items)))

            movement = Movement(
                type=MovementsType.ADMISSION,
                id_user=admin_login,
                id_destination_storage=storage_id,
                id_destination_owner=owner_id,
                date=date,
                comment="",
                status=RNG.choice([MovementsStatus.CLOSED, MovementsStatus.CLOSED, MovementsStatus.IN_PROGRESS]),
                total_cost=0.0,
                products_catalog=[],
            )

            total_cost = 0.0
            for meta in chosen_catalog:
                per_unit = meta["capacity"] if meta["divisible"] else 1
                units_count = RNG.randint(1, 5) if meta["uniq"] else RNG.randint(1, 8)
                price = round(RNG.uniform(15, 2500), 2)

                products = []
                for _ in range(units_count):
                    serial = ""
                    if meta["uniq"]:
                        serial = f"SN-{meta['id']}-{RNG.randint(100000, 999999)}"
                    products.append(Product(
                        id_product_catalog=meta["id"],
                        id_storage=storage_id,
                        id_owner=owner_id,
                        serial_number=serial,
                        count=per_unit,
                    ))

                mpc = MovementProductsCatalog(
                    id_product_catalog=meta["id"],
                    count=units_count,
                    price=price,
                    products=products,
                )
                movement.products_catalog.append(mpc)
                total_cost += _admission_line_totals(units_count, price, rate, flag_nds)

            movement.total_cost = round(total_cost, 2)

            admission = Admission(
                id_payment_type=payment_type_id,
                id_supplier=supplier_id,
                flag_nds=flag_nds,
                id_nds_rate=nds_rate_id,
                dollar_rate=round(RNG.uniform(38, 42), 2),
                invoice_number=invoice_number,
                movement=movement,
            )
            session.add(admission)
            session.flush()

            for mpc in movement.products_catalog:
                for product in mpc.products:
                    session.flush()
                    pool.add(product.id, mpc.id_product_catalog, storage_id, owner_id,
                              next(c for c in ctx.catalog_items if c["id"] == mpc.id_product_catalog))

            if (i + 1) % 15 == 0:
                session.commit()
        session.commit()

    print(f"[seed] Постачань: {n}, одиниць ТМЦ створено: {len(pool.units)}")


# ============================================================================
# Фаза 4: рух ТМЦ (списання, переміщення, видача, видача клієнту, продаж,
# повернення, повернення продажу)
# ============================================================================

def seed_write_offs(ctx: LookupContext, pool: StockPool, admin_login: str, n: int = 30) -> None:
    warehouse_ids = [s["id"] for s in ctx.storages if s["type"] == StorageType.WAREHOUSE]
    with rx.session() as session:
        created = 0
        for _ in range(n):
            candidates = [pid for pid, u in pool.units.items() if u["storage_id"] in warehouse_ids]
            if not candidates:
                break
            storage_id = RNG.choice(warehouse_ids)
            pids = [pid for pid in candidates if pool.units[pid]["storage_id"] == storage_id]
            if not pids:
                continue
            picked = RNG.sample(pids, k=min(RNG.randint(1, 5), len(pids)))
            products = session.exec(select(Product).where(Product.id.in_(picked))).all()
            if not products:
                continue

            by_catalog: Dict[int, List[Product]] = {}
            for p in products:
                by_catalog.setdefault(p.id_product_catalog, []).append(p)

            owner_id = pool.units[picked[0]]["owner_id"]
            movement = Movement(
                type=MovementsType.WRITE_OFF,
                id_user=admin_login,
                id_incoming_storage=storage_id,
                id_incoming_owner=owner_id,
                date=(now_local().date() - timedelta(days=RNG.randint(0, 150))).isoformat(),
                comment=RNG.choice(["Пересортиця", "Брак", "Втрата", "Списання за актом"]),
                status=MovementsStatus.CLOSED,
                total_cost=0.0,
                products_catalog=[
                    MovementProductsCatalog(id_product_catalog=cid, count=len(units), products=units)
                    for cid, units in by_catalog.items()
                ],
            )
            session.add(movement)
            session.flush()

            for p in products:
                p.is_deleted = True
                session.add(p)
                pool.remove(p.id)
            created += 1
            if created % 10 == 0:
                session.commit()
        session.commit()
    print(f"[seed] Списань: {created}")


def seed_relocations(ctx: LookupContext, pool: StockPool, admin_login: str, n: int = 35) -> None:
    warehouse_ids = [s["id"] for s in ctx.storages if s["type"] == StorageType.WAREHOUSE]
    with rx.session() as session:
        created = 0
        for _ in range(n):
            src_candidates = [pid for pid, u in pool.units.items() if u["storage_id"] in warehouse_ids]
            if len(warehouse_ids) < 2 or not src_candidates:
                break
            src_storage = RNG.choice(warehouse_ids)
            dst_storage = RNG.choice([s for s in warehouse_ids if s != src_storage])
            pids = [pid for pid in src_candidates if pool.units[pid]["storage_id"] == src_storage]
            if not pids:
                continue
            picked = RNG.sample(pids, k=min(RNG.randint(1, 4), len(pids)))
            products = session.exec(select(Product).where(Product.id.in_(picked))).all()
            if not products:
                continue

            by_catalog: Dict[int, List[Product]] = {}
            for p in products:
                by_catalog.setdefault(p.id_product_catalog, []).append(p)

            owner_id = pool.units[picked[0]]["owner_id"]
            movement = Movement(
                type=MovementsType.MOVEMENT,
                id_user=admin_login,
                id_incoming_storage=src_storage,
                id_destination_storage=dst_storage,
                id_incoming_owner=owner_id,
                id_destination_owner=owner_id,
                date=(now_local().date() - timedelta(days=RNG.randint(0, 150))).isoformat(),
                comment="Планове переміщення",
                status=MovementsStatus.CLOSED,
                total_cost=0.0,
                products_catalog=[
                    MovementProductsCatalog(id_product_catalog=cid, count=len(units), products=units)
                    for cid, units in by_catalog.items()
                ],
            )
            session.add(movement)
            session.flush()

            for p in products:
                p.id_storage = dst_storage
                session.add(p)
                pool.relocate(p.id, dst_storage)
            created += 1
            if created % 10 == 0:
                session.commit()
        session.commit()
    print(f"[seed] Переміщень: {created}")


def _apply_issue_relocation(session, products: List[Product], pool: StockPool, dst_storage: int, dst_owner: int) -> None:
    for p in products:
        meta = pool.units.get(p.id)
        uniq = meta["uniq"] if meta else False
        if uniq:
            p.id_storage = dst_storage
            p.id_owner = dst_owner
            session.add(p)
            pool.relocate(p.id, dst_storage, dst_owner)
        else:
            p.is_deleted = True
            session.add(p)
            pool.remove(p.id)


def seed_issues(ctx: LookupContext, pool: StockPool, admin_login: str, n: int = 35) -> List[int]:
    warehouse_ids = [s["id"] for s in ctx.storages if s["type"] == StorageType.WAREHOUSE]
    dest_ids = [s["id"] for s in ctx.storages if s["type"] in (StorageType.TECHNICAL_SITE, StorageType.DEPARTMENT)]
    created_movement_ids: List[int] = []
    with rx.session() as session:
        created = 0
        for _ in range(n):
            candidates = [pid for pid, u in pool.units.items() if u["storage_id"] in warehouse_ids]
            if not candidates or not dest_ids:
                break
            src_storage = RNG.choice(warehouse_ids)
            pids = [pid for pid in candidates if pool.units[pid]["storage_id"] == src_storage]
            if not pids:
                continue
            picked = RNG.sample(pids, k=min(RNG.randint(1, 4), len(pids)))
            products = session.exec(
                select(Product).options(selectinload(Product.product_catalog)).where(Product.id.in_(picked))
            ).all()
            if not products:
                continue

            by_catalog: Dict[int, List[Product]] = {}
            for p in products:
                by_catalog.setdefault(p.id_product_catalog, []).append(p)

            src_owner = pool.units[picked[0]]["owner_id"]
            dst_storage = RNG.choice(dest_ids)
            dst_owner = RNG.choice(ctx.owner_ids)
            recipient_id = RNG.choice(ctx.worker_ids)

            movement = Movement(
                type=MovementsType.ISSUE,
                id_user=admin_login,
                id_incoming_storage=src_storage,
                id_destination_storage=dst_storage,
                id_incoming_owner=src_owner,
                id_destination_owner=dst_owner,
                date=(now_local().date() - timedelta(days=RNG.randint(0, 120))).isoformat(),
                comment="Видача на об'єкт",
                status=MovementsStatus.CLOSED,
                total_cost=0.0,
                products_catalog=[
                    MovementProductsCatalog(id_product_catalog=cid, count=len(units), products=units)
                    for cid, units in by_catalog.items()
                ],
            )
            issue = Issue(id_recipient=recipient_id, movement=movement)
            session.add(issue)
            session.flush()

            _apply_issue_relocation(session, products, pool, dst_storage, dst_owner)
            created_movement_ids.append(movement.id)
            created += 1
            if created % 10 == 0:
                session.commit()
        session.commit()
    print(f"[seed] Видач: {created}")
    return created_movement_ids


def seed_client_issues(ctx: LookupContext, pool: StockPool, admin_login: str, n: int = 20) -> None:
    warehouse_ids = [s["id"] for s in ctx.storages if s["type"] == StorageType.WAREHOUSE]
    client_ids = [s["id"] for s in ctx.storages if s["type"] == StorageType.CLIENT]
    with rx.session() as session:
        created = 0
        for _ in range(n):
            candidates = [pid for pid, u in pool.units.items() if u["storage_id"] in warehouse_ids]
            if not candidates or not client_ids:
                break
            src_storage = RNG.choice(warehouse_ids)
            pids = [pid for pid in candidates if pool.units[pid]["storage_id"] == src_storage]
            if not pids:
                continue
            picked = RNG.sample(pids, k=min(RNG.randint(1, 3), len(pids)))
            products = session.exec(
                select(Product).options(selectinload(Product.product_catalog)).where(Product.id.in_(picked))
            ).all()
            if not products:
                continue

            by_catalog: Dict[int, List[Product]] = {}
            for p in products:
                by_catalog.setdefault(p.id_product_catalog, []).append(p)

            src_owner = pool.units[picked[0]]["owner_id"]
            dst_storage = RNG.choice(client_ids)
            dst_owner = RNG.choice(ctx.owner_ids)
            recipient_id = RNG.choice(ctx.worker_ids)

            movement = Movement(
                type=MovementsType.CLIENT_ISSUE,
                id_user=admin_login,
                id_incoming_storage=src_storage,
                id_destination_storage=dst_storage,
                id_incoming_owner=src_owner,
                id_destination_owner=dst_owner,
                date=(now_local().date() - timedelta(days=RNG.randint(0, 120))).isoformat(),
                comment="Видача клієнту за договором",
                status=MovementsStatus.CLOSED,
                total_cost=0.0,
                products_catalog=[
                    MovementProductsCatalog(id_product_catalog=cid, count=len(units), products=units)
                    for cid, units in by_catalog.items()
                ],
            )
            client_issue = ClientIssue(
                id_recipient=recipient_id,
                contract_number=f"ДГ-{RNG.randint(100, 999)}/{2024 + RNG.randint(0, 1)}",
                installation_address=rand_address(),
                movement=movement,
            )
            session.add(client_issue)
            session.flush()

            _apply_issue_relocation(session, products, pool, dst_storage, dst_owner)
            created += 1
            if created % 10 == 0:
                session.commit()
        session.commit()
    print(f"[seed] Видач клієнту: {created}")


def seed_sales(ctx: LookupContext, pool: StockPool, admin_login: str, n: int = 45) -> List[Dict]:
    warehouse_ids = [s["id"] for s in ctx.storages if s["type"] == StorageType.WAREHOUSE]
    completed_sales: List[Dict] = []
    with rx.session() as session:
        created = 0
        for _ in range(n):
            candidates = [pid for pid, u in pool.units.items() if u["storage_id"] in warehouse_ids]
            if not candidates:
                break
            src_storage = RNG.choice(warehouse_ids)
            pids = [pid for pid in candidates if pool.units[pid]["storage_id"] == src_storage]
            if not pids:
                continue
            picked = RNG.sample(pids, k=min(RNG.randint(1, 5), len(pids)))
            products = session.exec(select(Product).where(Product.id.in_(picked))).all()
            if not products:
                continue

            by_catalog: Dict[int, List[Product]] = {}
            for p in products:
                by_catalog.setdefault(p.id_product_catalog, []).append(p)

            src_owner = pool.units[picked[0]]["owner_id"]
            responsible_id = RNG.choice(ctx.worker_ids)

            movement_products_catalog = []
            total_cost = 0.0
            prices: Dict[int, float] = {}
            for cid, units in by_catalog.items():
                meta = next(c for c in ctx.catalog_items if c["id"] == cid)
                price = round(RNG.uniform(20, 3000), 2)
                prices[cid] = price
                line_units = [(u.count or 0, meta["divisible"], meta["capacity"]) for u in units]
                movement_products_catalog.append(
                    MovementProductsCatalog(id_product_catalog=cid, count=len(units), price=price, products=units)
                )
                total_cost += sale_line_cost(price, line_units)

            movement = Movement(
                type=MovementsType.SALE,
                id_user=admin_login,
                id_incoming_storage=src_storage,
                id_incoming_owner=src_owner,
                date=(now_local().date() - timedelta(days=RNG.randint(0, 120))).isoformat(),
                comment="",
                status=MovementsStatus.CLOSED,
                total_cost=round(total_cost, 2),
                products_catalog=movement_products_catalog,
            )
            sale = Sale(id_responsible=responsible_id, movement=movement)
            session.add(sale)
            session.flush()

            for p in products:
                p.is_deleted = True
                session.add(p)
                pool.remove(p.id)

            completed_sales.append({
                "sale_id": sale.id,
                "storage_id": src_storage,
                "owner_id": src_owner,
                "product_ids": [p.id for p in products],
            })
            created += 1
            if created % 10 == 0:
                session.commit()
        session.commit()
    print(f"[seed] Продажів: {created}")
    return completed_sales


def seed_returns(ctx: LookupContext, pool: StockPool, admin_login: str, n: int = 15) -> None:
    """Повернення з площадки/відділу на склад (власник не змінюється)."""
    site_types = (StorageType.TECHNICAL_SITE, StorageType.DEPARTMENT)
    warehouse_ids = [s["id"] for s in ctx.storages if s["type"] == StorageType.WAREHOUSE]
    with rx.session() as session:
        created = 0
        for _ in range(n):
            candidates = [pid for pid, u in pool.units.items() if pool.units[pid]["storage_id"] in
                          {s["id"] for s in ctx.storages if s["type"] in site_types}]
            if not candidates or not warehouse_ids:
                break
            src_storage = pool.units[RNG.choice(candidates)]["storage_id"]
            pids = [pid for pid in candidates if pool.units[pid]["storage_id"] == src_storage]
            picked = RNG.sample(pids, k=min(RNG.randint(1, 3), len(pids)))
            products = session.exec(select(Product).where(Product.id.in_(picked))).all()
            if not products:
                continue

            by_catalog: Dict[int, List[Product]] = {}
            for p in products:
                by_catalog.setdefault(p.id_product_catalog, []).append(p)

            dst_storage = RNG.choice(warehouse_ids)
            movement = Movement(
                type=MovementsType.RETURN,
                id_user=admin_login,
                id_incoming_storage=src_storage,
                id_destination_storage=dst_storage,
                date=(now_local().date() - timedelta(days=RNG.randint(0, 90))).isoformat(),
                comment="Повернення обладнання з об'єкта",
                status=MovementsStatus.CLOSED,
                total_cost=0.0,
                products_catalog=[
                    MovementProductsCatalog(id_product_catalog=cid, count=len(units), products=units)
                    for cid, units in by_catalog.items()
                ],
            )
            session.add(movement)
            session.flush()

            for p in products:
                p.id_storage = dst_storage
                session.add(p)
                pool.relocate(p.id, dst_storage)
            created += 1
            if created % 10 == 0:
                session.commit()
        session.commit()
    print(f"[seed] Повернень з площадок/відділів: {created}")


def seed_sale_returns(ctx: LookupContext, pool: StockPool, admin_login: str, completed_sales: List[Dict], n: int = 12) -> None:
    warehouse_ids = [s["id"] for s in ctx.storages if s["type"] == StorageType.WAREHOUSE]
    if not completed_sales:
        return
    candidates = RNG.sample(completed_sales, k=min(n, len(completed_sales)))
    with rx.session() as session:
        created = 0
        for sale_info in candidates:
            product_ids = sale_info["product_ids"]
            if not product_ids:
                continue
            k = RNG.randint(1, len(product_ids))
            returned_ids = RNG.sample(product_ids, k=k)
            products = session.exec(select(Product).where(Product.id.in_(returned_ids))).all()
            if not products:
                continue

            by_catalog: Dict[int, List[Product]] = {}
            for p in products:
                by_catalog.setdefault(p.id_product_catalog, []).append(p)

            dst_storage = RNG.choice(warehouse_ids)
            owner_id = sale_info["owner_id"]

            movement_products_catalog = []
            total_cost = 0.0
            for cid, units in by_catalog.items():
                compensation = round(RNG.uniform(20, 1500), 2)
                movement_products_catalog.append(
                    MovementProductsCatalog(id_product_catalog=cid, count=len(units), price=compensation, products=units)
                )
                total_cost += compensation

            movement = Movement(
                type=MovementsType.SALE_RETURN,
                id_user=admin_login,
                id_destination_storage=dst_storage,
                id_incoming_owner=owner_id,
                id_destination_owner=owner_id,
                date=(now_local().date() - timedelta(days=RNG.randint(0, 60))).isoformat(),
                comment="Повернення від клієнта",
                status=MovementsStatus.CLOSED,
                total_cost=round(total_cost, 2),
                products_catalog=movement_products_catalog,
            )
            sale_return = SaleReturn(id_sale=sale_info["sale_id"], movement=movement)
            session.add(sale_return)
            session.flush()

            for p in products:
                p.is_deleted = False
                p.id_storage = dst_storage
                p.id_owner = owner_id
                session.add(p)
                meta = next(c for c in ctx.catalog_items if c["id"] == p.id_product_catalog)
                pool.add(p.id, p.id_product_catalog, dst_storage, owner_id, meta)
            created += 1
        session.commit()
    print(f"[seed] Повернень продажу: {created}")


def seed_requests(ctx: LookupContext, admin_login: str, issue_movement_ids: List[int], n: int = 35) -> None:
    warehouse_ids = [s["id"] for s in ctx.storages if s["type"] == StorageType.WAREHOUSE]
    dest_ids = [s["id"] for s in ctx.storages if s["type"] in (StorageType.TECHNICAL_SITE, StorageType.DEPARTMENT)]
    with rx.session() as session:
        created = 0
        for i in range(n):
            req_type = RNG.choice([MovementsType.ISSUE, MovementsType.SALE])
            n_lines = RNG.randint(1, 3)
            chosen = RNG.sample(ctx.catalog_items, k=min(n_lines, len(ctx.catalog_items)))

            positions = []
            for meta in chosen:
                count = RNG.randint(1, 10)
                part = RNG.randint(1, meta["capacity"] - 1) if meta["divisible"] and meta["capacity"] > 1 and RNG.random() < 0.3 else None
                positions.append(RequestProductsCatalog(id_product_catalog=meta["id"], count=count, part_amount=part))

            is_completed = RNG.random() < 0.4
            request = Request(
                type=req_type,
                id_author=admin_login,
                id_responsible=RNG.choice(ctx.worker_ids),
                id_destination_storage=RNG.choice(dest_ids) if dest_ids else None,
                date=(now_local().date() - timedelta(days=RNG.randint(0, 100))).isoformat(),
                comment=RNG.choice(["", "Терміново", "За планом на тиждень", "Уточнити кількість перед видачею"]),
                status=RequestStatus.COMPLETED if (is_completed and issue_movement_ids) else RequestStatus.NEW,
                id_movement=RNG.choice(issue_movement_ids) if (is_completed and issue_movement_ids and req_type == MovementsType.ISSUE) else None,
                products_catalog=positions,
            )
            session.add(request)
            created += 1
            if created % 10 == 0:
                session.flush()
        session.commit()
    print(f"[seed] Заявок: {created}")


# ============================================================================
# main
# ============================================================================

def main() -> None:
    print("=" * 70)
    print("Наповнення TrifleSklad тестовими даними")
    print("=" * 70)

    reset_database()
    info = bootstrap_core()
    ctx = seed_lookup_data(info["admin_worker_id"])

    pool = StockPool()
    seed_admissions(ctx, pool, admin_login="admin", n=90)

    seed_write_offs(ctx, pool, admin_login="admin", n=30)
    seed_relocations(ctx, pool, admin_login="admin", n=35)
    issue_movement_ids = seed_issues(ctx, pool, admin_login="admin", n=35)
    seed_client_issues(ctx, pool, admin_login="admin", n=20)
    completed_sales = seed_sales(ctx, pool, admin_login="admin", n=45)
    seed_returns(ctx, pool, admin_login="admin", n=15)
    seed_sale_returns(ctx, pool, admin_login="admin", completed_sales=completed_sales, n=12)
    seed_requests(ctx, admin_login="admin", issue_movement_ids=issue_movement_ids, n=35)

    print("=" * 70)
    print("Готово! Логін: admin / new_admin")
    print(f"Одиниць ТМЦ у залишках наприкінці: {len(pool.units)}")
    print("=" * 70)


if __name__ == "__main__":
    main()
