from enum import StrEnum


class Action(StrEnum):
    WORKERS_CREATE = ("workers:create", "Додавання співробітників", "Дозволяє додавати співробітників")
    WORKERS_DELETE = ("workers:delete", "Видалення співробітників", "Дозволяє видаляти співробітників")
    WORKERS_EDIT = ("workers:edit", "Редагування співробітників", "Дозволяє редагувати інформацію про співробітників")
    WORKERS_LIST = ("workers:list", "Список співробітників", "Дозволяє переглядати список співробітників")
    WORKERS_VIEW = ("workers:view", "Перегляд співробітників", "Дозволяє переглядати інформацію про співробітників")

    ROLES_CREATE = ("roles:create", "Додавання ролей", "Дозволяє додавати ролі")
    ROLES_DELETE = ("roles:delete", "Видалення ролей", "Дозволяє видаляти роли")
    ROLES_EDIT = ("roles:edit", "Редагування ролей", "Дозволяє редагувати інформацию про роли")
    ROLES_LIST = ("roles:list", "Список ролей", "Дозволяє переглядати список ролей")
    ROLES_VIEW = ("roles:view", "Перегляд ролей", "Дозволяє переглядати информацию про роли")

    USERS_CREATE = ("users:create", "Додавання користувачів", "Дозволяє додавати користувачів")
    USERS_DELETE = ("users:delete", "Видалення користувачів", "Дозволяє видаляти користувачів")
    USERS_EDIT = ("users:edit", "Редагування користувачів", "Дозволяє редагувати інформацію про користувачів")
    USERS_LIST = ("users:list", "Список користувачів", "Дозволяє переглядати список користувачів")
    USERS_VIEW = ("users:view", "Перегляд користувачів", "Дозволяє переглядати інформацію про користувачів")

    CATEGORIES_CREATE = ("categories:create", "Додавання категорій", "Дозволяє додавати категорії")
    CATEGORIES_DELETE = ("categories:delete", "Видалення категорій", "Дозволяє видаляти категорії")
    CATEGORIES_EDIT = ("categories:edit", "Редагування категорій", "Дозволяє редагувати інформацію про категорії")
    CATEGORIES_LIST = ("categories:list", "Список категорій", "Дозволяє переглядати список категорій")
    CATEGORIES_VIEW = ("categories:view", "Перегляд категорій", "Дозволяє переглядати інформацію про категорії")

    OWNERS_CREATE = ("owners:create", "Додавання власників", "Дозволяє додавати власників")
    OWNERS_DELETE = ("owners:delete", "Видалення власників", "Дозволяє видаляти власників")
    OWNERS_EDIT = ("owners:edit", "Редагування власників", "Дозволяє редагувати інформацію про власників")
    OWNERS_LIST = ("owners:list", "Список власників", "Дозволяє переглядати список власників")
    OWNERS_VIEW = ("owners:view", "Перегляд власників", "Дозволяє переглядати інформацію про власників")

    def __new__(cls, code: str, title: str, description: str):
        obj = str.__new__(cls, code)
        obj._value_ = code
        obj.title_attr = title
        obj.description_attr = description
        return obj
