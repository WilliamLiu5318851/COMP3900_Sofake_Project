import json
import sqlite3

DB_NAME = "news.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # table for news submitted
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS news (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT NOT NULL
        )
    """)

    # table for simulation_runs result
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS simulation_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            news_id INTEGER NOT NULL,
            agent_count INTEGER NOT NULL,
            topology TEXT NOT NULL,
            seed INTEGER NOT NULL,
            steps INTEGER NOT NULL,
            role_mix   TEXT NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (news_id) REFERENCES news(id)
        )
    """)

    conn.commit()
    conn.close()

# insert the input news into database
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

#get all news in the database
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
    topology: str,
    seed: int,
    steps: int,
    role_mix:dict,
    result_json: dict
):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO simulation_runs
        (news_id, agent_count, topology, seed, steps, role_mix, result_json)
        VALUES (?,?,?,?,?,?,?)
        """, (
            news_id,
            agent_count,
            topology,
            seed,
            steps,
            json.dumps(role_mix),
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
        simulation_runs.topology, 
        simulation_runs.seed, 
        simulation_runs.steps, 
        simulation_runs.role_mix, 
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

    row = cursor.fetchall()
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