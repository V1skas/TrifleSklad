from typing import List, Optional

from sqlmodel import Field, Relationship

import reflex as rx


class RolesActions(rx.Model, table=True):
    __tablename__ = "roles_actions" # type: ignore

    # Table columns
    role_id: int = Field(default=None, foreign_key="roles.id", primary_key=True)
    action_id: int = Field(default=None, foreign_key="actions.id", primary_key=True)


class UsersActions(rx.Model, table=True):
    __tablename__ = "users_actions" # type: ignore

    # Table columns
    id_user: str = Field(default=None, foreign_key="users.login", primary_key=True)
    id_action: int = Field(default=None, foreign_key="actions.id", primary_key=True)


class UsersRoles(rx.Model, table=True):
    __tablename__ = "users_roles" # type: ignore

    # Table columns
    id_user: str = Field(default=None, foreign_key="users.login", primary_key=True)
    id_role: int = Field(default=None, foreign_key="roles.id", primary_key=True)


class Role(rx.Model, table=True):
    __tablename__ = "roles" # type: ignore

    # Table columns
    id: int = Field(primary_key=True) # type: ignore
    title: str = Field(default=None, nullable=False)
    description: Optional[str] = Field(nullable=True)

    # Relationships
    actions: Optional[List['Action']] = Relationship(link_model=RolesActions)
    #users: Optional[List['User']] = Relationship(back_populates="roles", link_model=UsersRoles)


class Action(rx.Model, table=True):
    __tablename__ = "actions" # type: ignore

    # Table columns
    id: int = Field(primary_key=True) # type: ignore
    code: str = Field(default=None, nullable=False, unique=True)
    title: str = Field(default=None, nullable=False)
    description: Optional[str] = Field(nullable=True)

    # Relationships
    #roles: Optional[List['Role']] = Relationship(link_model=RolesActions)
    #users: Optional[List['User']] = Relationship(back_populates="actions", link_model=UsersActions)


class AuthToken(rx.Model, table=True):
    __tablename__ = "auth_tokens" # type: ignore

    # Table columns
    id: int = Field(primary_key=True, nullable=True) # type: ignore
    token: str = Field(nullable=False, unique=True)
    id_user: str = Field(foreign_key="users.login", nullable=False)

    # Relationships
    user: Optional['User'] = Relationship(back_populates="auth_tokens")


class User(rx.Model, table=True):
    __tablename__ = "users" # type: ignore

    # Table columns
    login: str = Field(primary_key=True)
    id_worker: int = Field(default=None, foreign_key="workers.id")
    salt: str = Field(nullable=False)
    password_hash: str = Field(nullable=False)
    is_deleted: bool = Field(default=False, nullable=False)

    # Relationships
    actions: Optional[List[Action]] = Relationship(link_model=UsersActions)
    roles: Optional[List[Role]] = Relationship(link_model=UsersRoles)
    worker: Optional['Worker'] = Relationship()
    auth_tokens: Optional[List[AuthToken]] = Relationship(back_populates="user")


class Worker(rx.Model, table=True):
    __tablename__ = "workers" # type: ignore

    # Table columns
    id: int = Field(primary_key=True) # type: ignore
    fio: str = Field(default="", nullable=False)
    phone_number: Optional[str] = Field(nullable=True)
    email: Optional[str] = Field(nullable=True)
    position: Optional[str] = Field(nullable=True)
    is_deleted: bool = Field(default=False, nullable=False)

    # Relationships
    #user: Optional[User] = Relationship(back_populates="worker")
    storages: Optional[List['Storage']] = Relationship(back_populates="responsible")
    issues: Optional[List['Issue']] = Relationship(back_populates="recipient")
    sales: Optional[List['Sale']] = Relationship(back_populates="responsible")


class ProductCategory(rx.Model, table=True):
    __tablename__ = "product_categories" # type: ignore

    # Table columns
    id: int = Field(primary_key=True) # type: ignore
    title: str = Field(default="", nullable=False)
    description: Optional[str] = Field(nullable=True)
    #id_parrent: Optional[int] = Field(default=None, foreign_key="product_categories.id", nullable=True)
    is_deleted: bool = Field(default=False, nullable=False)

    # Relationships
    products: Optional[List['ProductCatalog']] = Relationship(back_populates="category")


