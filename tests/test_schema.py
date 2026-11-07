"""Тесты схемы: ограничения целостности, каскады, транзакции."""

import sqlite3

import pytest

from insert_data import (AUTHORS, BOOKS, READERS, add_reader, open_demo_db,
                         seed)
from library_db import TABLES, table_counts


def test_tables_created(empty_db):
    """Схема создаёт все четыре таблицы."""
    names = {row[0] for row in empty_db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert set(TABLES) <= names


def test_foreign_keys_enabled(empty_db):
    """Проверка внешних ключей включена при подключении."""
    assert empty_db.execute("PRAGMA foreign_keys").fetchone()[0] == 1


@pytest.mark.parametrize("sql, params", [
    ("INSERT INTO authors (name, country) VALUES (NULL, 'Россия')", ()),
    ("INSERT INTO authors (name, country) VALUES ('Лев Толстой', 'Россия')",
     ()),
    ("INSERT INTO authors (name, country, birth_year) "
     "VALUES ('Кто-то', 'Россия', 999)", ()),
    ("INSERT INTO books (title, author_id, year, pages, isbn) "
     "VALUES ('Нет автора', 999, 2000, 100, 'x-1')", ()),
    ("INSERT INTO books (title, author_id, year, pages, isbn) "
     "VALUES ('Пустая', 1, 2000, 0, 'x-2')", ()),
    ("INSERT INTO books (title, author_id, year, pages, isbn) "
     "VALUES ('Дубль', 1, 2000, 10, ?)", (BOOKS[0][4],)),
    ("INSERT INTO readers (name, email) VALUES ('Без почты', 'нет')", ()),
    ("INSERT INTO readers (name, email) "
     "VALUES ('Дубль', 'petrov@example.com')", ()),
    ("INSERT INTO loans (book_id, reader_id, taken, due) "
     "VALUES (1, 1, '2026-10-10', '2026-10-01')", ()),
    ("INSERT INTO loans (book_id, reader_id, taken, due, returned) "
     "VALUES (1, 1, '2026-10-10', '2026-10-20', '2026-10-01')", ()),
    ("INSERT INTO loans (book_id, reader_id, taken, due) "
     "VALUES (1, 999, '2026-10-10', '2026-10-20')", ()),
], ids=["author-null", "author-unique", "author-year", "book-fk",
        "book-pages", "book-isbn", "reader-email", "reader-unique",
        "loan-due", "loan-returned", "loan-fk"])
def test_constraints(db, sql, params):
    """Недопустимые данные отклоняются самой СУБД."""
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(sql, params)


def test_delete_reader_cascades_to_loans(db):
    """Удаление читателя удаляет его выдачи (ON DELETE CASCADE)."""
    before = table_counts(db)["loans"]
    with db:
        db.execute("DELETE FROM readers WHERE email = 'smirnova@example.com'")
    assert table_counts(db)["loans"] == before - 3


def test_author_with_books_cannot_be_deleted(db):
    """Автора с книгами удалить нельзя (ON DELETE RESTRICT)."""
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("DELETE FROM authors WHERE name = 'Лев Толстой'")


def test_author_without_books_can_be_deleted(db):
    """Автора без книг удалить можно."""
    with db:
        db.execute("DELETE FROM authors WHERE name = 'Анна Ахматова'")
    assert table_counts(db)["authors"] == len(AUTHORS) - 1


def test_registered_default(empty_db):
    """Дата регистрации по умолчанию — текущая дата."""
    empty_db.execute("INSERT INTO readers (name, email) "
                     "VALUES ('Новый', 'new@example.com')")
    registered, today = empty_db.execute(
        "SELECT registered, date('now') FROM readers").fetchone()
    assert registered == today


def test_seed_is_atomic(empty_db):
    """Ошибка в конце seed отменяет и все предыдущие вставки."""
    with empty_db:
        add_reader(empty_db, "Уже записан", READERS[-1][1])
    with pytest.raises(sqlite3.IntegrityError):
        seed(empty_db)
    assert table_counts(empty_db) == {"authors": 0, "books": 0,
                                      "readers": 1, "loans": 0}


def test_demo_db_file(tmp_path):
    """Файл базы заполняется один раз и сохраняет данные после закрытия."""
    path = tmp_path / "library.db"
    conn = open_demo_db(str(path))
    first = table_counts(conn)
    conn.close()
    conn = open_demo_db(str(path))
    assert table_counts(conn) == first
    conn.close()
