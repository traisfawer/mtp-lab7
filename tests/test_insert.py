"""Тесты вставки данных (задание средней сложности № 2)."""

import sqlite3

import pytest

from insert_data import (AUTHORS, BOOKS, LOANS, READERS, add_author,
                         add_book, add_books, add_loan, add_reader,
                         ensure_author, seed)
from library_db import table_counts


def test_seed_counts(empty_db):
    """Функция seed вставляет все демонстрационные данные."""
    assert seed(empty_db) == {"authors": len(AUTHORS), "books": len(BOOKS),
                              "readers": len(READERS), "loans": len(LOANS)}


def test_add_author_returns_id(empty_db):
    """add_author возвращает id новой строки."""
    author_id = add_author(empty_db, "Иван Тургенев", "Россия", 1818)
    row = empty_db.execute("SELECT * FROM authors WHERE id = ?",
                           (author_id,)).fetchone()
    assert (row["name"], row["country"], row["birth_year"]) == (
        "Иван Тургенев", "Россия", 1818)


def test_add_book(empty_db):
    """add_book сохраняет книгу со ссылкой на автора."""
    author_id = add_author(empty_db, "Иван Тургенев", "Россия")
    book_id = add_book(empty_db, "Отцы и дети", author_id, 1862, 288, "1")
    row = empty_db.execute("SELECT title, author_id FROM books WHERE id = ?",
                           (book_id,)).fetchone()
    assert tuple(row) == ("Отцы и дети", author_id)


def test_add_books_many(db):
    """Метод executemany добавляет все строки и сообщает их количество."""
    count = add_books(db, [
        ("Муму", "Лев Толстой", 1854, 64, "new-1"),
        ("Ася", "Лев Толстой", 1858, 96, "new-2"),
    ])
    assert count == 2
    assert table_counts(db)["books"] == len(BOOKS) + 2


def test_add_books_unknown_author(db):
    """Книга неизвестного автора не вставляется (author_id = NULL)."""
    with pytest.raises(sqlite3.IntegrityError):
        add_books(db, [("Книга", "Нет такого", 2000, 10, "new-3")])


def test_add_reader_dates(empty_db):
    """Дату регистрации можно указать или взять текущую."""
    first = add_reader(empty_db, "Аня", "anya@example.com", "2026-01-01")
    second = add_reader(empty_db, "Боря", "borya@example.com")
    dates = dict(empty_db.execute(
        "SELECT id, registered FROM readers").fetchall())
    today = empty_db.execute("SELECT date('now')").fetchone()[0]
    assert dates == {first: "2026-01-01", second: today}


def test_add_loan_resolves_ids(db):
    """add_loan находит книгу по ISBN и читателя по e-mail."""
    loan_id = add_loan(db, BOOKS[0][4], "popova@example.com",
                       "2026-10-10", "2026-10-24")
    row = db.execute(
        "SELECT b.title, r.name FROM loans AS l "
        "JOIN books AS b ON b.id = l.book_id "
        "JOIN readers AS r ON r.id = l.reader_id WHERE l.id = ?",
        (loan_id,)).fetchone()
    assert tuple(row) == ("Война и мир", "Елена Попова")


@pytest.mark.parametrize("isbn, email", [
    ("нет-такого", "popova@example.com"),
    (BOOKS[0][4], "nobody@example.com"),
])
def test_add_loan_unknown(db, isbn, email):
    """Выдача несуществующей книги или читателю, которого нет, — ошибка."""
    with pytest.raises(LookupError):
        add_loan(db, isbn, email, "2026-10-10", "2026-10-24")


def test_ensure_author_is_idempotent(empty_db):
    """INSERT OR IGNORE не создаёт дубликат и возвращает тот же id."""
    first = ensure_author(empty_db, "Иван Тургенев", "Россия")
    second = ensure_author(empty_db, "Иван Тургенев", "Россия")
    assert first == second
    assert table_counts(empty_db)["authors"] == 1
