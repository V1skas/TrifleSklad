"""Спільні UI-компоненти для inline-створення довідкових даних з форм руху ТМЦ.

Кожен білдер діалогу приймає host-стан (`Add*State`, що підмішує
`LookupCreatorsMixin`) і рендериться поряд з відповідним селектом форми.
Кнопка `create_lookup_button` — ghost-кнопка «＋ Створити …», видима лише за
наявності відповідного права (як кнопка «Створити товар» у поставці).
"""

import reflex as rx

from TrifleSklad.state import AppState


def create_lookup_button(action, label: str, on_click) -> rx.Component:
    return rx.hstack(
        rx.spacer(),
        rx.cond(
            AppState.get_user_actions.contains(action),
            rx.button(
                rx.icon("plus", size=14),
                label,
                variant="ghost",
                size="2",
                type="button",
                on_click=on_click,
            ),
        ),
        width="100%",
    )


def _field(label: str, value, on_change, area: bool = False) -> rx.Component:
    return rx.fragment(
        rx.text(label, size="2"),
        (rx.text_area if area else rx.input)(
            value=value,
            on_change=on_change,
            width="100%",
        ),
    )


def supplier_create_dialog(State) -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Створення постачальника"),
            rx.vstack(
                rx.text("*Назва:", size="2"),
                rx.input(value=State.sup_title, on_change=State.on_change_sup_title, width="100%"),
                _field("Опис:", State.sup_description, State.on_change_sup_description, area=True),
                _field("Адреса:", State.sup_address, State.on_change_sup_address),
                _field("Email:", State.sup_email, State.on_change_sup_email),
                _field("Контактна особа:", State.sup_contact_person, State.on_change_sup_contact_person),
                _field("Контактний телефон:", State.sup_contact_phone, State.on_change_sup_contact_phone),
                _field("ЄДРПОУ:", State.sup_edrpou, State.on_change_sup_edrpou),
                rx.hstack(
                    rx.button("Скасувати", variant="outline", type="button", on_click=State.set_supplier_create_open(False)),
                    rx.spacer(),
                    rx.button("Створити", type="button", on_click=State.create_supplier),
                    width="100%",
                    padding_top="0.5em",
                ),
                spacing="2",
                width="100%",
            ),
            width="28em",
        ),
        open=State.supplier_create_open,
        on_open_change=State.set_supplier_create_open,
    )


def owner_create_dialog(State) -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Створення власника"),
            rx.vstack(
                rx.text("*Назва:", size="2"),
                rx.input(value=State.owner_title, on_change=State.on_change_owner_title, width="100%"),
                _field("Опис:", State.owner_description, State.on_change_owner_description, area=True),
                rx.hstack(
                    rx.button("Скасувати", variant="outline", type="button", on_click=State.set_owner_create_open(False)),
                    rx.spacer(),
                    rx.button("Створити", type="button", on_click=State.create_owner),
                    width="100%",
                    padding_top="0.5em",
                ),
                spacing="2",
                width="100%",
            ),
            width="28em",
        ),
        open=State.owner_create_open,
        on_open_change=State.set_owner_create_open,
    )


def payment_type_create_dialog(State) -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Створення типу оплати"),
            rx.vstack(
                rx.text("*Назва:", size="2"),
                rx.input(value=State.pt_title, on_change=State.on_change_pt_title, width="100%"),
                _field("Опис:", State.pt_description, State.on_change_pt_description, area=True),
                rx.hstack(
                    rx.button("Скасувати", variant="outline", type="button", on_click=State.set_payment_type_create_open(False)),
                    rx.spacer(),
                    rx.button("Створити", type="button", on_click=State.create_payment_type),
                    width="100%",
                    padding_top="0.5em",
                ),
                spacing="2",
                width="100%",
            ),
            width="28em",
        ),
        open=State.payment_type_create_open,
        on_open_change=State.set_payment_type_create_open,
    )


