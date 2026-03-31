import re
from database.db import insert_news, get_all_news


def is_valid_text(text: str):
    return bool(re.search(r"[a-zA-Z0-9]", text))


def create_news(content: str):

    content = content.strip()

    if not content:
        raise ValueError("News content cannot be empty")

    if not is_valid_text(content):
        raise ValueError("News must contain meaningful text")

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