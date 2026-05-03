# Poker Analytics App

Технический README для локального запуска, подготовки данных и проверки качества.

## 1. Требования

- Python `>=3.11`
- `uv`
- Docker + Docker Compose v2

## 2. Структура проекта

- `src/poker/` — парсер, нормализация, расчёт статистик
- `main.py` — batch-обработка и вывод диагностик
- `app.py` — FastAPI API
- `tests/` — интеграционные тесты на реальных данных
- `stat_catalog.json` — каталог статов

## 3. Данные

Приложение читает пути из `.env`:

```env
GTO_DATA_DIR=Test base/GTO bots data
POPULATION_DATA_DIR=Test base/Тестовая база данные популяции
```

Минимально необходимые входные данные:

- `.txt` hand history файлы в `GTO_DATA_DIR`
- `.txt` hand history файлы в `POPULATION_DATA_DIR`

### Копирование данных

```bash
mkdir -p "Test base/GTO bots data" "Test base/Тестовая база данные популяции"
cp /path/to/gto/*.txt "Test base/GTO bots data/"
cp /path/to/population/*.txt "Test base/Тестовая база данные популяции/"
```

Проверка, что данные на месте:

```bash
ls -1 "Test base/GTO bots data" | head
ls -1 "Test base/Тестовая база данные популяции" | head
```

## 4. Запуск

Локально (batch):

```bash
uv run python main.py
```

Локально (API):

```bash
uv run uvicorn app:app --host 0.0.0.0 --port 8000
```

В Docker:

```bash
make start
```

### Веб-интерфейс

После запуска API (локально или в Docker), перейдите в браузере по адресу:
👉 **[http://localhost:8000](http://localhost:8000)**

Остановка:

```bash
docker compose down
```

## 5. Тесты

Запуск всех тестов:

```bash
make tests
```

Тесты используют реальные hand history данные из `.env` и не используют моки.

## 6. Coverage

Запуск покрытия:

```bash
make coverage
```

Артефакты:

- `coverage.xml` — coverage для CI/интеграций
- `term-missing` — покрытие и непрокрытые строки в консоли

<details>
<summary>Текущий результат покрытия (развернуть)</summary>


```text
TOTAL                        494     76    85%
```

```text
src/poker/__init__.py          0      0   100%
src/poker/aggregator.py       34     34     0%
src/poker/models.py           92      2    98%
src/poker/normalizer.py       97      3    97%
src/poker/parser.py          160     21    87%
src/poker/patterns.py         13      0   100%
src/poker/stat_engine.py      98     16    84%
```

</details>


Рекомендуемый минимальный порог в CI:

```bash
uv run pytest --cov=src/poker --cov-fail-under=80
```
