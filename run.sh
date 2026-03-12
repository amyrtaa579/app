#!/bin/bash

# Загружаем переменные окружения
set -a
source .env
set +a

# Функция для запуска компонента
start_component() {
    echo "Starting $1..."
    $2
}

# Запуск всех компонентов
case "$1" in
    api)
        # Запуск FastAPI с uvicorn
        uvicorn app.main:app \
            --host ${HOST:-0.0.0.0} \
            --port ${PORT:-8000} \
            --workers ${WORKERS:-4} \
            --log-level ${LOG_LEVEL:-info} \
            --access-log
        ;;
    
    worker)
        # Запуск Celery worker
        celery -A app.worker worker \
            --loglevel=${LOG_LEVEL:-info} \
            --concurrency=2 \
            --logfile=/home/tpgk/logs/celery.log
        ;;
    
    beat)
        # Запуск Celery beat (планировщик)
        celery -A app.worker beat \
            --loglevel=${LOG_LEVEL:-info} \
            --logfile=/home/tpgk/logs/celery_beat.log
        ;;
    
    flower)
        # Запуск Flower для мониторинга Celery
        celery -A app.worker flower \
            --port=5555 \
            --basic-auth=admin:${FLOWER_PASSWORD:-password}
        ;;
    
    init)
        # Инициализация проекта
        python scripts/init_project.py
        ;;
    
    migrate)
        # Запуск миграций (если используем Alembic)
        alembic upgrade head
        ;;
    
    all)
        # Запуск всего одновременно через supervisor
        echo "Please use systemd services for production"
        echo "Or run each component separately:"
        echo "  ./run.sh api"
        echo "  ./run.sh worker"
        echo "  ./run.sh beat"
        ;;
    
    *)
        echo "Usage: $0 {api|worker|beat|flower|init|migrate|all}"
        exit 1
esac