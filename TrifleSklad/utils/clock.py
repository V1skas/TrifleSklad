"""Єдине джерело «поточного часу» для застосунку.

Проблема: `datetime.now()`/`date.today()` віддають час у таймзоні процесу.
На сервері застосунок може працювати у контейнері з таймзоною UTC за
замовчуванням, тому дати рухів ТМЦ зберігались і показувались би не в
локальному київському часі.

Рішення: скрізь, де потрібне «сьогодні»/«зараз», використовуємо `now_local()`
замість `datetime.now()`/`date.today()`. Прив'язаний до явної зони
`Europe/Kyiv` (з автопереходом на літній/зимовий час) і не залежить від
таймзони ОС/контейнера. Пакет `tzdata` у залежностях гарантує наявність зони
навіть у мінімальних контейнерах.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

try:
    LOCAL_TZ = ZoneInfo("Europe/Kyiv")
except Exception:  # застаріла база tzdata ще може мати лише стару назву
    LOCAL_TZ = ZoneInfo("Europe/Kiev")


def now_local() -> datetime:
    """Поточний момент у київському часі (EET/EEST) як naive datetime.

    Повертаємо naive навмисно: колонки БД у проєкті — timezone-naive, дата
    руху зберігається як рядок ISO (`date.isoformat()`). Заміняє
    `datetime.now()`/`date.today()` по всьому застосунку."""
    return datetime.now(LOCAL_TZ).replace(tzinfo=None)