class ProductCatalog(rx.Model, table=True):
    __tablename__ = "products_catalog" # type: ignore

    # Table columns
    id: int = Field(primary_key=True) # type: ignore
    title: str = Field(default="", nullable=False)
    description: Optional[str] = Field(nullable=True)
    id_category: Optional[int] = Field(default=None, foreign_key="product_categories.id")
    unit: str = Field(default="", nullable=False)
    divisible: bool = Field(default=False, nullable=False)
    uniq: bool = Field(default=False, nullable=False)
    capacity: int = Field(default=0, nullable=False)
    count: float = Field(default=0, nullable=False)
    is_deleted: bool = Field(default=False, nullable=False)

    # Relationships
    category: Optional[ProductCategory] = Relationship(back_populates="products")
    products: Optional[List['Product']] = Relationship(back_populates="product_catalog")


class Owner(rx.Model, table=True):
    __tablename__ = "owners" # type: ignore

    # Table columns
    id: int = Field(primary_key=True) # type: ignore
    title: str = Field(default="", nullable=False)
    description: Optional[str] = Field(nullable=True)
    is_deleted: bool = Field(default=False, nullable=False)

    # Relationships
    owner: Optional[List['Product']] = Relationship(back_populates="owner")
    products: Optional[List['Product']] = Relationship(back_populates="owner")

class Supplier(rx.Model, table=True):
    __tablename__ = "suppliers" # type: ignore

    # Table columns
    id: int = Field(primary_key=True) # type: ignore
    title: str = Field(default="", nullable=False)
    description: Optional[str] = Field(nullable=True)
    address: str = Field(default="", nullable=False)
    email: str = Field(default="", nullable=False)
    contact_person: str = Field(default="", nullable=False)
    contact_phone: str = Field(default="", nullable=False)
    edrpou: str = Field(default="", nullable=False)
    is_deleted: bool = Field(default=False, nullable=False)

    # Relationships
    admissions: Optional[List['Admission']] = Relationship(back_populates="supplier")

class Storage(rx.Model, table=True):
    __tablename__ = "storages" # type: ignore

    # Table columns
    id: int = Field(primary_key=True) # type: ignore
    type: int = Field(nullable=False)
    title: str = Field(nullable=False)
    description: Optional[str] = Field(nullable=True)
    address: str = Field(default="", nullable=False)
    id_responsible: int = Field(default=0, nullable=False, foreign_key="workers.id")
    is_deleted: bool = Field(default=False, nullable=False)

    # Relationships
    responsible: Optional[Worker] = Relationship(back_populates="storages")
    products: Optional[List['Product']] = Relationship(back_populates="storage")


class Product(rx.Model, table=True):
    __tablename__ = "products"

    # Table columns
    id: int = Field(primary_key=True)
    serial_number: str = Field(nullable=True)
    id_product_catalog: int = Field(foreign_key="products_catalog.id", nullable=False)
    id_storage: int = Field(foreign_key="storages.id", nullable=False)
    id_owner: int = Field(foreign_key="owners.id", nullable=False)
    count: int = Field(default=1, nullable=False)
    is_deleted: bool = Field(default=False, nullable=False)

    # Relationship
    product_catalog: Optional[ProductCatalog] = Relationship(back_populates="products")
    storage: Optional[Storage] = Relationship(back_populates="products")
    owner: Optional[Owner] = Relationship(back_populates="products")


class MovementProducts(rx.Model, table=True):
    __tablename__ = "movements_products"

    # Table columns
    id_movement_product: int = Field(primary_key=True, foreign_key="movements_products_catalog.id")
    id_product: int = Field(primary_key=True, foreign_key="products.id")


