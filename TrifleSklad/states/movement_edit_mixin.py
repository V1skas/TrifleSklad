from typing import ClassVar, List, Tuple

import reflex as rx

from TrifleSklad import routes
from TrifleSklad.declared import movements_status_list, movements_type_list
from TrifleSklad.services.movement_edit import MovementEditService


class FullEditMixin(rx.State, mixin=True):
    """Повне редагування руху ТМЦ для сторінок `Edit*` — шапка плюс перелік
    одиниць, на відміну від «урізаного» шляху (лише статус і коментар).

    Підмішується в кожен `Edit*State` поруч з `AppState`:
    `class EditXState(FullEditMixin, AppState)`. Конкретний стан задає class-var
    `MOVEMENT_TYPE` і викликає `self._load_editability(id)` наприкінці свого
    `on_load` — за зразком `AuditHistoryMixin`.
    """

    MOVEMENT_TYPE: ClassVar[int] = 0

    can_edit_full: bool = False
    full_edit_block_message: str = ""
    # (id, тип, дата, статус, url) — той самий формат, що cancel_conflict_rows.
    full_edit_conflicts: List[Tuple[str, str, str, str, str]] = []
    # Причина коригування — необов'язкова, вводиться у діалозі підтвердження
    # збереження (лише коли доступне повне редагування).
    edit_reason: str = ""
    is_save_dialog_open: bool = False

    @rx.var
    def is_view_only_edit(self) -> bool:
        """Чи лишається форма «урізаною» (усі поля шапки disabled)."""
        return not self.can_edit_full

    @rx.var
    def has_full_edit_conflicts(self) -> bool:
        return len(self.full_edit_conflicts) > 0

    @rx.event
    def on_change_edit_reason(self, value: str):
        self.edit_reason = value

    @rx.event
    def open_save_dialog(self):
        """«Зберегти» у шапці: для повного редагування — діалог з необов'язковою
        причиною коригування; для урізаного — збереження одразу (причина
        коригування там не застосовна)."""
        if not self.can_edit_full:
            return self.edit_one()
        self.edit_reason = ""
        self.is_save_dialog_open = True

    @rx.event
    def set_save_dialog_open(self, value: bool):
        self.is_save_dialog_open = value

    @rx.event
    def confirm_save(self):
        self.is_save_dialog_open = False
        return self.edit_one()

    def _load_editability(self, movement_id: int) -> None:
        self.edit_reason = ""
        self.is_save_dialog_open = False
        verdict = MovementEditService().editability(
            movement_id, self.MOVEMENT_TYPE, self.user.login if self.user is not None else ""
        )
        self.can_edit_full = verdict.allowed
        self.full_edit_block_message = verdict.message
        self.full_edit_conflicts = [
            (
                str(m.id),
                movements_type_list.get(m.type, "—"),
                m.date,
                movements_status_list[m.status],
                routes.movement_view_url(m.type, m.id),
            )
            for m in verdict.conflicts
        ]
