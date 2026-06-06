from typing import Dict, List, Optional

class MovementsType:
    ADMISSION = 1
    WRITE_OFF = 2
    MOVEMENT = 3
    ISSUE = 4
    SALE = 5

movements_type_list: Dict[int, str] = {
    MovementsType.ADMISSION: "Постачання",
    MovementsType.WRITE_OFF: "Списання",
    MovementsType.MOVEMENT: "Переміщення",
    MovementsType.ISSUE: "Видача",
    MovementsType.SALE: "Продаж",
}

class StorageType:
    WAREHOUSE = 1
    TECHNICAL_SITE = 2

storage_type_list: Dict[int, str] = {StorageType.WAREHOUSE: "Склад",
                     StorageType.TECHNICAL_SITE: "Тех. площадка"}

class MovementsStatus:
    CREATED = 0
    IN_PROGRESS = 1
    CLOSED = 2
    CANCELED = 3

movements_status_list: List[str] = ["Створено", "В роботі", "Закрито", "Скасовано"]

def get_status_by_text(text: str) -> Optional[int]:
    for index, status in enumerate(movements_status_list):
        if status == text:
            return index
    else:
        return None