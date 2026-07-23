from typing import Dict, List, Optional, Tuple

# Скільки днів після дати поставки дозволено редагувати перелік ТМЦ (за
# наявності права admissions:edit_products і відсутності конфліктів із
# пізнішими рухами — див. AdmissionDAO.can_edit_products).
ADMISSION_PRODUCTS_EDIT_WINDOW_DAYS = 30

# Тривалість ковзного вікна сесії (хвилини): скільки часу токен лишається
# дійсним після останньої активності (продовжується при кожному require_auth,
# див. services/auth.py). Поки константа; перенести в key/value-налаштування
# (blueprint §9.8) — опціональна пост-фаза.
SESSION_TIMEOUT_MINUTES = 60

class MovementsType:
    ADMISSION = 1
    WRITE_OFF = 2
    MOVEMENT = 3
    ISSUE = 4
    SALE = 5
    RETURN = 6
    SALE_RETURN = 7
    CLIENT_ISSUE = 8

movements_type_list: Dict[int, str] = {
    MovementsType.ADMISSION: "Постачання",
    MovementsType.WRITE_OFF: "Списання",
    MovementsType.MOVEMENT: "Переміщення",
    MovementsType.ISSUE: "Видача",
    MovementsType.SALE: "Продаж",
    MovementsType.RETURN: "Повернення",
    MovementsType.SALE_RETURN: "Повернення продажу",
    MovementsType.CLIENT_ISSUE: "Видача клієнту",
}

class StorageType:
    WAREHOUSE = 1
    TECHNICAL_SITE = 2
    DEPARTMENT = 3
    CLIENT = 4

storage_type_list: Dict[int, str] = {StorageType.WAREHOUSE: "Склад",
                     StorageType.TECHNICAL_SITE: "Тех. площадка",
                     StorageType.DEPARTMENT: "Відділ",
                     StorageType.CLIENT: "Клієнт"}

class MovementsStatus:
    CREATED = 0
    IN_PROGRESS = 1
    CLOSED = 2
    CANCELED = 3

movements_status_list: List[str] = ["Створено", "В роботі", "Закрито", "Скасовано"]


class RequestStatus:
    NEW = 0
    COMPLETED = 1

request_status_list: List[str] = ["Нова", "Виконана"]

def format_amount(value) -> str:
    """Число без зайвого «.0» для цілих значень: 100.0 → «100», 0.75 → «0.75».
    Використовується для дробової ємності одиниці (Product.count)."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "0"
    return str(int(number)) if number == int(number) else str(number)


def format_request_qty(count: int, part: Optional[int], unit: str = "") -> str:
    """Людиночитний опис кількості позиції заявки: цілі одиниці та/або частина
    (для подільного ТМЦ). Напр. «2 ціл. + 30 м», «1 ціл.», «30 м»."""
    chunks: List[str] = []
    if count and count > 0:
        chunks.append(f"{count} ціл.")
    if part:
        chunks.append(f"{part} {unit}".strip())
    return " + ".join(chunks) if chunks else "0"


def sale_line_cost(price: float, units: List[Tuple[int, bool, int]]) -> float:
    """Вартість позиції продажу. Ціна трактується як вартість за цілу одиницю
    (повну ємність). Для подільної одиниці з залишком `count` із ємності
    `capacity` внесок = price * count/capacity (частина оплачується пропорційно),
    для неподільної (або без ємності) — price за одиницю.
    units = [(count, divisible, capacity), ...]."""
    total = 0.0
    for count, divisible, capacity in units:
        if divisible and capacity and capacity > 0:
            total += price * (count / capacity)
        else:
            total += price
    return round(total, 2)


def generate_serial_range(
    mask: str, start: str, end: str, count: int, is_hex: bool = False
) -> Tuple[Optional[List[str]], Optional[str]]:
    """Генерує список серійних номерів за маскою з одним входженням "{n}" та
    діапазоном [start, end]. За замовчуванням — десяткові числа; is_hex=True —
    шістнадцяткові (0-9A-F), як прийнято для серійних номерів. Ширина
    нуль-паддінгу — за довжиною рядка `end` (напр. end="050" -> "001".."050",
    end="0F" -> "0A".."0F"). Повертає (список, None) при успіху або
    (None, повідомлення_помилки)."""
    if mask.count("{n}") != 1:
        return None, "Маска повинна містити рівно одне входження {n}!"
    start_s, end_s = start.strip(), end.strip()
    base = 16 if is_hex else 10
    try:
        start_n = int(start_s, base)
        end_n = int(end_s, base)
    except ValueError:
        kind = "шістнадцятковими" if is_hex else "цілими"
        return None, f"Початок і кінець діапазону мають бути {kind} числами!"
    if end_n < start_n:
        return None, "Кінець діапазону не може бути меншим за початок!"
    total = end_n - start_n + 1
    if total != count:
        return None, f"Діапазон містить {total} номер(ів), а потрібно заповнити {count}!"
    width = len(end_s)
    if is_hex:
        values = [format(n, "X").zfill(width) for n in range(start_n, end_n + 1)]
    else:
        values = [str(n).zfill(width) for n in range(start_n, end_n + 1)]
    return [mask.replace("{n}", v) for v in values], None


def get_status_by_text(text: str) -> Optional[int]:
    for index, status in enumerate(movements_status_list):
        if status == text:
            return index
    else:
        return None