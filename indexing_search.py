"""Задание повышенной сложности № 4: индексация и поиск.

На синтетическом каталоге книг (таблица catalog, по умолчанию
100 000 строк) показано:

1. Как индекс меняет план запроса. EXPLAIN QUERY PLAN выводит
   «SCAN catalog» (перебор всех строк) без индекса и
   «SEARCH catalog USING INDEX ...» с индексом.
2. Насколько ускоряются запросы:
   - поиск по ISBN — уникальный индекс;
   - поиск по автору и году — составной индекс (author, year);
   - диапазон лет с сортировкой — покрывающий индекс (year, title):
     все нужные поля есть в индексе, таблица не читается
     (USING COVERING INDEX).
3. Полнотекстовый поиск FTS5 по названию и описанию: без учёта
   регистра, по началу слова (вой*), с операторами AND, OR, NOT,
   по фразе в кавычках, с ранжированием bm25. Обычный LIKE '%слово%'
   индекс использовать не может и ищет подстроку: по «мир» он находит
   и «Мирный».

Запуск:
    python indexing_search.py          — каталог из 100 000 книг;
    python indexing_search.py 300000   — каталог другого размера.
"""

import random
import sqlite3
import sys
import time

from library_db import connect, format_table

DEFAULT_SIZE = 100_000
SEED = 6

ADJECTIVES = ["Тихий", "Последний", "Северный", "Золотой", "Тёмный",
              "Вечный", "Забытый", "Красный", "Далёкий", "Белый",
              "Старый", "Мирный"]
NOUNS = ["дом", "сад", "город", "путь", "берег", "лес", "мир", "огонь",
         "ветер", "остров", "век", "след"]
GENRES = ["Роман", "Повесть", "Сборник рассказов", "Пьеса", "Очерк"]
TOPICS = ["война", "любовь", "мир", "дорога", "семья", "море", "звёзды",
          "память", "детство", "революция", "наука", "путешествие",
          "тайна", "дружба", "свобода", "ёлка"]
INITIALS = "АБВГДЕЗИКЛМНОПРС"
SURNAMES = ["Иванов", "Смирнов", "Кузнецов", "Попов", "Соколов", "Лебедев",
            "Козлов", "Новиков", "Морозов", "Волков", "Зайцев", "Павлов"]

INDEXES = {
    "idx_catalog_isbn":
        "CREATE UNIQUE INDEX idx_catalog_isbn ON catalog (isbn)",
    "idx_catalog_author_year":
        "CREATE INDEX idx_catalog_author_year ON catalog (author, year)",
    "idx_catalog_year_title":
        "CREATE INDEX idx_catalog_year_title ON catalog (year, title)",
}


def generate_books(count, seed=SEED):
    """Сгенерировать count книг: (название, автор, год, ISBN, описание).

    Генератор случайных чисел инициализируется seed, поэтому данные
    одинаковы при каждом запуске.
    """
    rng = random.Random(seed)
    for number in range(1, count + 1):
        title = f"{rng.choice(ADJECTIVES)} {rng.choice(NOUNS)}"
        author = f"{rng.choice(INITIALS)}. {rng.choice(SURNAMES)}"
        topics = ", ".join(rng.sample(TOPICS, 3))
        description = f"{rng.choice(GENRES)}. Темы: {topics}."
        yield (title, author, rng.randint(1900, 2025),
               f"978-5-{number:07d}", description)


def create_catalog(conn):
    """Создать пустую таблицу catalog без индексов."""
    conn.executescript("""
        DROP TABLE IF EXISTS catalog;
        CREATE TABLE catalog (
            id          INTEGER PRIMARY KEY,
            title       TEXT    NOT NULL,
            author      TEXT    NOT NULL,
            year        INTEGER NOT NULL,
            isbn        TEXT    NOT NULL,
            description TEXT    NOT NULL
        );
    """)


