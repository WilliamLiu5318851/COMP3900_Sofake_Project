import re
from database.db import insert_news, get_all_news
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