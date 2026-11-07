"""Задание средней сложности № 6: использовать параметры запроса.

Значения никогда не вставляются в текст SQL — они передаются отдельно,
а модуль sqlite3 подставляет их сам. Показаны:
- позиционные параметры «?» — books_by_author, set_pages;
- именованные параметры «:имя» — books_in_years;
- список значений для IN (...) — books_by_ids;
- параметр в LIKE с экранированием % и _ — search_titles;
- почему нельзя собирать SQL через f-строку — find_reader_unsafe
  (SQL-инъекция) и безопасный вариант find_reader.

Запуск:
    python query_params.py            — демонстрация;
    python query_params.py Чехов      — поиск книг автора из аргумента.
"""

import sys

from insert_data import open_demo_db
from library_db import print_rows


def books_by_author(conn, author_name):
    """Найти книги автора по части имени (позиционный параметр «?»)."""
    return conn.execute(
        "SELECT b.title, b.year FROM books AS b "
        "JOIN authors AS a ON a.id = b.author_id "
        "WHERE py_lower(a.name) LIKE ? ESCAPE '\\' ORDER BY b.year",
        (like_pattern(author_name),)).fetchall()


def books_in_years(conn, start, end):
    """Найти книги, изданные в интервале лет (именованные параметры)."""
    return conn.execute(
        "SELECT title, year FROM books "
        "WHERE year BETWEEN :start AND :end ORDER BY year, title",
        {"start": start, "end": end}).fetchall()


def books_by_ids(conn, ids):
    """Найти книги по списку id (столько «?», сколько значений)."""
    ids = list(ids)
    if not ids:
        return []
    placeholders = ", ".join("?" * len(ids))
    return conn.execute(
        f"SELECT id, title FROM books WHERE id IN ({placeholders}) "
        "ORDER BY id", ids).fetchall()


def escape_like(text):
    """Экранировать для LIKE символы %, _ и обратную косую черту."""
    return (text.replace("\\", "\\\\")
            .replace("%", "\\%").replace("_", "\\_"))


def like_pattern(text):
    """Шаблон LIKE «содержит text» без учёта регистра."""
    return f"%{escape_like(text.strip().lower())}%"


def search_titles(conn, text):
    """Найти книги, в названии которых есть text (без учёта регистра)."""
    return conn.execute(
        "SELECT title, year FROM books "
        "WHERE py_lower(title) LIKE ? ESCAPE '\\' ORDER BY title",
        (like_pattern(text),)).fetchall()


def set_pages(conn, isbn, pages):
    """Изменить число страниц книги; вернуть количество изменённых строк."""
    with conn:
        cursor = conn.execute("UPDATE books SET pages = ? WHERE isbn = ?",
                              (pages, isbn))
    return cursor.rowcount


def find_reader_unsafe(conn, name):
    """НЕБЕЗОПАСНО: значение вставляется в SQL через f-строку.

    Оставлено только для демонстрации SQL-инъекции: строка
    «' OR '1'='1» превращает условие в «всегда истина».
    """
    return conn.execute(
        f"SELECT name, email FROM readers WHERE name = '{name}'").fetchall()


def find_reader(conn, name):
    """Найти читателя по имени безопасно — через параметр."""
    return conn.execute("SELECT name, email FROM readers WHERE name = ?",
                        (name,)).fetchall()


def main(argv=None):
    """Продемонстрировать параметризованные запросы."""
    args = sys.argv[1:] if argv is None else argv
    conn = open_demo_db()

    author = " ".join(args) if args else "Достоевский"
    print_rows(f"Книги автора «{author}» (параметр ?)",
               books_by_author(conn, author))
    print_rows("Книги 1860–1880 годов (параметры :start и :end)",
               books_in_years(conn, 1860, 1880))
    print_rows("Книги с id 1, 5, 12 (IN с тремя параметрами)",
               books_by_ids(conn, [1, 5, 12]))
    print_rows("Поиск «МАСТЕР» без учёта регистра (LIKE с параметром)",
               search_titles(conn, "МАСТЕР"))
    print_rows("Поиск «№ 6» (символы в параметре не ломают запрос)",
               search_titles(conn, "№ 6"))

    changed = set_pages(conn, "978-5-17-000012-7", 328)
    print(f"\nUPDATE с параметрами изменил строк: {changed}")

    attack = "' OR '1'='1"
    print(f"\nВвод злоумышленника: {attack}")
    print(f"f-строка (инъекция) вернула строк: "
          f"{len(find_reader_unsafe(conn, attack))} — все читатели!")
    print(f"Параметр «?» вернул строк: {len(find_reader(conn, attack))} — "
          f"такого имени нет, ввод воспринят как обычный текст")
    conn.close()


if __name__ == "__main__":
    main()
