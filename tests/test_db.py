import pytest
import os
import tempfile
from backend.database.db import init_db, insert_news, get_all_news, insert_simulation_run, get_simulation_by_run_id
import json


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


def test_parallel_runs_persistence():
    """Verify the persistence of parallel simulation runs handling massive payload."""
    init_db()
    news_id = insert_news("Test ground truth for parallel runs")
    
    # Create a massive dummy result_json object matching new structure
    dummy_result_json = {
        "run_log": {"run_id": "first_run_id"},
        "signal_drift": {},
        "fuse_evaluations": [{"Total_Deviation": 5.0}],
        "runs": [
            {
                "run_log": {"run_id": "run_0"},
                "signal_drift": {"post_1": []},
                "fuse_evaluations": [{"Total_Deviation": 3.1, "post_id": "post_1"}]
            },
            {
                "run_log": {"run_id": "run_1"},
                "signal_drift": {"post_2": []},
                "fuse_evaluations": [
                    {"Total_Deviation": 4.5, "post_id": "post_2"},
                    {"Total_Deviation": 2.2, "post_id": "post_3"}
                ]
            }
        ]
    }
    
    # 精准匹配 db.py 中的 10 个参数，并且 result_json 传入 dict (底层会自动 dumps)
    run_id = insert_simulation_run(
        news_id=news_id,
        agent_count=20,
        steps=5,
        seed=42,
        intra_cluster_p=0.5,
        inter_cluster_m=2,
        agents_per_cluster=10,
        weak_tie_p=0.05,
        simulations=2,
        result_json=dummy_result_json
    )
    
    assert run_id is not None
    assert run_id > 0
    
    # 直接从数据库底层读取，验证数据序列化与反序列化的完整性
    row = get_simulation_by_run_id(run_id)
    retrieved_json = json.loads(row[11])  # 索引 11 是 result_json 字段
    
    assert len(retrieved_json['runs']) == 2
    assert retrieved_json["runs"][1]["fuse_evaluations"][1]["post_id"] == "post_3"
    assert retrieved_json == dummy_result_json