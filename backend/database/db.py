import sqlite3
import json

DB_NAME = "/app/news.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulation_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_id INTEGER NOT NULL,
            agent_count INTEGER NOT NULL,
            steps INTEGER NOT NULL,
            seed INTEGER NOT NULL,
            intra_cluster_p REAL,
            inter_cluster_m INTEGER,
            agents_per_cluster INTEGER,
            weak_tie_p REAL,
            simulations INTEGER,
            result_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (news_id) REFERENCES news(id)
        )
    """)

    conn.commit()
    conn.close()


def insert_news(content: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO news (content) VALUES (?)",
        (content,)
    )

    conn.commit()
    news_id = cursor.lastrowid
    conn.close()

    return news_id


def get_all_news():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT id, content FROM news ORDER BY id DESC")
    rows = cursor.fetchall()

    conn.close()
    return rows

# get news by its id from the database
def get_news_by_id(news_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT id, content FROM news WHERE id = ?", (news_id,))
    row = cursor.fetchone()
    conn.close()
    return row

# insert a simulation result into simulation_runs table
def insert_simulation_run(
    news_id: int,
    agent_count: int,
    steps: int,
    seed: int,
    intra_cluster_p: float,
    inter_cluster_m: int,
    agents_per_cluster: int,
    weak_tie_p: float,
    simulations: int,
    result_json: dict
):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO simulation_runs (
            news_id,
            agent_count,
            steps,
            seed,
            intra_cluster_p,
            inter_cluster_m,
            agents_per_cluster,
            weak_tie_p,
            simulations,
            result_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            news_id,
            agent_count,
            steps,
            seed,
            intra_cluster_p,
            inter_cluster_m,
            agents_per_cluster,
            weak_tie_p,
            simulations,
            json.dumps(result_json)

    ))
    conn.commit()
    run_id = cursor.lastrowid
    conn.close()
    return run_id

# get one simulation result based on run_id
def get_simulation_by_run_id(run_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        simulation_runs.id, 
        simulation_runs.news_id, 
        news.content, 
        simulation_runs.agent_count, 
        simulation_runs.steps, 
        simulation_runs.seed, 
        simulation_runs.intra_cluster_p, 
        simulation_runs.inter_cluster_m, 
        simulation_runs.agents_per_cluster, 
        simulation_runs.weak_tie_p, 
        simulation_runs.simulations, 
        simulation_runs.result_json, 
        simulation_runs.created_at
    FROM simulation_runs
    JOIN news ON simulation_runs.news_id = news.id
    WHERE simulation_runs.id = ?
    """, (run_id,))

    row = cursor.fetchone()
    conn.close()
    return row

# get all simulation runs, can be used for displaying the content when user press history
def get_all_simulation_runs():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        simulation_runs.id, 
        news.content 
    FROM simulation_runs
    JOIN news ON simulation_runs.news_id = news.id
    ORDER BY simulation_runs.id DESC 
    """)

    rows = cursor.fetchall()
    conn.close()
    return rows

def check_simulation_run_exist(run_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id
    FROM simulation_runs
    WHERE id = ?
    """, (run_id,))

    row = cursor.fetchone()
    conn.close()
    return row is not None

def delete_simulation_run_by_id(run_id: int):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM simulation_runs
        WHERE id = ?
    """, (run_id,))

    conn.commit()
    delete_count = cursor.rowcount
    conn.close()
    return delete_count