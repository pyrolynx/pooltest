## Небольшая сборка для тестирования пула коннектов aiopg к Postgresql
Состоит из модуля сервера `app.py`, который реализует HTTP-интерфейс на запись в базу, используемую в качестве Key
-Value хранилища. И модуля `flood.py`, содержащего в себе функциональность многократных вызовов к KV-хранилищу.


# Подготовка
```shell script
# Развернем базу с помощью Docker
docker run --rm -d --name pooltest-db -p '127.0.0.1:5432:5432' -v "$PWD/data/postgres:/var/lib/postgresql" postgres:11 

createuser -U postgres -l pooltest
createdb -U postgres -O pooltest pooltest
psql -U pooltest pooltest < 'CREATE TABLE IF NOT EXISTS kv (id SERIAL PRIMARY KEY, value VARCHAR NOT NULL);'

# Создаем вируальное окружение
python3.7 -m pip install virtualenv
python3.7 -m pip virtualenv venv
. ./venv/bin/activate

# Устанавливаем зависимости
pip3 install requirements.txt
``` 

# Тестирование
Модуль `app.py` конфигурируется с помощью `config.py`, для различных тестов рекомендуется менять параметры там.
Клиент тестирования `flood.py` содержит в себе несколько различных вызовов KeyValue HTTP API
. Для конфигурирования тестов стоит менять функцию `async def run`.