def fill_catalog(conn, count, seed=SEED):
    """Заполнить каталог count сгенерированными книгами."""
    with conn:
        conn.executemany(
            "INSERT INTO catalog (title, author, year, isbn, description) "
            "VALUES (?, ?, ?, ?, ?)", generate_books(count, seed))
    return count


def create_indexes(conn):
    """Создать индексы каталога."""
    with conn:
        for sql in INDEXES.values():
            conn.execute(sql)


def drop_indexes(conn):
    """Удалить индексы каталога."""
    with conn:
        for name in INDEXES:
            conn.execute(f"DROP INDEX IF EXISTS {name}")


def query_plan(conn, sql, params=()):
    """Вернуть план выполнения запроса (EXPLAIN QUERY PLAN) списком строк."""
    return [row[3] for row in
            conn.execute(f"EXPLAIN QUERY PLAN {sql}", params)]


def best_time_ms(conn, sql, params=(), repeat=5):
    """Лучшее из repeat время выполнения запроса в миллисекундах."""
    best = float("inf")
    for _ in range(repeat):
        start = time.perf_counter()
        conn.execute(sql, params).fetchall()
        best = min(best, time.perf_counter() - start)
    return best * 1000


def sample_queries(conn):
    """Запросы для сравнения со значениями, взятыми из самих данных."""
    middle = conn.execute("SELECT COUNT(*) / 2 FROM catalog").fetchone()[0]
    row = conn.execute("SELECT isbn, author, year FROM catalog WHERE id = ?",
                       (max(middle, 1),)).fetchone()
    return [
        ("Поиск по ISBN",
         "SELECT * FROM catalog WHERE isbn = ?", (row["isbn"],)),
        ("Автор и год",
         "SELECT title FROM catalog WHERE author = ? AND year = ?",
         (row["author"], row["year"])),
        ("Диапазон лет + сортировка",
         "SELECT year, title FROM catalog WHERE year BETWEEN ? AND ? "
         "ORDER BY year, title", (2000, 2001)),
    ]


def compare_indexes(conn, repeat=5):
    """Сравнить запросы без индексов и с индексами.

    Возвращает список словарей: название запроса, время и план
    выполнения до и после создания индексов.
    """
    queries = sample_queries(conn)
    drop_indexes(conn)
    results = [{"name": name,
                "plan_before": query_plan(conn, sql, params),
                "ms_before": best_time_ms(conn, sql, params, repeat)}
               for name, sql, params in queries]
    create_indexes(conn)
    for result, (_, sql, params) in zip(results, queries):
        result["plan_after"] = query_plan(conn, sql, params)
        result["ms_after"] = best_time_ms(conn, sql, params, repeat)
    return results


def normalize(text):
    """Заменить «ё» на «е», чтобы поиск не зависел от этой буквы.

    Регистр букв FTS5 (токенизатор unicode61) учитывает сам, поэтому
    текст в нижний регистр не переводится: операторы AND, OR, NOT
    в запросе должны оставаться заглавными.
    """
    return text.replace("ё", "е").replace("Ё", "Е")


def fts_available(conn):
    """Проверить, собран ли SQLite с модулем полнотекстового поиска FTS5."""
    try:
        conn.execute("CREATE VIRTUAL TABLE temp.fts_probe USING fts5(text)")
    except sqlite3.OperationalError:
        return False
    conn.execute("DROP TABLE temp.fts_probe")
    return True


def build_fts(conn):
    """Построить полнотекстовый индекс catalog_fts по каталогу."""
    conn.create_function("normalize_text", 1, normalize, deterministic=True)
    with conn:
        conn.execute("DROP TABLE IF EXISTS catalog_fts")
        conn.execute(
            "CREATE VIRTUAL TABLE catalog_fts USING fts5("
            "title, description, tokenize = 'unicode61 remove_diacritics 2')")
        conn.execute(
            "INSERT INTO catalog_fts (rowid, title, description) "
            "SELECT id, normalize_text(title), normalize_text(description) "
            "FROM catalog")


