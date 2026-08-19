FROM python:3.13-slim

WORKDIR /TrifleSklad

# Reflex требует unzip и curl для скачивания внутреннего JS-движка (bun)
RUN apt-get update && apt-get install -y unzip curl && rm -rf /var/lib/apt/lists/*

# Копируем конфигурацию uv. .python-version фиксирует интерпретатор на 3.13 —
# без него uv взял бы последнюю версию под requires-python (>=3.13) и тянул 3.14.
COPY pyproject.toml uv.lock* .python-version ./

# Моментально устанавливаем зависимости
RUN pip install uv
RUN uv sync

# Копируем весь оставшийся код проекта. Каталог utils/ переехал в
# TrifleSklad/utils/ (рефакторинг архитектуры), поэтому отдельно не копируется.
COPY alembic.ini rxconfig.py update.py .update_marker deploy.py entrypoint.sh ./
COPY TrifleSklad/ ./TrifleSklad/
COPY alembic ./alembic/
COPY assets/ ./assets/
COPY components/ ./components/

# RUN uv run reflex export --frontend-only --no-zip

# Настройки для продакшена
ENV DB_URL="sqlite:///data/reflex.db"

ENTRYPOINT [ "sh", "entrypoint.sh" ]

# Запускаем Reflex. В режиме prod (Reflex 0.9) фронтенд и бэкенд работают на
# ОДНОМ порту — раздаётся и статика, и WebSocket-логика. Явно задаём порт 80,
# чтобы вшитый во фронтенд адрес бэкенда (env.json) совпадал с опубликованным
# портом контейнера и WebSocket подключался same-origin, без привязки к
# конкретному внешнему адресу.
CMD ["uv", "run", "reflex", "run", "--env", "prod", "--backend-port", "80"]