def nds_rate_create_dialog(State) -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Створення ставки ПДВ"),
            rx.vstack(
                rx.text("*Назва:", size="2"),
                rx.input(value=State.nds_title, on_change=State.on_change_nds_title, width="100%"),
                rx.text("Ставка (%):", size="2"),
                rx.input(
                    type="number",
                    min="0",
                    step="0.01",
                    value=State.nds_rate_value,
                    on_change=State.on_change_nds_rate_value,
                    width="100%",
                ),
                _field("Опис:", State.nds_description, State.on_change_nds_description, area=True),
                rx.hstack(
                    rx.button("Скасувати", variant="outline", type="button", on_click=State.set_nds_rate_create_open(False)),
                    rx.spacer(),
                    rx.button("Створити", type="button", on_click=State.create_nds_rate),
                    width="100%",
                    padding_top="0.5em",
                ),
                spacing="2",
                width="100%",
            ),
            width="28em",
        ),
        open=State.nds_rate_create_open,
        on_open_change=State.set_nds_rate_create_open,
    )


def worker_create_dialog(State) -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Створення співробітника"),
            rx.vstack(
                rx.text("*ПІБ:", size="2"),
                rx.input(value=State.wrk_fio, on_change=State.on_change_wrk_fio, width="100%"),
                _field("Телефон:", State.wrk_phone_number, State.on_change_wrk_phone_number),
                _field("Email:", State.wrk_email, State.on_change_wrk_email),
                _field("Посада:", State.wrk_position, State.on_change_wrk_position),
                rx.hstack(
                    rx.button("Скасувати", variant="outline", type="button", on_click=State.set_worker_create_open(False)),
                    rx.spacer(),
                    rx.button("Створити", type="button", on_click=State.create_worker),
                    width="100%",
                    padding_top="0.5em",
                ),
                spacing="2",
                width="100%",
            ),
            width="28em",
        ),
        open=State.worker_create_open,
        on_open_change=State.set_worker_create_open,
    )


def storage_create_dialog(State) -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Створення місця зберігання"),
            rx.vstack(
                rx.cond(
                    State.st_allow_type_choice,
                    rx.fragment(
                        rx.text("*Тип:", size="2"),
                        rx.select.root(
                            rx.select.trigger(placeholder="Оберіть тип", width="100%"),
                            rx.select.content(
                                rx.foreach(
                                    State.st_type_options,
                                    lambda t: rx.select.item(t[0], value=t[1]),
                                ),
                                width="100%",
                            ),
                            value=State.st_type.to_string(),
                            on_change=State.on_change_st_type,
                            width="100%",
                        ),
                    ),
                    rx.hstack(
                        rx.text("Тип:", size="2"),
                        rx.text(State.st_type_title, weight="bold", size="2"),
                    ),
                ),
                rx.text("*Назва:", size="2"),
                rx.input(value=State.st_title, on_change=State.on_change_st_title, width="100%"),
                _field("Опис:", State.st_description, State.on_change_st_description, area=True),
                _field("Адреса:", State.st_address, State.on_change_st_address),
                rx.text("*Відповідальний:", size="2"),
                rx.select.root(
                    rx.select.trigger(placeholder="Оберіть зі списку", width="100%"),
                    rx.select.content(
                        rx.foreach(
                            State.st_list_responsibles,
                            lambda w: rx.select.item(w[0], value=w[1]),
                        ),
                        width="100%",
                    ),
                    value=State.st_id_responsible,
                    on_change=State.on_change_st_id_responsible,
                    width="100%",
                ),
                rx.hstack(
                    rx.button("Скасувати", variant="outline", type="button", on_click=State.set_storage_create_open(False)),
                    rx.spacer(),
                    rx.button("Створити", type="button", on_click=State.create_storage),
                    width="100%",
                    padding_top="0.5em",
                ),
                spacing="2",
                width="100%",
            ),
            width="28em",
        ),
        open=State.storage_create_open,
        on_open_change=State.set_storage_create_open,
    )
