import json
from database.db import (
    insert_news, 
    get_all_news,  
    get_all_simulation_runs, 
    get_simulation_by_run_id,
    check_simulation_run_exist,
    delete_simulation_run_by_id,
)
from services.news_validation import validate_news_content

def create_news(content: str):

    is_valid, message = validate_news_content(content)

    if not is_valid:
        raise ValueError(message)

    content = content.strip()
    news_id = insert_news(content)

    return {
        "id": news_id,
        "content": content
    }


def list_news():

    rows = get_all_news()

    news_list = []

    for row in rows:
        news_list.append({
            "id": row[0],
            "content": row[1]
        })

    return news_list

# history list page
def list_history_runs():
    rows = get_all_simulation_runs()
    history_list = []
    for row in rows:
        history_list.append({
            "run_id": row[0],
            "content": row[1]
        })
    return history_list

# history detail page
def get_history_run_detail(run_id: int):
    row = get_simulation_by_run_id(run_id)
    if not row:
        raise ValueError("History not found")
    
    return {
        "run_id": row[0],
        "news_id": row[1],
        "content": row[2],
        "agent_count": row[3],
        "steps": row[4],
        "seed": row[5],
        "intra_cluster_p": row[6],
        "inter_cluster_m": row[7],
        "agents_per_cluster": row[8],
        "weak_tie_p": row[9],
        "simulations": row[10],
        "result_json": json.loads(row[11]),
        "created_at": row[12],
    }

def delete_history_run(run_id: int):
    if not check_simulation_run_exist(run_id):
        raise ValueError("History run not exits")
    
    delete_count = delete_simulation_run_by_id(run_id)
    if delete_count == 0:
        raise ValueError("History run not found")
    
    return {
        "message": "History run deleted successfully",
        "run_id": run_id
    }