class Movement(rx.Model, table=True):
    __tablename__ = "movements"

    # Table columns
    id: int = Field(primary_key=True)
    type: int = Field(nullable=False)
    id_user: str = Field(foreign_key="users.login", nullable=False)
    id_incoming_storage: int = Field(foreign_key="storages.id", nullable=True)
    id_destination_storage: int = Field(foreign_key="storages.id", nullable=True)
    id_incoming_owner: int = Field(foreign_key="owners.id", nullable=True)
    id_destination_owner: int = Field(foreign_key="owners.id", nullable=True)
    date: str = Field(nullable=False)
    comment: str = Field(nullable=True)
    status: int = Field(nullable=False)
    total_cost: float = Field(nullable=True)

    # Relationship
    products_catalog: Optional[List['MovementProductsCatalog']] = Relationship() # Relationship(back_populates="movement")
    incoming_storage: Optional['Storage'] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "Movement.id_incoming_storage"}
    )
    destination_storage: Optional['Storage'] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "Movement.id_destination_storage"}
    )
    incoming_owner: Optional['Owner'] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "Movement.id_incoming_owner"}
    )
    destination_owner: Optional['Owner'] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "Movement.id_destination_owner"}
    )


class MovementProductsCatalog(rx.Model, table=True):
    __tablename__ = "movements_products_catalog"

    # Table columns
    id: int = Field(primary_key=True)
    id_movement: int = Field(foreign_key="movements.id", nullable=False)
    id_product_catalog: int = Field(foreign_key="products_catalog.id", nullable=False)
    count: int = Field(default=0, nullable=False)
    price: float = Field(default=0.0, nullable=False)

    # Relationship
    # movement: Optional[Movement] = Relationship(back_populates="products_catalog")
    products: Optional[List[Product]] = Relationship(link_model=MovementProducts)
    product: Optional[ProductCatalog] = Relationship()


class PaymentType(rx.Model, table=True):
    __tablename__ = "payment_types"

    # Table columns
    id: int = Field(primary_key=True)
    title: str = Field(nullable=False, unique=True)
    description: Optional[str] = Field(nullable=True)
    is_deleted: bool = Field(default=False, nullable=False)

    # Relationships


class NDSRate(rx.Model, table=True):
    __tablename__ = "nds_rates"

    # Table columns
    id: int = Field(primary_key=True)
    title: str = Field(nullable=False, unique=True)
    rate: float = Field(default=0.0, nullable=False)
    description: Optional[str] = Field(nullable=True)
    is_deleted: bool = Field(default=False, nullable=False)


class Admission(rx.Model, table=True):
    __tablename__ = "admissions"

    # Table columns
    id: int = Field(primary_key=True, foreign_key="movements.id", default=None)
    id_payment_type: int = Field(nullable=False, foreign_key="payment_types.id")
    id_supplier: int = Field(foreign_key="suppliers.id", nullable=False)
    flag_nds: bool = Field(default=False, nullable=False)
    id_nds_rate: Optional[int] = Field(default=None, foreign_key="nds_rates.id", nullable=True)
    dollar_rate: float = Field(default=0.0, nullable=False)
    invoice_number: Optional[str] = Field(default=None, nullable=True)

    # Relationship
    supplier: Optional[Supplier] = Relationship(back_populates="admissions")
    movement: Optional[Movement] = Relationship()
    payment_type: Optional[PaymentType] = Relationship()
    nds_rate: Optional[NDSRate] = Relationship()


class Issue(rx.Model, table=True):
    __tablename__ = "issues"

    # Table columns
    id: int = Field(primary_key=True, foreign_key="movements.id")
    id_recipient: int = Field(foreign_key="workers.id", nullable=False)

    # Relationship
    recipient: Optional[Worker] = Relationship(back_populates="issues")
    movement: Optional[Movement] = Relationship()


class Sale(rx.Model, table=True):
    __tablename__ = "sales"

    # Table columns
    id: int = Field(primary_key=True, foreign_key="movements.id")
    id_responsible: int = Field(foreign_key="workers.id", nullable=False)

    # Relationship
    responsible: Optional[Worker] = Relationship(back_populates="sales")
    movement: Optional[Movement] = Relationship()