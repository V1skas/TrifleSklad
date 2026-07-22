from typing import List, Tuple

import reflex as rx

from TrifleSklad.audit import get_audit_history, parse_changes
from TrifleSklad.audit.labels import ACTION_LABELS
from TrifleSklad.dao.user import UserDao

# (id запису audit_log, дата, ПІБ актора, підпис дії, короткий підсумок, деталізація)
# деталізація — [(підпис поля, було, стало), ...], див. BaseAuditAction.describe_rows.
HistoryRow = Tuple[int, str, str, str, str, List[Tuple[str, str, str]]]


class AuditService:
    def history_for(self, table_name: str, record_id) -> List[HistoryRow]:
        try:
            with rx.session() as session:
                logs = get_audit_history(session, table_name, record_id)
                rows: List[HistoryRow] = []
                for log in logs:
                    try:
                        action_obj = parse_changes(log)
                    except (KeyError, ValueError):
                        # Немає зареєстрованого класу дії (напр. застарілий запис) — пропускаємо.
                        continue
                    actor_fio = UserDao.get_fio(log.id_user, session) or log.id_user
                    rows.append((
                        log.id,
                        log.created_at.strftime("%d.%m.%Y %H:%M"),
                        actor_fio,
                        ACTION_LABELS.get(log.action, log.action),
                        action_obj.summary_text(),
                        action_obj.describe_rows(),
                    ))
                return rows
        except Exception as e:
            print(f"[AuditService][history_for][ERROR] {e}")
            raise