def full_text_search(conn, query, limit=10):
    """Найти книги по запросу FTS5; совпадения в названии важнее (×10).

    В поле fragment найденные слова выделены квадратными скобками.
    """
    return conn.execute(
        "SELECT c.id, c.title, c.year, "
        "       snippet(catalog_fts, -1, '[', ']', '…', 6) AS fragment, "
        "       round(bm25(catalog_fts, 10.0, 1.0), 2) AS rank "
        "FROM catalog_fts "
        "JOIN catalog AS c ON c.id = catalog_fts.rowid "
        "WHERE catalog_fts MATCH ? "
        "ORDER BY rank, c.id LIMIT ?",
        (normalize(query), limit)).fetchall()


def fts_count(conn, query):
    """Количество книг, найденных полнотекстовым поиском."""
    return conn.execute(
        "SELECT COUNT(*) FROM catalog_fts WHERE catalog_fts MATCH ?",
        (normalize(query),)).fetchone()[0]


def like_count(conn, text):
    """Количество книг, где text встречается как подстрока (LIKE)."""
    return conn.execute(
        "SELECT COUNT(*) FROM catalog "
        "WHERE py_lower(title || ' ' || description) LIKE ?",
        (f"%{text.lower()}%",)).fetchone()[0]


def main(argv=None):
    """Построить каталог и показать работу индексов и поиска."""
    args = sys.argv[1:] if argv is None else argv
    try:
        size = int(args[0]) if args else DEFAULT_SIZE
    except ValueError:
        print("Размер каталога должен быть целым числом")
        return
    conn = connect(":memory:")
    start = time.perf_counter()
    create_catalog(conn)
    fill_catalog(conn, size)
    print(f"Каталог из {size:,} книг создан за "
          f"{time.perf_counter() - start:.1f} с".replace(",", " "))

    results = compare_indexes(conn)
    print("\n== Запросы без индексов и с индексами ==")
    print(format_table(
        [(r["name"], f"{r['ms_before']:.2f}", f"{r['ms_after']:.3f}",
          f"×{r['ms_before'] / max(r['ms_after'], 1e-6):.0f}")
         for r in results],
        ["Запрос", "Без индекса, мс", "С индексом, мс", "Ускорение"]))
    print("\n== План выполнения (EXPLAIN QUERY PLAN) ==")
    for r in results:
        print(f"{r['name']}:")
        print(f"  без индекса: {'; '.join(r['plan_before'])}")
        print(f"  с индексом:  {'; '.join(r['plan_after'])}")

    if not fts_available(conn):
        print("\nSQLite собран без FTS5 — полнотекстовый поиск недоступен")
        return
    start = time.perf_counter()
    build_fts(conn)
    print(f"\nПолнотекстовый индекс FTS5 построен за "
          f"{time.perf_counter() - start:.1f} с")

    for query in ["мир", "ВОЙНА AND море", "вой*", "тайна NOT война",
                  '"тихий сад"', "елка"]:
        print(f"\n== FTS5: {query!r} — найдено {fts_count(conn, query)} ==")
        print(format_table(full_text_search(conn, query, limit=3),
                           ["id", "Название", "Год", "Где найдено", "bm25"]))

    like_ms = best_time_ms(
        conn, "SELECT id FROM catalog "
              "WHERE py_lower(title || ' ' || description) LIKE '%мир%'",
        repeat=3)
    fts_ms = best_time_ms(
        conn, "SELECT rowid FROM catalog_fts WHERE catalog_fts MATCH 'мир'",
        repeat=3)
    print("\n== LIKE '%мир%' против FTS5 'мир' ==")
    print(format_table(
        [("LIKE (подстрока, полный перебор)", like_count(conn, "мир"),
          f"{like_ms:.1f}"),
         ("FTS5 (целое слово, индекс)", fts_count(conn, "мир"),
          f"{fts_ms:.1f}")],
        ["Способ", "Найдено", "Время, мс"]))
    print("LIKE находит больше: в его результат попадают «Мирный ...».")
    conn.close()


if __name__ == "__main__":
    main()
