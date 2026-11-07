"""Тесты запросов с JOIN (задание средней сложности № 8)."""

from datetime import date

import pytest

from insert_data import AUTHORS, BOOKS, LOANS, add_loan
from joins import (authors_with_book_count, books_with_authors, loans_report,
                   overdue_loans, popular_books, readers_without_loans)


def test_books_with_authors(db):
    """INNER JOIN: у каждой книги есть автор, книги не теряются."""
    rows = books_with_authors(db)
    assert len(rows) == len(BOOKS)
    assert ("Михаил Булгаков", "Мастер и Маргарита", 1967) in [
        tuple(row) for row in rows]


def test_authors_with_book_count(db):
    """LEFT JOIN сохраняет авторов без книг (с нулём)."""
    counts = {row["author"]: row["books"]
              for row in authors_with_book_count(db)}
    assert len(counts) == len(AUTHORS)
    assert counts["Фёдор Достоевский"] == 3
    assert counts["Анна Ахматова"] == 0
    assert sum(counts.values()) == len(BOOKS)


def test_readers_without_loans(db):
    """LEFT JOIN ... IS NULL находит читателей без выдач."""
    assert [row["name"] for row in readers_without_loans(db)] == [
        "Елена Попова"]
    add_loan(db, BOOKS[0][4], "popova@example.com", "2026-10-10",
             "2026-10-24")
    assert readers_without_loans(db) == []


def test_loans_report(db):
    """JOIN четырёх таблиц: одна строка на каждую выдачу."""
    rows = loans_report(db)
    assert len(rows) == len(LOANS)
    first = rows[0]
    assert (first["reader"], first["title"], first["author"]) == (
        "Иван Петров", "Война и мир", "Лев Толстой")
    statuses = [row["status"] for row in rows]
    assert statuses.count("на руках") == 4
    assert first["status"] == "возвращена 2026-09-15"


@pytest.mark.parametrize("today, expected", [
    (date(2026, 9, 1), []),
    (date(2026, 10, 10), [("Иван Петров", 10), ("Алексей Кузнецов", 5)]),
    (date(2026, 10, 20), [("Иван Петров", 20), ("Алексей Кузнецов", 15),
                          ("Мария Смирнова", 5), ("Ольга Иванова", 4)]),
])
def test_overdue_loans(db, today, expected):
    """Просрочка считается от переданной даты, возвращённые не попадают."""
    rows = overdue_loans(db, today)
    assert [(row["reader"], row["days_overdue"]) for row in rows] == expected


@pytest.mark.parametrize("minimum, expected", [
    (2, [("Мастер и Маргарита", 3), ("1984", 2)]),
    (3, [("Мастер и Маргарита", 3)]),
    (4, []),
])
def test_popular_books(db, minimum, expected):
    """HAVING отбирает книги по числу выдач."""
    rows = popular_books(db, minimum)
    assert [(row["title"], row["loans"]) for row in rows] == expected
