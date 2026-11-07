"""Фикстуры pytest для unit-тестов базы данных (повышенная сложность № 10).

Каждый тест получает новую базу в памяти (":memory:"), поэтому тесты
не зависят друг от друга и не трогают файл library.db.
"""

import pytest

from indexing_search import build_fts, create_catalog, fill_catalog
from indexing_search import fts_available
from insert_data import seed
from library_db import connect, create_schema

CATALOG_SIZE = 2000


@pytest.fixture
def empty_db():
    """Пустая база со схемой «Библиотека»."""
    conn = connect(":memory:")
    create_schema(conn)
    yield conn
    conn.close()


@pytest.fixture
def db(empty_db):
    """База «Библиотека» с демонстрационными данными."""
    seed(empty_db)
    return empty_db


@pytest.fixture
def catalog_size():
    """Размер синтетического каталога в тестах."""
    return CATALOG_SIZE


@pytest.fixture
def catalog():
    """База с синтетическим каталогом книг без индексов."""
    conn = connect(":memory:")
    create_catalog(conn)
    fill_catalog(conn, CATALOG_SIZE)
    yield conn
    conn.close()


@pytest.fixture
def fts(catalog):
    """Каталог с построенным полнотекстовым индексом FTS5."""
    if not fts_available(catalog):
        pytest.skip("SQLite собран без FTS5")
    build_fts(catalog)
    return catalog
