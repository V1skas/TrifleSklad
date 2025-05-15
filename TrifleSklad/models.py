from typing import List, Optional

from sqlmodel import Field, Relationship

import reflex as rx


class RolesActions(rx.Model, table=True):
    __tablename__ = "roles_actions"

    # Table columns
    role_id: int = Field(default=None, foreign_key="roles.id", primary_key=True)
    action_id: str = Field(default=None, foreign_key="actions.id", primary_key=True)


class UsersActions(rx.Model, table=True):
    __tablename__ = "users_actions"

    # Table columns
    id_user: str = Field(default=None, foreign_key="users.login", primary_key=True)
    id_action: str = Field(default=None, foreign_key="actions.id", primary_key=True)

class UsersRoles(rx.Model, table=True):
    __tablename__ = "users_roles"

    # Table columns
    id_user: int = Field(default=None, foreign_key="users.login", primary_key=True)
    id_role: int = Field(default=None, foreign_key="roles.id", primary_key=True)


class Role(rx.Model, table=True):
    __tablename__ = "roles"

    # Table columns
    id: int = Field(primary_key=True)
    title: str
    description: str = ""

    # Relationships
    actions: Optional[List['Action']] = Relationship(back_populates="roles", link_model=RolesActions)
    users: Optional[List['User']] = Relationship(back_populates="roles", link_model=UsersRoles)


class Action(rx.Model, table=True):
    __tablename__ = "actions"

    # Table columns
    id: str = Field(primary_key=True)
    title: str
    description: Optional[str]

    # Relationships
    roles: Optional[List['Role']] = Relationship(back_populates="actions", link_model=RolesActions)
    users: Optional[List['User']] = Relationship(back_populates="actions", link_model=UsersActions)


class User(rx.Model, table=True):
    __tablename__ = "users"

    # Table columns
    login: str = Field(primary_key=True)
    id_worker: int = Field(default=None, foreign_key="workers.id")
    salt: str
    password_hash: str
    is_deleted: bool = False

    # Relationships
    actions: Optional[List[Action]] = Relationship(back_populates="users", link_model=UsersActions)
    roles: Optional[List[Role]] = Relationship(back_populates="users", link_model=UsersRoles)
    worker: Optional['Worker'] = Relationship(back_populates="user")


class Worker(rx.Model, table=True):
    __tablename__ = "workers"

    # Table columns
    id: int = Field(primary_key=True)
    fio: str
    phone_number: str
    email: str
    id_position: int = Field(default=None, foreign_key="positions.id")
    is_deleted: bool = False

    # Relationships
    user: Optional[User] = Relationship(back_populates="worker")
    position: Optional['Position'] = Relationship(back_populates="workers")


class Position(rx.Model, table=True):
    __tablename__ = "positions"

    # Table columns
    id: int = Field(primary_key=True)
    title: str
    id_deleted: bool = False

    # Relationships
    workers: Optional[List[Worker]] = Relationship(back_populates="position")