import reflex as rx
import hashlib
import os
from sqlmodel import select

from TrifleSklad.models import Action, Role, User, Worker
from update import sync_actions

def generate_password_hash(password: str, salt: str) -> str:
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

def initial_deploy():
    with rx.session() as session:
        sync_actions(session)
        
        admin_user = session.exec(select(User).where(User.login == "admin")).first()
        if admin_user:
            print("Система уже инициализирована (пользователь 'admin' существует). Выход.")
            return

        print("Создаем первого сотрудника и администратора...")

        worker = Worker(
            fio="Главный Администратор",
            position="Системный администратор"
        )
        session.add(worker)
        session.commit()
        session.refresh(worker)

        salt = os.urandom(16).hex()
        password = "admin"
        pwd_hash = generate_password_hash(password, salt)
        
        user = User(
            login="admin",
            id_worker=worker.id,
            salt=salt,
            password_hash=pwd_hash
        )
        session.add(user)

        admin_role = Role(
            title="Супер-Администратор",
            description="Полный доступ ко всем функциям системы"
        )
        
        all_actions = session.exec(select(Action)).all()
        admin_role.actions = all_actions
        
        session.add(admin_role)
        
        user.roles = [admin_role]
        
        session.commit()
        
        print(f"Деплой успешно завершен!")
        print(f"Логин: admin")
        print(f"Пароль: {password}")
        print(f"Назначена роль: {admin_role.title} с {len(all_actions)} правами.")

if __name__ == "__main__":
    initial_deploy()