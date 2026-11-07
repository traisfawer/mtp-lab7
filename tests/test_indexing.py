"""Тесты индексов и полнотекстового поиска (повышенная сложность № 4)."""

import sqlite3

import pytest

from indexing_search import (INDEXES, compare_indexes, create_indexes,
                             drop_indexes, fts_count, full_text_search,
                             generate_books, like_count, main, normalize,
                             query_plan, sample_queries,
                             speedup_text)


def plan_text(conn, sql, params=()):
    """План запроса одной строкой."""
    return " ".join(query_plan(conn, sql, params))


def test_generate_books_deterministic():
    """Данные каталога одинаковы при одном seed и различны при разных."""
    assert list(generate_books(50, seed=1)) == list(generate_books(50, seed=1))
    assert list(generate_books(50, seed=1)) != list(generate_books(50, seed=2))


def test_catalog_filled(catalog, catalog_size):
    """Каталог заполнен, ISBN уникальны."""
    total, unique = catalog.execute(
        "SELECT COUNT(*), COUNT(DISTINCT isbn) FROM catalog").fetchone()
    assert total == unique == catalog_size


def test_indexes_created_and_dropped(catalog):
    """Индексы создаются и удаляются."""
    def index_names():
        return {row[0] for row in catalog.execute(
            "SELECT name FROM sqlite_master WHERE type = 'index'")}

    create_indexes(catalog)
    assert set(INDEXES) <= index_names()
    drop_indexes(catalog)
    assert not set(INDEXES) & index_names()


@pytest.mark.parametrize("number, index", [
    (0, "USING INDEX idx_catalog_isbn"),
    (1, "USING INDEX idx_catalog_author_year"),
    (2, "USING COVERING INDEX idx_catalog_year_title"),
])
def test_query_plan_uses_index(catalog, number, index):
    """Без индекса — полный перебор (SCAN), с индексом — поиск (SEARCH)."""
    _, sql, params = sample_queries(catalog)[number]
    assert "SCAN" in plan_text(catalog, sql, params)
    create_indexes(catalog)
    plan = plan_text(catalog, sql, params)
    assert "SEARCH" in plan and index in plan


def test_order_by_without_temp_sort(catalog):
    """С индексом по году сортировка не требует временного B-дерева."""
    _, sql, params = sample_queries(catalog)[2]
    assert "TEMP B-TREE" in plan_text(catalog, sql, params)
    create_indexes(catalog)
    assert "TEMP B-TREE" not in plan_text(catalog, sql, params)


def test_unique_index_rejects_duplicate(catalog):
    """Уникальный индекс запрещает повторный ISBN."""
    create_indexes(catalog)
    isbn = catalog.execute("SELECT isbn FROM catalog LIMIT 1").fetchone()[0]
    with pytest.raises(sqlite3.IntegrityError):
        catalog.execute("INSERT INTO catalog (title, author, year, isbn, "
                        "description) VALUES ('x', 'y', 2000, ?, 'z')",
                        (isbn,))


def test_index_gives_same_results(catalog):
    """Индекс ускоряет запрос, но не меняет набор найденных строк."""
    def run_all():
        return [sorted(map(tuple, catalog.execute(sql, params)))
                for _, sql, params in sample_queries(catalog)]

    before = run_all()
    create_indexes(catalog)
    assert run_all() == before
    assert all(before)


def test_full_order_by_is_stable(catalog):
    """При полной сортировке порядок строк с индексом и без совпадает."""
    _, sql, params = sample_queries(catalog)[2]
    before = list(map(tuple, catalog.execute(sql, params)))
    create_indexes(catalog)
    assert list(map(tuple, catalog.execute(sql, params))) == before


def test_compare_indexes(catalog):
    """Отчёт сравнения содержит время и планы для всех запросов."""
    results = compare_indexes(catalog, repeat=1)
    assert len(results) == 3
    for result in results:
        assert result["ms_before"] > 0 and result["ms_after"] > 0
        assert "SCAN" in " ".join(result["plan_before"])
        assert "SEARCH" in " ".join(result["plan_after"])


def test_normalize():
    """Буква «ё» заменяется на «е», регистр и операторы сохраняются."""
    assert normalize("Ёлка AND звёзды") == "Елка AND звезды"


@pytest.mark.parametrize("first, second", [
    ("война", "ВОЙНА"),
    ("ёлка", "елка"),
    ("звёзды", "ЗВЕЗДЫ"),
])
def test_fts_case_and_yo_insensitive(fts, first, second):
    """Полнотекстовый поиск не зависит от регистра и от «ё/е»."""
    assert fts_count(fts, first) == fts_count(fts, second) > 0


def test_fts_operators(fts):
    """Префикс, AND, NOT и фраза работают как ожидается."""
    war = fts_count(fts, "война")
    assert fts_count(fts, "вой*") >= war
    assert fts_count(fts, "война AND море") <= war
    assert fts_count(fts, "война NOT море") == \
        war - fts_count(fts, "война AND море")
    assert 0 < fts_count(fts, '"тихий сад"') <= fts_count(fts, "тихий")


def test_fts_results_and_ranking(fts):
    """Результаты ограничены limit, совпадение в названии — выше."""
    rows = full_text_search(fts, "мир", limit=5)
    assert len(rows) == 5
    assert all("мир" in row["title"].lower().split() for row in rows)
    assert all("[мир]" in row["fragment"].lower() for row in rows)
    ranks = [row["rank"] for row in rows]
    assert ranks == sorted(ranks)


def test_fts_not_excludes(fts):
    """Оператор NOT исключает книги со словом."""
    for row in full_text_search(fts, "тайна NOT война", limit=50):
        assert "[война]" not in row["fragment"].lower()


def test_like_finds_substrings(fts):
    """LIKE ищет подстроку, поэтому находит больше, чем FTS по слову."""
    assert like_count(fts, "мир") > fts_count(fts, "мир")
    mirny = fts.execute("SELECT COUNT(*) FROM catalog "
                        "WHERE title LIKE 'Мирный%'").fetchone()[0]
    assert mirny > 0


def test_fts_bad_query(fts):
    """Синтаксически неверный запрос FTS5 вызывает OperationalError."""
    with pytest.raises(sqlite3.OperationalError):
        fts_count(fts, "AND")


@pytest.mark.parametrize("argument", ["0", "-5", "abc", "1.5"])
def test_main_rejects_bad_size(capsys, argument):
    """Неверный размер каталога — сообщение, а не падение программы."""
    main([argument])
    assert "целым положительным" in capsys.readouterr().out


@pytest.mark.parametrize("size", ["1", "300"])
def test_main_small_catalog(capsys, size):
    """Демонстрация работает и на очень маленьком каталоге."""
    main([size])
    output = capsys.readouterr().out
    assert "USING INDEX idx_catalog_isbn" in output
    assert "LIKE '%мир%' против FTS5" in output


def test_main_output_fits_windows_encoding(capsys):
    """Вывод можно перенаправить в файл в кодировке Windows (cp1251)."""
    main(["300"])
    capsys.readouterr().out.encode("cp1251")


@pytest.mark.parametrize("before, after, text", [
    (34, 1, "в 34 раза"), (50, 1, "в 50 раз"), (12, 1, "в 12 раз"),
    (2050, 1, "в 2050 раз"), (1, 1, "в 1 раз"), (122, 1, "в 122 раза"),
])
def test_speedup_text(before, after, text):
    """Слово «раз» согласуется с числом."""
    assert speedup_text(before, after) == text
