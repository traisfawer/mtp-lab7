"""Задание средней сложности № 8: выполнить JOIN.

Запросы к базе «Библиотека», объединяющие несколько таблиц:
- INNER JOIN двух таблиц — books_with_authors;
- LEFT JOIN + GROUP BY: авторы вместе с теми, у кого нет книг —
  authors_with_book_count;
- LEFT JOIN ... IS NULL: читатели без выдач — readers_without_loans;
- JOIN четырёх таблиц — loans_report;
- JOIN + условие с параметром и расчёт дней просрочки — overdue_loans;
- JOIN + GROUP BY + HAVING — popular_books.

Запуск: python joins.py
"""

from datetime import date

from insert_data import open_demo_db
from library_db import print_rows


def books_with_authors(conn):
    """Книги с именами авторов (INNER JOIN)."""
    return conn.execute(
        "SELECT a.name AS author, b.title, b.year "
        "FROM books AS b "
        "INNER JOIN authors AS a ON a.id = b.author_id "
        "ORDER BY a.name, b.year").fetchall()


def authors_with_book_count(conn):
    """Все авторы и число их книг, включая авторов без книг (LEFT JOIN)."""
    return conn.execute(
        "SELECT a.name AS author, COUNT(b.id) AS books "
        "FROM authors AS a "
        "LEFT JOIN books AS b ON b.author_id = a.id "
        "GROUP BY a.id "
        "ORDER BY books DESC, a.name").fetchall()


def readers_without_loans(conn):
    """Читатели, которые ещё ни разу не брали книги."""
    return conn.execute(
        "SELECT r.name, r.email "
        "FROM readers AS r "
        "LEFT JOIN loans AS l ON l.reader_id = r.id "
        "WHERE l.id IS NULL "
        "ORDER BY r.name").fetchall()


def loans_report(conn):
    """Журнал выдач: читатель, книга, автор, даты и состояние."""
    return conn.execute(
        "SELECT r.name AS reader, b.title, a.name AS author, "
        "       l.taken, l.due, "
        "       CASE WHEN l.returned IS NULL THEN 'на руках' "
        "            ELSE 'возвращена ' || l.returned END AS status "
        "FROM loans AS l "
        "JOIN readers AS r ON r.id = l.reader_id "
        "JOIN books AS b ON b.id = l.book_id "
        "JOIN authors AS a ON a.id = b.author_id "
        "ORDER BY l.taken, r.name").fetchall()


def overdue_loans(conn, today):
    """Невозвращённые книги, срок которых истёк к дате today."""
    return conn.execute(
        "SELECT r.name AS reader, r.email, b.title, l.due, "
        "       CAST(julianday(:today) - julianday(l.due) AS INTEGER) "
        "           AS days_overdue "
        "FROM loans AS l "
        "JOIN readers AS r ON r.id = l.reader_id "
        "JOIN books AS b ON b.id = l.book_id "
        "WHERE l.returned IS NULL AND l.due < :today "
        "ORDER BY days_overdue DESC",
        {"today": str(today)}).fetchall()


def popular_books(conn, min_loans=2):
    """Книги, которые выдавали не меньше min_loans раз."""
    return conn.execute(
        "SELECT b.title, a.name AS author, COUNT(*) AS loans "
        "FROM loans AS l "
        "JOIN books AS b ON b.id = l.book_id "
        "JOIN authors AS a ON a.id = b.author_id "
        "GROUP BY b.id "
        "HAVING COUNT(*) >= ? "
        "ORDER BY loans DESC, b.title", (min_loans,)).fetchall()


def main():
    """Вывести результаты всех запросов с JOIN."""
    conn = open_demo_db()
    print_rows("INNER JOIN: книги и авторы", books_with_authors(conn))
    print_rows("LEFT JOIN + GROUP BY: сколько книг у каждого автора",
               authors_with_book_count(conn))
    print_rows("LEFT JOIN ... IS NULL: читатели без выдач",
               readers_without_loans(conn))
    print_rows("JOIN четырёх таблиц: журнал выдач", loans_report(conn))
    today = date(2026, 10, 10)
    print_rows(f"Просроченные выдачи на {today:%d.%m.%Y}",
               overdue_loans(conn, today))
    print_rows("JOIN + HAVING: книги, выданные 2 и более раз",
               popular_books(conn))
    conn.close()


if __name__ == "__main__":
    main()
