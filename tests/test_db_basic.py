import pytest
from backend.database.db import init_db, insert_news, get_all_news


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """
    Run each test against a throwaway SQLite file in a temp directory
    so tests never touch the real news.db.
    """
    import backend.database.db as db_module

    db_file = str(tmp_path / "test_news.db")
    monkeypatch.setattr(db_module, "DB_NAME", db_file)
    yield


def test_basic_crud():
    """Verify the most basic CRUD (Create, Read, Update, Delete) logic"""
    # 1. Initialization (Ensure the table is created successfully)
    init_db()

    # 2. Insert a single news item
    test_str = "This is a basic test content."
    news_id = insert_news(test_str)

    # 3. Verify if the returned ID is valid
    assert news_id is not None
    assert news_id > 0

    # 4. Retrieve all news and compare the content
    news_list = get_all_news()
    # Check the most recently inserted item (since get_all_news uses DESC ordering)
    assert news_list[0][1] == test_str


def test_multiple_inserts_ordering():
    """Verify DESC ordering when multiple items are inserted."""
    init_db()
    insert_news("First article")
    insert_news("Second article")
    insert_news("Third article")

    news_list = get_all_news()
    # DESC order means "Third" should be first
    assert news_list[0][1] == "Third article"
    assert len(news_list) == 3


def test_empty_db_returns_empty_list():
    """An initialised but empty DB should return an empty list."""
    init_db()
    news_list = get_all_news()
    assert news_list == []
