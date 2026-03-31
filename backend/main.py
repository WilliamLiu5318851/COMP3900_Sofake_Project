from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database.db import init_db
from services.news_service import create_news, list_news

app = FastAPI()

init_db()

origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class NewsCreate(BaseModel):
    content: str


@app.get("/")
def root():
    return {"message": "Backend is running"}


@app.get("/healthcheck")
def healthcheck():
    return {"status": "healthy"}


@app.post("/api/news")
def submit_news(news: NewsCreate):
    try:
        return create_news(news.content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/news")
def get_news():
    return list_news()