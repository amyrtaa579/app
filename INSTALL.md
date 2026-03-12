# Инструкция по установке чат-бота ТПГК

## 1. Подготовка сервера (Ubuntu 22.04 / 24.04)

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка необходимых пакетов
sudo apt install -y python3.11 python3.11-venv python3.11-dev \
    postgresql postgresql-contrib \
    redis-server \
    nginx \
    git \
    build-essential \
    libmagic1  # для python-magic

# Создание пользователя
sudo useradd -m -s /bin/bash tpgk
sudo usermod -aG sudo tpgk