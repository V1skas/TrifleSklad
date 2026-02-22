import reflex as rx
from sqlmodel import select

from TrifleSklad.models import Action 
from TrifleSklad.actions import Action as SystemAction

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

if __name__ == "__main__":
    with rx.session() as session:
        sync_actions(session)