from enum import StrEnum

class Action(StrEnum):
    WORKERS_CREATE = ('workers:create', 'Додавання співробітників', 'Дозволяє додавати співробітників')
    WORKERS_DELETE = ('workers:delete', 'Видалення співробітників', 'Дозволяє видаляти співробітників')
    WORKERS_EDIT = ('workers:edit', 'Редагування співробітників', 'Дозволяє редагувати інформацію про співробітників')
    WORKERS_LIST = ('workers:list', 'Список співробітників', 'Дозволяє переглядати список співробітників')
    WORKERS_VIEW = ('workers:view', 'Перегляд співробітників', 'Дозволяє переглядати інформацію про співробітників')

    ROLES_CREATE = ('roles:create', 'Додавання ролей', 'Дозволяє додавати ролі')
    ROLES_DELETE = ('roles:delete', 'Видалення ролей', 'Дозволяє видаляти роли')
    ROLES_EDIT = ('roles:edit', 'Редагування ролей', 'Дозволяє редагувати інформацию про роли')
    ROLES_LIST = ('roles:list', 'Список ролей', 'Дозволяє переглядати список ролей')
    ROLES_VIEW = ('roles:view', 'Перегляд ролей', 'Дозволяє переглядати информацию про роли')

    USERS_CREATE = ('users:create', 'Додавання користувачів', 'Дозволяє додавати користувачів')
    USERS_DELETE = ('users:delete', 'Видалення користувачів', 'Дозволяє видаляти користувачів')
    USERS_EDIT = ('users:edit', 'Редагування користувачів', 'Дозволяє редагувати інформацію про користувачів')
    USERS_LIST = ('users:list', 'Список користувачів', 'Дозволяє переглядати список користувачів')
    USERS_VIEW = ('users:view', 'Перегляд користувачів', 'Дозволяє переглядати інформацію про користувачів')

    def __new__(cls, code: str, title: str, description: str):
        obj = str.__new__(cls, code)
        obj._value_ = code
        obj.title_attr = title 
        obj.description_attr = description
        return obj