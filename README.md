# Лабораторная работа № 7. Работа с различными СУБД в Python

**Ефимов Денис Борисович, группа 220042-11, вариант 6, лабораторная №7**

Дисциплина «Методы и технологии программирования» (часть 1).

## Задания варианта 6

Средней сложности:
- № 6 — использовать параметры запроса — `query_params.py`;
- № 8 — выполнить JOIN — `joins.py`;
- № 2 — вставить данные в таблицу — `insert_data.py`.

Повышенной сложности:
- № 4 — индексация и поиск — `indexing_search.py`;
- № 10 — unit-тесты базы данных — каталог `tests/`.

## База данных «Библиотека»

СУБД — SQLite (встроенный модуль `sqlite3`, установка сервера не нужна).
Схема и подключение — `library_db.py`:

| Таблица | Поля | Ограничения |
|---|---|---|
| `authors` | id, name, country, birth_year | name UNIQUE, CHECK года |
| `books` | id, title, author_id, year, pages, isbn | FK → authors (RESTRICT), isbn UNIQUE, CHECK pages > 0 |
| `readers` | id, name, email, registered | email UNIQUE + CHECK, дата по умолчанию |
| `loans` | id, book_id, reader_id, taken, due, returned | FK → books, readers (CASCADE), CHECK дат |

## Описание

- `insert_data.py` — INSERT с параметрами и `lastrowid`, именованные
  параметры, `executemany`, `INSERT ... SELECT`, `INSERT OR IGNORE`;
  все данные вставляются одной транзакцией (`with conn`), ошибка
  отменяет её целиком. Создаёт файл `library.db`.
- `query_params.py` — параметры `?` и `:имя`, список для `IN (...)`,
  поиск через `LIKE` с экранированием `%` и `_`, `UPDATE` с параметрами;
  демонстрация SQL-инъекции при сборке запроса f-строкой.
  Поиск не зависит от регистра русских букв: встроенный `lower()` SQLite
  работает только с латиницей, поэтому регистрируется функция `py_lower`.
- `joins.py` — `INNER JOIN`, `LEFT JOIN` (авторы без книг, читатели без
  выдач), JOIN четырёх таблиц, просрочка через `julianday`,
  `GROUP BY` + `HAVING`.
- `indexing_search.py` — каталог из 100 000 книг: время запросов и план
  `EXPLAIN QUERY PLAN` без индексов и с индексами (уникальный,
  составной, покрывающий); полнотекстовый поиск FTS5 (регистр, «ё/е»,
  `вой*`, `AND`/`OR`/`NOT`, фраза, ранжирование `bm25`, фрагменты
  `snippet`) и сравнение с `LIKE '%...%'`.
- `tests/` — 88 тестов pytest; каждый тест работает с новой базой
  в памяти: ограничения целостности, каскадное удаление, атомарность
  транзакций, вставка, параметры и SQL-инъекция, JOIN, планы запросов
  и полнотекстовый поиск.

## Запуск

```
pip install -r requirements.txt

python insert_data.py
python query_params.py
python query_params.py Чехов
python joins.py
python indexing_search.py
python indexing_search.py 300000
```

## Тесты

```
python -m pytest -v
```

Проверка стиля: `python -m flake8 .`
