"""Реэкспорт-шим: канонічне місце — `TrifleSklad.states.app`.

Лишається, поки всі ~100 state-класів секцій не перейдуть на прямий імпорт
з `TrifleSklad.states.app` (фази 6-9); тоді цей файл видаляється.
"""

from TrifleSklad.states.app import AppState, route_param

__all__ = ["AppState", "route_param"]
