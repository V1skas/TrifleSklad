from enum import StrEnum

class Action(StrEnum):
    WORKERS_CREATE = ('workers:create', 'Додавання співробітників', 'Дозволяє додавати співробітників')
    WORKERS_DELETE = ('workers:delete', 'Видалення співробітників', 'Дозволяє видаляти співробітників')
    WORKERS_EDIT = ('workers:edit', 'Редагування співробітників', 'Дозволяє редагувати інформацію про співробітників')
    WORKERS_LIST = ('workers:list', 'Список співробітників', 'Дозволяє переглядати список співробітників')

    def __new__(cls, code: str, title: str, description: str):
        obj = str.__new__(cls, code)
        obj._value_ = code
        obj.title_attr = title 
        obj.description_attr = description
        return obj