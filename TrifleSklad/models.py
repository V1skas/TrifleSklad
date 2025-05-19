from typing import List, Optional

from sqlmodel import Field, Relationship

import reflex as rx


class RolesActions(rx.Model, table=True):
    __tablename__ = "roles_actions" # type: ignore

    # Table columns
    role_id: int = Field(default=None, foreign_key="roles.id", primary_key=True)
    action_id: str = Field(default=None, foreign_key="actions.id", primary_key=True)


class UsersActions(rx.Model, table=True):
    __tablename__ = "users_actions" # type: ignore

    # Table columns
    id_user: str = Field(default=None, foreign_key="users.login", primary_key=True)
    id_action: str = Field(default=None, foreign_key="actions.id", primary_key=True)

class UsersRoles(rx.Model, table=True):
    __tablename__ = "users_roles" # type: ignore

    # Table columns
    id_user: int = Field(default=None, foreign_key="users.login", primary_key=True)
    id_role: int = Field(default=None, foreign_key="roles.id", primary_key=True)


class Role(rx.Model, table=True):
    __tablename__ = "roles" # type: ignore

    # Table columns
    id: int = Field(primary_key=True) # type: ignore
    title: str = Field(default=None, nullable=False)
    description: Optional[str] = Field(nullable=True)

    # Relationships
    actions: Optional[List['Action']] = Relationship(back_populates="roles", link_model=RolesActions)
    users: Optional[List['User']] = Relationship(back_populates="roles", link_model=UsersRoles)


class Action(rx.Model, table=True):
    __tablename__ = "actions" # type: ignore

    # Table columns
    id: str = Field(primary_key=True) # type: ignore
    title: str = Field(default=None, )
    description: Optional[str] = Field(nullable=True)

    # Relationships
    roles: Optional[List['Role']] = Relationship(back_populates="actions", link_model=RolesActions)
    users: Optional[List['User']] = Relationship(back_populates="actions", link_model=UsersActions)


class User(rx.Model, table=True):
    __tablename__ = "users" # type: ignore

    # Table columns
    login: str = Field(primary_key=True)
    id_worker: int = Field(default=None, foreign_key="workers.id")
    salt: str = Field(nullable=False)
    password_hash: str = Field(nullable=False)
    is_deleted: bool = Field(default=False, nullable=False)

    # Relationships
    actions: Optional[List[Action]] = Relationship(back_populates="users", link_model=UsersActions)
    roles: Optional[List[Role]] = Relationship(back_populates="users", link_model=UsersRoles)
    worker: Optional['Worker'] = Relationship(back_populates="user")


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
    user: Optional[User] = Relationship(back_populates="worker")


class ProductCategory(rx.Model, table=True):
    __tablename__ = "product_categories" # type: ignore

    # Table columns
    id: int = Field(primary_key=True) # type: ignore
    title: str = Field(default="", nullable=False)
    description: Optional[str] = Field(nullable=True)
    id_parrent: Optional[int] = Field(default=None, foreign_key="product_categories.id", nullable=True)
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
    capacity: int = Field(default=0, nullable=False)
    count: float = Field(default=0, nullable=False)
    is_deleted: bool = Field(default=False, nullable=False)

    # Relationships
    category: Optional[ProductCategory] = Relationship(back_populates="products")
