"""Тесты параметризованных запросов (задание средней сложности № 6)."""

import sqlite3

import pytest

from insert_data import BOOKS, READERS
from query_params import (books_by_author, books_by_ids, books_in_years,
                          escape_like, find_reader, find_reader_unsafe,
                          like_pattern, search_titles, set_pages)


def titles(rows):
    """Список названий из результата запроса."""
    return [row["title"] for row in rows]


@pytest.mark.parametrize("name", ["Достоевский", "достоевский", "ДОСТО"])
def test_books_by_author(db, name):
    """Поиск по части имени автора не зависит от регистра."""
    assert titles(books_by_author(db, name)) == [
        "Преступление и наказание", "Идиот", "Братья Карамазовы"]


def test_books_in_years_inclusive(db):
    """Границы интервала входят в результат."""
    rows = books_in_years(db, 1866, 1869)
    assert [(row["title"], row["year"]) for row in rows] == [
        ("Преступление и наказание", 1866),
        ("Война и мир", 1869),
        ("Идиот", 1869),
    ]


def test_books_by_ids(db):
    """IN (...) с параметрами: несуществующие id просто не находятся."""
    rows = books_by_ids(db, [12, 1, 999])
    assert [(row["id"], row["title"]) for row in rows] == [
        (1, "Война и мир"), (12, "1984")]
    assert books_by_ids(db, []) == []


@pytest.mark.parametrize("text, expected", [
    ("МАСТЕР", ["Мастер и Маргарита"]),
    ("  сад ", ["Вишнёвый сад"]),
    ("№ 6", ["Палата № 6"]),
    ("%", []),
    ("_", []),
    ("нет такого", []),
])
def test_search_titles(db, text, expected):
    """Поиск по названию: без учёта регистра, % и _ — обычные символы."""
    assert titles(search_titles(db, text)) == expected


def test_escape_like():
    """Спецсимволы LIKE экранируются обратной косой чертой."""
    assert escape_like("50%_a") == "50\\%\\_a"
    assert like_pattern(" ВОЙНА ") == "%война%"


def test_set_pages(db):
    """UPDATE с параметрами меняет одну строку; чужой ISBN — ни одной."""
    isbn = BOOKS[0][4]
    assert set_pages(db, isbn, 1225) == 1
    assert db.execute("SELECT pages FROM books WHERE isbn = ?",
                      (isbn,)).fetchone()[0] == 1225
    assert set_pages(db, "нет-такого", 1) == 0


def test_set_pages_check_constraint(db):
    """Недопустимое значение отклоняется, старое значение сохраняется."""
    isbn = BOOKS[0][4]
    with pytest.raises(sqlite3.IntegrityError):
        set_pages(db, isbn, 0)
    assert db.execute("SELECT pages FROM books WHERE isbn = ?",
                      (isbn,)).fetchone()[0] == BOOKS[0][3]


def test_sql_injection(db):
    """f-строка уязвима к SQL-инъекции, параметр — нет."""
    attack = "' OR '1'='1"
    assert len(find_reader_unsafe(db, attack)) == len(READERS)
    assert find_reader(db, attack) == []


def test_find_reader(db):
    """Параметризованный поиск находит читателя по точному имени."""
    rows = find_reader(db, "Ольга Иванова")
    assert [tuple(row) for row in rows] == [
        ("Ольга Иванова", "ivanova@example.com")]
