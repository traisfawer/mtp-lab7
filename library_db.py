"""Общий модуль лабораторной работы № 7: база данных «Библиотека» (SQLite).

Таблицы:
- authors — авторы;
- books   — книги (ссылка на автора);
- readers — читатели;
- loans   — выдачи книг читателям (ссылки на книгу и читателя).

Ограничения NOT NULL, UNIQUE, CHECK и внешние ключи проверяет сама СУБД,
поэтому при подключении включается PRAGMA foreign_keys.
"""

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.join(BASE_DIR, "library.db")
TABLES = ("authors", "books", "readers", "loans")

SCHEMA = """
CREATE TABLE IF NOT EXISTS authors (
    id         INTEGER PRIMARY KEY,
    name       TEXT    NOT NULL UNIQUE,
    country    TEXT    NOT NULL,
    birth_year INTEGER CHECK (birth_year BETWEEN 1000 AND 2100)
);

CREATE TABLE IF NOT EXISTS books (
    id        INTEGER PRIMARY KEY,
    title     TEXT    NOT NULL,
    author_id INTEGER NOT NULL
              REFERENCES authors (id) ON DELETE RESTRICT,
    year      INTEGER NOT NULL CHECK (year BETWEEN 1000 AND 2100),
    pages     INTEGER NOT NULL CHECK (pages > 0),
    isbn      TEXT    NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS readers (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL UNIQUE CHECK (email LIKE '%_@_%'),
    registered TEXT NOT NULL DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS loans (
    id        INTEGER PRIMARY KEY,
    book_id   INTEGER NOT NULL REFERENCES books (id) ON DELETE CASCADE,
    reader_id INTEGER NOT NULL REFERENCES readers (id) ON DELETE CASCADE,
    taken     TEXT    NOT NULL,
    due       TEXT    NOT NULL,
    returned  TEXT,
    CHECK (due >= taken),
    CHECK (returned IS NULL OR returned >= taken)
);
"""


def py_lower(value):
    """Перевести текст в нижний регистр, включая русские буквы.

    Встроенная функция SQLite lower() меняет регистр только у латиницы,
    поэтому для поиска без учёта регистра регистрируется эта функция.
    """
    return value.lower() if isinstance(value, str) else value


def connect(path=DEFAULT_DB):
    """Открыть базу данных с включёнными внешними ключами.

    Строки результатов возвращаются как sqlite3.Row: к полям можно
    обращаться и по номеру, и по имени (row["title"]). В соединении
    регистрируется SQL-функция py_lower.
    """
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.create_function("py_lower", 1, py_lower, deterministic=True)
    return conn


def create_schema(conn):
    """Создать таблицы, если их ещё нет."""
    conn.executescript(SCHEMA)


def table_counts(conn):
    """Вернуть словарь «таблица → количество строк»."""
    return {table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in TABLES}


def format_table(rows, headers=()):
    """Отформатировать строки результата как текстовую таблицу."""
    body = [["" if value is None else str(value) for value in row]
            for row in rows]
    if not body:
        return "(нет строк)"
    header = [str(name) for name in headers]
    table = [header] + body if header else body
    widths = [max(len(row[i]) for row in table) for i in range(len(body[0]))]

    def line(values):
        return " | ".join(value.ljust(width)
                          for value, width in zip(values, widths)).rstrip()

    lines = [line(row) for row in table]
    if header:
        lines.insert(1, "-+-".join("-" * width for width in widths))
    return "\n".join(lines)


def print_rows(title, rows):
    """Вывести заголовок и результат запроса в виде таблицы."""
    rows = list(rows)
    headers = rows[0].keys() if rows and hasattr(rows[0], "keys") else ()
    print(f"\n== {title} ==")
    print(format_table(rows, headers))
