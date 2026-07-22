from typing import ClassVar, Dict, List, Optional

import reflex as rx

from TrifleSklad.actions import Action as SystemAction
from TrifleSklad.services.audit import AuditService, HistoryRow


class AuditHistoryMixin(rx.State, mixin=True):
    """Блок «Історія змін» для сторінок перегляду. Підмішується в кожен
    `View*State` (поруч з `AppState`): `class ViewXState(AuditHistoryMixin, AppState)`.
    Конкретний стан задає class-var `HISTORY_TABLE`/`HISTORY_ACTION`/
    `HISTORY_DETAIL_ACTION` і викликає `self._load_history(record_id)` у кінці
    свого `on_load` — за зразком `ViewUnitsReportState._load_unit`."""

    HISTORY_TABLE: ClassVar[str] = ""
    HISTORY_ACTION: ClassVar[Optional[SystemAction]] = None
    HISTORY_DETAIL_ACTION: ClassVar[Optional[SystemAction]] = None

    history_entries: List[HistoryRow] = []
    history_expanded: Dict[int, bool] = {}

    @rx.event
    def toggle_history(self, log_id: int):
        self.history_expanded[log_id] = not self.history_expanded.get(log_id, False)

    @rx.var
    def has_history(self) -> bool:
        return len(self.history_entries) > 0

    @rx.var
    def can_view_history(self) -> bool:
        return self.HISTORY_ACTION is not None and self.has_permission(self.HISTORY_ACTION)

    @rx.var
    def can_view_history_detail(self) -> bool:
        return self.HISTORY_DETAIL_ACTION is not None and self.has_permission(self.HISTORY_DETAIL_ACTION)

    def _load_history(self, record_id) -> None:
        if not self.can_view_history:
            self.history_entries = []
            return
        entries = AuditService().history_for(self.HISTORY_TABLE, record_id)
        if not self.can_view_history_detail:
            # Право на деталізацію — окреме від права бачити сам факт історії:
            # без нього деталі полів не повинні йти на клієнт узагалі (не лише
            # ховатись у UI), інакше їх видно через стан у мережевому інспекторі.
            entries = [(log_id, date, actor, action, summary, []) for log_id, date, actor, action, summary, _ in entries]
        self.history_entries = entries
