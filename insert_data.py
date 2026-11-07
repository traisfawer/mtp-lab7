"""Задание средней сложности № 2: вставить данные в таблицу.

Показаны разные способы вставки в SQLite:
- одиночный INSERT с параметрами и получением id новой строки
  (cursor.lastrowid) — add_author, add_book;
- именованные параметры и значение по умолчанию — add_reader;
- массовая вставка executemany — add_books;
- INSERT ... SELECT: id связанных строк ищутся прямо в запросе — add_loan;
- INSERT OR IGNORE — повторная вставка без ошибки — ensure_author;
- вставка всех данных одной транзакцией (with conn) — seed: при ошибке
  в любой строке не сохраняется ничего.

Запуск: python insert_data.py — пересоздаёт файл library.db.
"""

import os
import sqlite3

from library_db import (DEFAULT_DB, connect, create_schema, print_rows,
                        table_counts)

AUTHORS = [
    ("Лев Толстой", "Россия", 1828),
    ("Фёдор Достоевский", "Россия", 1821),
    ("Антон Чехов", "Россия", 1860),
    ("Михаил Булгаков", "Россия", 1891),
    ("Александр Пушкин", "Россия", 1799),
    ("Джордж Оруэлл", "Великобритания", 1903),
    ("Рэй Брэдбери", "США", 1920),
    ("Анна Ахматова", "Россия", 1889),
]

BOOKS = [
    ("Война и мир", "Лев Толстой", 1869, 1300, "978-5-17-000001-1"),
    ("Анна Каренина", "Лев Толстой", 1878, 864, "978-5-17-000002-8"),
    ("Преступление и наказание", "Фёдор Достоевский", 1866, 672,
     "978-5-17-000003-5"),
    ("Идиот", "Фёдор Достоевский", 1869, 640, "978-5-17-000004-2"),
    ("Братья Карамазовы", "Фёдор Достоевский", 1880, 992,
     "978-5-17-000005-9"),
    ("Вишнёвый сад", "Антон Чехов", 1904, 96, "978-5-17-000006-6"),
    ("Палата № 6", "Антон Чехов", 1892, 128, "978-5-17-000007-3"),
    ("Мастер и Маргарита", "Михаил Булгаков", 1967, 480,
     "978-5-17-000008-0"),
    ("Собачье сердце", "Михаил Булгаков", 1987, 160, "978-5-17-000009-7"),
    ("Евгений Онегин", "Александр Пушкин", 1833, 320, "978-5-17-000010-3"),
    ("Капитанская дочка", "Александр Пушкин", 1836, 224,
     "978-5-17-000011-0"),
    ("1984", "Джордж Оруэлл", 1949, 320, "978-5-17-000012-7"),
    ("Скотный двор", "Джордж Оруэлл", 1945, 128, "978-5-17-000013-4"),
    ("451 градус по Фаренгейту", "Рэй Брэдбери", 1953, 256,
     "978-5-17-000014-1"),
]

READERS = [
    ("Иван Петров", "petrov@example.com", "2026-09-01"),
    ("Мария Смирнова", "smirnova@example.com", "2026-09-01"),
    ("Алексей Кузнецов", "kuznetsov@example.com", "2026-09-05"),
    ("Ольга Иванова", "ivanova@example.com", "2026-09-10"),
    ("Дмитрий Соколов", "sokolov@example.com", "2026-09-15"),
    ("Елена Попова", "popova@example.com", "2026-10-01"),
]

LOANS = [
    ("978-5-17-000001-1", "petrov@example.com", "2026-09-02", "2026-09-16",
     "2026-09-15"),
    ("978-5-17-000008-0", "petrov@example.com", "2026-09-16", "2026-09-30",
     None),
    ("978-5-17-000003-5", "smirnova@example.com", "2026-09-03",
     "2026-09-17", "2026-09-20"),
    ("978-5-17-000008-0", "smirnova@example.com", "2026-09-05",
     "2026-09-12", "2026-09-12"),
    ("978-5-17-000012-7", "smirnova@example.com", "2026-10-01",
     "2026-10-15", None),
    ("978-5-17-000012-7", "kuznetsov@example.com", "2026-09-06",
     "2026-09-20", "2026-09-19"),
    ("978-5-17-000010-3", "kuznetsov@example.com", "2026-09-21",
     "2026-10-05", None),
    ("978-5-17-000006-6", "ivanova@example.com", "2026-09-11", "2026-09-25",
     "2026-09-24"),
    ("978-5-17-000008-0", "ivanova@example.com", "2026-10-02", "2026-10-16",
     None),
    ("978-5-17-000014-1", "sokolov@example.com", "2026-09-16", "2026-09-30",
     "2026-10-03"),
]


def add_author(conn, name, country, birth_year=None):
    """Добавить автора и вернуть его id."""
    cursor = conn.execute(
        "INSERT INTO authors (name, country, birth_year) VALUES (?, ?, ?)",
        (name, country, birth_year))
    return cursor.lastrowid


