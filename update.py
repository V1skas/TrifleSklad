import reflex as rx
from sqlmodel import select

from TrifleSklad.models import Action, Role
from TrifleSklad.actions import Action as SystemAction

# Роль, якій автоматично видаються всі права (створюється у deploy.py).
SUPER_ADMIN_ROLE_TITLE = "Супер-Администратор"


def grant_all_actions_to_super_admin(session: rx.session):
    """Видає ролі «Супер-Администратор» усі наявні права. Викликається після
    синхронізації дій, щоб нові права (додані в actions.py) одразу були доступні
    супер-адміну без ручного призначення через UI."""
    admin_role = session.exec(
        select(Role).where(Role.title == SUPER_ADMIN_ROLE_TITLE)
    ).first()
    if admin_role is None:
        return

    all_actions = session.exec(select(Action)).all()
    existing_codes = {act.code for act in admin_role.actions}
    missing = [act for act in all_actions if act.code not in existing_codes]
    if missing:
        admin_role.actions = list(admin_role.actions) + missing
        session.add(admin_role)
        session.commit()
        print(f"Супер-Администратору выдано новых прав: {len(missing)}")


def sync_actions(session: rx.session):
    print("Начинаем синхронизацию действий (Actions)...")
    
    existing_actions_list = session.exec(select(Action)).all()
    existing_actions = {act.code: act for act in existing_actions_list}
    
    added_count = 0
    updated_count = 0

    for sys_action in SystemAction:
        if sys_action.value not in existing_actions:
            new_action = Action(
                code=sys_action.value,
                title=sys_action.title_attr,
                description=sys_action.description_attr
            )
            session.add(new_action)
            added_count += 1
        else:
            db_action = existing_actions[sys_action.value]
            is_changed = False
            
            if db_action.title != sys_action.title_attr:
                db_action.title = sys_action.title_attr
                is_changed = True
                
            if db_action.description != sys_action.description_attr:
                db_action.description = sys_action.description_attr
                is_changed = True
                
            if is_changed:
                session.add(db_action)
                updated_count += 1

    session.commit()
    print(f"Готово! Добавлено: {added_count}, Обновлено текстов: {updated_count}")

    grant_all_actions_to_super_admin(session)

if __name__ == "__main__":
    with rx.session() as session:
        sync_actions(session)