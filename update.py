import reflex as rx
from sqlmodel import select

from TrifleSklad.models import Action, Role, RolesActions, UsersActions
from TrifleSklad.actions import Action as SystemAction

# Роль, якій автоматично видаються всі права (створюється у deploy.py).
SUPER_ADMIN_ROLE_TITLE = "Супер-Администратор"

# Перейменовані права: старий код -> новий. Гранти переносяться на новий код,
# стара строка `actions` видаляється. Просте вилучення з `actions.py` цього не
# зробило б: sync_actions лише додає/оновлює тексти й ніколи не видаляє строки,
# яких немає в enum, — осиротіле право лишалося б у дуал-листі вибору прав.
RENAMED_ACTIONS = {"admissions:edit_products": "admissions:edit_full"}


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


def migrate_renamed_actions(session: rx.session):
    """Переносить гранти (roles_actions / users_actions) зі старого коду права на
    новий за таблицею RENAMED_ACTIONS і видаляє стару строку `actions`.

    Ідемпотентно: якщо старої строки вже немає — no-op. Викликати ПІСЛЯ
    sync_actions, щоб новий код права вже існував у таблиці.
    """
    for old_code, new_code in RENAMED_ACTIONS.items():
        old_action = session.exec(select(Action).where(Action.code == old_code)).first()
        if old_action is None:
            continue
        new_action = session.exec(select(Action).where(Action.code == new_code)).first()
        if new_action is None:
            print(f"Пропущено перенос {old_code} -> {new_code}: нового права немає в БД")
            continue

        moved = 0
        role_grants = session.exec(
            select(RolesActions).where(RolesActions.action_id == old_action.id)
        ).all()
        existing_roles = {
            row.role_id
            for row in session.exec(
                select(RolesActions).where(RolesActions.action_id == new_action.id)
            ).all()
        }
        for grant in role_grants:
            if grant.role_id not in existing_roles:
                session.add(RolesActions(role_id=grant.role_id, action_id=new_action.id))
                moved += 1
            session.delete(grant)

        user_grants = session.exec(
            select(UsersActions).where(UsersActions.id_action == old_action.id)
        ).all()
        existing_users = {
            row.id_user
            for row in session.exec(
                select(UsersActions).where(UsersActions.id_action == new_action.id)
            ).all()
        }
        for grant in user_grants:
            if grant.id_user not in existing_users:
                session.add(UsersActions(id_user=grant.id_user, id_action=new_action.id))
                moved += 1
            session.delete(grant)

        session.delete(old_action)
        session.commit()
        print(f"Право {old_code} перейменовано на {new_code}, перенесено грантів: {moved}")


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

    migrate_renamed_actions(session)
    grant_all_actions_to_super_admin(session)

if __name__ == "__main__":
    with rx.session() as session:
        sync_actions(session)