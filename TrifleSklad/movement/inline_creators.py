"""Спільний міксин для inline-створення довідкових даних прямо з форм руху ТМЦ.

Замість того, щоб залишати форму руху по новий запис довідника (постачальник,
власник, тип оплати, ставка ПДВ, склад, співробітник) і втрачати введене,
кожен `Add*State` підмішує `LookupCreatorsMixin` — це додає діалоги створення з
авто-вибором створеного запису в потрібному селекті.

Патерн повторює `MovementListFilterMixin` (movement/list_mixin.py): один міксин,
поля неймспейсяться префіксами, щоб не конфліктувати між сутностями. Кожен
`create_*()` після успішного збереження викликає hook `_after_create_<entity>`,
який host-стан перевизначає (перезавантажує свій список + підставляє новий id у
поле `self.item`). За замовчуванням hook — порожній (no-op).
"""

from typing import List, Tuple

import reflex as rx

from TrifleSklad.actions import Action as ActionEnum
from TrifleSklad.dao import (
    NDSRateDAO,
    OwnerDAO,
    PaymentTypeDAO,
    StorageDAO,
    SupplierDAO,
    WorkerDAO,
)
from TrifleSklad.declared import StorageType, storage_type_list
from TrifleSklad.models import NDSRate, Owner, PaymentType, Storage, Supplier
from TrifleSklad.state import AppState


