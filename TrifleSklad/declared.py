from typing import Dict, List, Optional, Tuple

class MovementsType:
    ADMISSION = 1
    WRITE_OFF = 2
    MOVEMENT = 3
    ISSUE = 4
    SALE = 5
    RETURN = 6
    SALE_RETURN = 7

movements_type_list: Dict[int, str] = {
    MovementsType.ADMISSION: "Постачання",
    MovementsType.WRITE_OFF: "Списання",
    MovementsType.MOVEMENT: "Переміщення",
    MovementsType.ISSUE: "Видача",
    MovementsType.SALE: "Продаж",
    MovementsType.RETURN: "Повернення",
    MovementsType.SALE_RETURN: "Повернення продажу",
}

class StorageType:
    WAREHOUSE = 1
    TECHNICAL_SITE = 2
    DEPARTMENT = 3

storage_type_list: Dict[int, str] = {StorageType.WAREHOUSE: "Склад",
                     StorageType.TECHNICAL_SITE: "Тех. площадка",
                     StorageType.DEPARTMENT: "Відділ"}

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


def get_status_by_text(text: str) -> Optional[int]:
    for index, status in enumerate(movements_status_list):
        if status == text:
            return index
    else:
        return None