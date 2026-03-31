#!/bin/sh
set -e

INIT_FLAG="/TrifleSklad/data/.initialized"
UPDATE_MARKER="/TrifleSklad/.update_marker"

if [ ! -f "$INIT_FLAG" ]; then
    uv run reflex db init
    uv run makemigrations
    uv run reflex db migrate
    uv run deploy.py
    uv run reflex export --frontend-only --no-zip
    touch "$INIT_FLAG"

    if [ -f "$UPDATE_MARKER" ]; then
        rm "$UPDATE_MARKER"
    fi

else
    if [ -f "$UPDATE_MARKER" ]; then
        uv run reflex db makemigrations
        uv run reflex db migrate
        uv run update.py
        uv run reflex export --frontend-only --no-zip
        rm "$UPDATE_MARKER"
    fi
fi

# Передаем управление основному процессу (Reflex)
exec "$@"