def ensure_author(conn, name, country, birth_year=None):
    """Добавить автора, если его ещё нет, и вернуть id (INSERT OR IGNORE)."""
    conn.execute(
        "INSERT OR IGNORE INTO authors (name, country, birth_year) "
        "VALUES (?, ?, ?)", (name, country, birth_year))
    return conn.execute("SELECT id FROM authors WHERE name = ?",
                        (name,)).fetchone()[0]


def add_book(conn, title, author_id, year, pages, isbn):
    """Добавить книгу и вернуть её id."""
    cursor = conn.execute(
        "INSERT INTO books (title, author_id, year, pages, isbn) "
        "VALUES (?, ?, ?, ?, ?)", (title, author_id, year, pages, isbn))
    return cursor.lastrowid


def add_books(conn, books):
    """Добавить книги одним вызовом executemany.

    books — последовательность кортежей (название, имя автора, год,
    страниц, ISBN). id автора находится подзапросом.
    """
    cursor = conn.executemany(
        "INSERT INTO books (title, author_id, year, pages, isbn) "
        "VALUES (?, (SELECT id FROM authors WHERE name = ?), ?, ?, ?)",
        books)
    return cursor.rowcount


def add_reader(conn, name, email, registered=None):
    """Добавить читателя (именованные параметры) и вернуть его id.

    Если дата регистрации не указана, берётся текущая дата.
    """
    cursor = conn.execute(
        "INSERT INTO readers (name, email, registered) "
        "VALUES (:name, :email, COALESCE(:registered, date('now')))",
        {"name": name, "email": email, "registered": registered})
    return cursor.lastrowid


def add_loan(conn, isbn, email, taken, due, returned=None):
    """Выдать книгу читателю (INSERT ... SELECT) и вернуть id выдачи."""
    cursor = conn.execute(
        "INSERT INTO loans (book_id, reader_id, taken, due, returned) "
        "SELECT b.id, r.id, ?, ?, ? "
        "FROM books AS b, readers AS r WHERE b.isbn = ? AND r.email = ?",
        (taken, due, returned, isbn, email))
    if cursor.rowcount == 0:
        raise LookupError(f"Нет книги {isbn} или читателя {email}")
    return cursor.lastrowid


def seed(conn):
    """Заполнить базу демонстрационными данными одной транзакцией."""
    with conn:
        conn.executemany(
            "INSERT INTO authors (name, country, birth_year) VALUES (?, ?, ?)",
            AUTHORS)
        add_books(conn, BOOKS)
        for name, email, registered in READERS:
            add_reader(conn, name, email, registered)
        for loan in LOANS:
            add_loan(conn, *loan)
    return table_counts(conn)


def open_demo_db(path=DEFAULT_DB):
    """Открыть базу; если она пустая, создать таблицы и заполнить их."""
    conn = connect(path)
    create_schema(conn)
    if table_counts(conn)["authors"] == 0:
        seed(conn)
    return conn


def main():
    """Пересоздать library.db и показать разные способы вставки."""
    if os.path.exists(DEFAULT_DB):
        os.remove(DEFAULT_DB)
    conn = connect(DEFAULT_DB)
    create_schema(conn)

    print("Демонстрационные данные (одна транзакция):", seed(conn))

    with conn:
        author_id = add_author(conn, "Иван Тургенев", "Россия", 1818)
        print(f"\nДобавлен автор, id = {author_id} (cursor.lastrowid)")
        book_id = add_book(conn, "Отцы и дети", author_id, 1862, 288,
                           "978-5-17-000015-8")
        print(f"Добавлена книга, id = {book_id}")
        count = add_books(conn, [
            ("Муму", "Иван Тургенев", 1854, 64, "978-5-17-000016-5"),
            ("Ася", "Иван Тургенев", 1858, 96, "978-5-17-000017-2"),
        ])
        print(f"executemany добавил книг: {count}")
        reader_id = add_reader(conn, "Новый Читатель", "new@example.com")
        print(f"Добавлен читатель, id = {reader_id}, дата — сегодняшняя")
        loan_id = add_loan(conn, "978-5-17-000015-8", "new@example.com",
                           "2026-10-10", "2026-10-24")
        print(f"Оформлена выдача, id = {loan_id} (INSERT ... SELECT)")

    again = ensure_author(conn, "Иван Тургенев", "Россия", 1818)
    print(f"INSERT OR IGNORE для существующего автора вернул тот же id: "
          f"{again}")

    try:
        with conn:
            add_author(conn, "Николай Гоголь", "Россия", 1809)
            add_book(conn, "Дубликат ISBN", author_id, 1900, 10,
                     "978-5-17-000001-1")
    except sqlite3.IntegrityError as error:
        print(f"\nОшибка: {error}. Транзакция отменена целиком — "
              f"автор «Николай Гоголь» тоже не сохранён:",
              conn.execute("SELECT COUNT(*) FROM authors WHERE name = ?",
                           ("Николай Гоголь",)).fetchone()[0] == 0)

    print("\nСтрок в таблицах:", table_counts(conn))
    print_rows("Книги Ивана Тургенева", conn.execute(
        "SELECT id, title, year, pages, isbn FROM books WHERE author_id = ?",
        (author_id,)))
    conn.close()
    print(f"\nБаза сохранена в {DEFAULT_DB}")


if __name__ == "__main__":
    main()