class LookupCreatorsMixin(rx.State, mixin=True):
    # ──────────────────────────────────────────────────────────────────────
    # Постачальник
    # ──────────────────────────────────────────────────────────────────────
    supplier_create_open: bool = False
    sup_title: str = ""
    sup_description: str = ""
    sup_address: str = ""
    sup_email: str = ""
    sup_contact_person: str = ""
    sup_contact_phone: str = ""
    sup_edrpou: str = ""

    def _reset_supplier_form(self):
        self.sup_title = ""
        self.sup_description = ""
        self.sup_address = ""
        self.sup_email = ""
        self.sup_contact_person = ""
        self.sup_contact_phone = ""
        self.sup_edrpou = ""

    @rx.event
    def open_supplier_create(self):
        self._reset_supplier_form()
        self.supplier_create_open = True

    @rx.event
    def set_supplier_create_open(self, value: bool):
        self.supplier_create_open = value

    @rx.event
    def on_change_sup_title(self, value: str):
        self.sup_title = value

    @rx.event
    def on_change_sup_description(self, value: str):
        self.sup_description = value

    @rx.event
    def on_change_sup_address(self, value: str):
        self.sup_address = value

    @rx.event
    def on_change_sup_email(self, value: str):
        self.sup_email = value

    @rx.event
    def on_change_sup_contact_person(self, value: str):
        self.sup_contact_person = value

    @rx.event
    def on_change_sup_contact_phone(self, value: str):
        self.sup_contact_phone = value

    @rx.event
    def on_change_sup_edrpou(self, value: str):
        self.sup_edrpou = value

    def _after_create_supplier(self, new_id: int):
        # Host перевизначає: перезавантажити список + підставити new_id.
        pass

    @rx.event
    async def create_supplier(self):
        if not (await self.get_state(AppState)).has_permission(ActionEnum.SUPPLIERS_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        if self.sup_title.strip() == "":
            return rx.toast.error("Вкажіть назву постачальника!")
        supplier = Supplier(
            title=self.sup_title.strip(),
            description=self.sup_description.strip() or None,
            address=self.sup_address.strip(),
            email=self.sup_email.strip(),
            contact_person=self.sup_contact_person.strip(),
            contact_phone=self.sup_contact_phone.strip(),
            edrpou=self.sup_edrpou.strip(),
        )
        flag, text, new_id = SupplierDAO.add_one(supplier)
        if not flag:
            return rx.toast.error(text)
        self.supplier_create_open = False
        self._after_create_supplier(new_id)
        return rx.toast.success("Постачальника створено та обрано!")

    # ──────────────────────────────────────────────────────────────────────
    # Власник
    # ──────────────────────────────────────────────────────────────────────
    owner_create_open: bool = False
    owner_title: str = ""
    owner_description: str = ""
    # Слот, для якого створюється власник (напр. "incoming"/"destination" у
    # переміщенні). Порожній — для секцій з єдиним селектом власника.
    owner_slot: str = ""

    def _reset_owner_form(self):
        self.owner_title = ""
        self.owner_description = ""

    @rx.event
    def open_owner_create(self, slot: str = ""):
        self._reset_owner_form()
        self.owner_slot = slot
        self.owner_create_open = True

    @rx.event
    def set_owner_create_open(self, value: bool):
        self.owner_create_open = value

    @rx.event
    def on_change_owner_title(self, value: str):
        self.owner_title = value

    @rx.event
    def on_change_owner_description(self, value: str):
        self.owner_description = value

    def _after_create_owner(self, new_id: int):
        pass

    @rx.event
    async def create_owner(self):
        if not (await self.get_state(AppState)).has_permission(ActionEnum.OWNERS_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        if self.owner_title.strip() == "":
            return rx.toast.error("Вкажіть назву власника!")
        owner = Owner(
            title=self.owner_title.strip(),
            description=self.owner_description.strip() or None,
        )
        flag, text, new_id = OwnerDAO.add_one(owner)
        if not flag:
            return rx.toast.error(text)
        self.owner_create_open = False
        self._after_create_owner(new_id)
        return rx.toast.success("Власника створено та обрано!")

    # ──────────────────────────────────────────────────────────────────────
    # Тип оплати
    # ──────────────────────────────────────────────────────────────────────
    payment_type_create_open: bool = False
    pt_title: str = ""
    pt_description: str = ""

    def _reset_payment_type_form(self):
        self.pt_title = ""
        self.pt_description = ""

    @rx.event
    def open_payment_type_create(self):
        self._reset_payment_type_form()
        self.payment_type_create_open = True

    @rx.event
    def set_payment_type_create_open(self, value: bool):
        self.payment_type_create_open = value

    @rx.event
    def on_change_pt_title(self, value: str):
        self.pt_title = value

    @rx.event
    def on_change_pt_description(self, value: str):
        self.pt_description = value

    def _after_create_payment_type(self, new_id: int):
        pass

    @rx.event
    async def create_payment_type(self):
        if not (await self.get_state(AppState)).has_permission(ActionEnum.PAYMENT_TYPE_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        if self.pt_title.strip() == "":
            return rx.toast.error("Вкажіть назву типу оплати!")
        payment_type = PaymentType(
            title=self.pt_title.strip(),
            description=self.pt_description.strip() or None,
        )
        flag, text, new_id = PaymentTypeDAO.add_one(payment_type)
        if not flag:
            return rx.toast.error(text)
        self.payment_type_create_open = False
        self._after_create_payment_type(new_id)
        return rx.toast.success("Тип оплати створено та обрано!")

    # ──────────────────────────────────────────────────────────────────────
    # Ставка ПДВ
    # ──────────────────────────────────────────────────────────────────────
    nds_rate_create_open: bool = False
    nds_title: str = ""
    nds_rate_value: str = "0"
    nds_description: str = ""

    def _reset_nds_rate_form(self):
        self.nds_title = ""
        self.nds_rate_value = "0"
        self.nds_description = ""

    @rx.event
    def open_nds_rate_create(self):
        self._reset_nds_rate_form()
        self.nds_rate_create_open = True

    @rx.event
    def set_nds_rate_create_open(self, value: bool):
        self.nds_rate_create_open = value

    @rx.event
    def on_change_nds_title(self, value: str):
        self.nds_title = value

    @rx.event
    def on_change_nds_rate_value(self, value: str):
        self.nds_rate_value = value

    @rx.event
    def on_change_nds_description(self, value: str):
        self.nds_description = value

    def _after_create_nds_rate(self, new_id: int):
        pass

    @rx.event
    async def create_nds_rate(self):
        if not (await self.get_state(AppState)).has_permission(ActionEnum.NDS_RATES_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        if self.nds_title.strip() == "":
            return rx.toast.error("Вкажіть назву ставки ПДВ!")
        try:
            rate = float(self.nds_rate_value) if self.nds_rate_value.strip() != "" else 0.0
        except ValueError:
            return rx.toast.error("Невірне значення ставки!")
        nds_rate = NDSRate(
            title=self.nds_title.strip(),
            rate=rate,
            description=self.nds_description.strip() or None,
        )
        flag, text, new_id = NDSRateDAO.add_one(nds_rate)
        if not flag:
            return rx.toast.error(text)
        self.nds_rate_create_open = False
        self._after_create_nds_rate(new_id)
        return rx.toast.success("Ставку ПДВ створено та обрано!")

    # ──────────────────────────────────────────────────────────────────────
    # Співробітник
    # ──────────────────────────────────────────────────────────────────────
    worker_create_open: bool = False
    wrk_fio: str = ""
    wrk_phone_number: str = ""
    wrk_email: str = ""
    wrk_position: str = ""

    def _reset_worker_form(self):
        self.wrk_fio = ""
        self.wrk_phone_number = ""
        self.wrk_email = ""
        self.wrk_position = ""

    @rx.event
    def open_worker_create(self):
        self._reset_worker_form()
        self.worker_create_open = True

    @rx.event
    def set_worker_create_open(self, value: bool):
        self.worker_create_open = value

    @rx.event
    def on_change_wrk_fio(self, value: str):
        self.wrk_fio = value

    @rx.event
    def on_change_wrk_phone_number(self, value: str):
        self.wrk_phone_number = value

    @rx.event
    def on_change_wrk_email(self, value: str):
        self.wrk_email = value

    @rx.event
    def on_change_wrk_position(self, value: str):
        self.wrk_position = value

    def _after_create_worker(self, new_id: int):
        pass

    @rx.event
    async def create_worker(self):
        if not (await self.get_state(AppState)).has_permission(ActionEnum.WORKERS_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        if self.wrk_fio.strip() == "":
            return rx.toast.error("Вкажіть ПІБ співробітника!")
        flag, text, new_id = WorkerDAO.add_one(
            {
                "fio": self.wrk_fio.strip(),
                "phone_number": self.wrk_phone_number.strip() or None,
                "email": self.wrk_email.strip() or None,
                "position": self.wrk_position.strip() or None,
            }
        )
        if not flag:
            return rx.toast.error(text)
        self.worker_create_open = False
        self._after_create_worker(new_id)
        return rx.toast.success("Співробітника створено та обрано!")

    # ──────────────────────────────────────────────────────────────────────
    # Місце зберігання (склад / площадка / відділ)
    # Тип задається слотом, з якого відкрито діалог. Для слота призначення
    # видачі/повернення тип обирається з обмеженого набору {площадка, відділ}.
    # ──────────────────────────────────────────────────────────────────────
    storage_create_open: bool = False
    st_title: str = ""
    st_description: str = ""
    st_address: str = ""
    st_id_responsible: str = ""
    st_type: int = StorageType.WAREHOUSE
    st_slot: str = ""
    st_allow_type_choice: bool = False
    st_list_responsibles: List[Tuple[str, str]] = []

    def _reset_storage_form(self):
        self.st_title = ""
        self.st_description = ""
        self.st_address = ""
        self.st_id_responsible = ""

    @rx.var
    def st_type_title(self) -> str:
        return storage_type_list.get(self.st_type, "")

    @rx.var
    def st_type_options(self) -> List[Tuple[str, str]]:
        # Для слота призначення видачі: площадка або відділ.
        # Для слота джерела повернення: додатково клієнт.
        options = [
            (storage_type_list[StorageType.TECHNICAL_SITE], str(StorageType.TECHNICAL_SITE)),
            (storage_type_list[StorageType.DEPARTMENT], str(StorageType.DEPARTMENT)),
        ]
        if self.st_slot == "incoming":
            options.append((storage_type_list[StorageType.CLIENT], str(StorageType.CLIENT)))
        return options

    @rx.event
    def open_storage_create(self, storage_type: int, slot: str, allow_type_choice: bool = False):
        self._reset_storage_form()
        self.st_type = storage_type
        self.st_slot = slot
        self.st_allow_type_choice = allow_type_choice
        self.st_list_responsibles = [
            (w.fio, str(w.id)) for w in WorkerDAO.get_all()
        ]
        self.storage_create_open = True

    @rx.event
    def set_storage_create_open(self, value: bool):
        self.storage_create_open = value

    @rx.event
    def on_change_st_title(self, value: str):
        self.st_title = value

    @rx.event
    def on_change_st_description(self, value: str):
        self.st_description = value

    @rx.event
    def on_change_st_address(self, value: str):
        self.st_address = value

    @rx.event
    def on_change_st_id_responsible(self, value: str):
        self.st_id_responsible = value

    @rx.event
    def on_change_st_type(self, value: str):
        if value.lstrip("-").isdigit():
            self.st_type = int(value)

    def _after_create_storage(self, new_id: int):
        # Host перевизначає: за self.st_slot підставити new_id у потрібне поле
        # та перезавантажити відповідний список.
        pass

    @rx.event
    async def create_storage(self):
        if not (await self.get_state(AppState)).has_permission(ActionEnum.STORAGE_CREATE):
            return rx.toast.error("У Вас немає дозволу на виконання цієї дії!")
        if self.st_title.strip() == "":
            return rx.toast.error("Вкажіть назву місця зберігання!")
        if not self.st_id_responsible.lstrip("-").isdigit() or int(self.st_id_responsible) <= 0:
            return rx.toast.error("Оберіть відповідального!")
        storage = Storage(
            type=self.st_type,
            title=self.st_title.strip(),
            description=self.st_description.strip() or None,
            address=self.st_address.strip(),
            id_responsible=int(self.st_id_responsible),
        )
        flag, text, new_id = StorageDAO.add_one(storage)
        if not flag:
            return rx.toast.error(text)
        self.storage_create_open = False
        self._after_create_storage(new_id)
        return rx.toast.success("Місце зберігання створено та обрано!")
