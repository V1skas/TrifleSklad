from typing import ClassVar

import reflex as rx


class CancelWithReasonMixin(rx.State, mixin=True):
    """Спільний діалог причини скасування руху (TS-56): необов'язкова причина
    коригування, введена перед підтвердженням скасування — йде в аудит поруч
    із самою дією (зміна статусу на «Скасовано», або для постачання —
    видалення запису).

    Підмішується в кожен View*State поруч з AppState. Кнопка «Скасувати»
    відкриває діалог (`open_cancel_reason_dialog`) замість виклику дії
    напряму; підтвердження (`confirm_cancel`) делегує фактичне скасування
    методу, ім'я якого задає `CANCEL_EVENT_NAME` (за замовчуванням
    `on_click_cancel`; для постачання, де скасування — це видалення
    непроведеного запису, — `on_click_delete`). Перевірки прав/конфліктів
    лишаються в самому методі скасування — міксин лише додає крок
    підтвердження з причиною."""

    CANCEL_EVENT_NAME: ClassVar[str] = "on_click_cancel"

    cancel_reason: str = ""
    is_cancel_reason_dialog_open: bool = False

    @rx.event
    def on_change_cancel_reason(self, value: str):
        self.cancel_reason = value

    @rx.event
    def open_cancel_reason_dialog(self):
        self.cancel_reason = ""
        self.is_cancel_reason_dialog_open = True

    @rx.event
    def set_cancel_reason_dialog_open(self, value: bool):
        self.is_cancel_reason_dialog_open = value

    @rx.event
    def confirm_cancel(self):
        self.is_cancel_reason_dialog_open = False
        return getattr(self, self.CANCEL_EVENT_NAME)()
