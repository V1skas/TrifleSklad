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

# Same-origin WebSocket: фронтенд Reflex по умолчанию подменяет ХОСТ адреса
# бэкенда на window.location.hostname, но ПОРТ оставляет запечённым (backend_port,
# здесь 80). За NAT-пробросом (внешний порт → :80) страница грузится с внешнего
# порта, а WebSocket всё равно бьётся на :80 → сокет не поднимается. Патчим шаблон
# state.js в установленном reflex, чтобы порт тоже брался из window.location
# (тот же origin, что и страница) — тогда WS работает через любой проброшенный порт.
# Правится ШАБЛОН (а не .web/), т.к. reflex перегенерирует .web из шаблона при
# каждой компиляции. Guard роняет сборку, если строка-якорь изменилась в новой
# версии Reflex (чтобы баг не вернулся молча).
RUN STATE_JS="$(uv run python -c 'import reflex_base, os; print(os.path.join(os.path.dirname(reflex_base.__file__), ".templates", "web", "utils", "state.js"))')" \
    && grep -q '    endpoint.hostname = frontend_hostname;' "$STATE_JS" \
    && sed -i 's/    endpoint.hostname = frontend_hostname;/    endpoint.hostname = frontend_hostname;\n    endpoint.port = window.location.port;/' "$STATE_JS" \
    && grep -q '    endpoint.port = window.location.port;' "$STATE_JS"

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