from typing import List

from sqlmodel import Session, select

from TrifleSklad.audit.base import BaseAuditAction
from TrifleSklad.models import AuditLog


def record_action(session: Session, actor_login: str, record_id, action: BaseAuditAction) -> None:
    """Кладе запис аудиту в ПОТОЧНУ сесію без власного commit — фіксується
    тоді й тільки тоді, коли фіксується сама мутація (та ж транзакція).
    "Порожні" зміни (edit без реальної різниці полів) не пишуться."""
    if not action.has_changes():
        return
    session.add(
        AuditLog(
            id_user=actor_login,
            action=action.action,
            table_name=action.table_name,
            record_id=str(record_id),
            changes=action.model_dump_json(exclude_none=True),
        )
    )


def get_audit_history(session: Session, table_name: str, record_id) -> List[AuditLog]:
    statement = (
        select(AuditLog)
        .where(AuditLog.table_name == table_name, AuditLog.record_id == str(record_id))
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    )
    return session.exec(statement).all()
