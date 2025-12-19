import os
import sys

from pathlib import Path
from typing import Any, AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from asyncpg import create_pool, Connection, Pool

sys.path.append(str(Path(__file__).parent.absolute()))

from core import UsersWorker, PlacesWorker, LLMSvc, RecSysSvc

DATABASE_URL: str = os.getenv("DATABASE_URL")
LLM_URL: str = "http://llm:8000"
RECSYS_URL: str = "http://recsys:8000"

pool: Pool
users_worker: UsersWorker
places_worker: PlacesWorker
llm_svc: LLMSvc
recsys_svc: RecSysSvc

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global pool, users_worker, places_worker
    pool = await create_pool(dsn=DATABASE_URL, min_size=5, max_size=20)
    users_worker = UsersWorker(pool)
    places_worker = PlacesWorker(pool)
    llm_svc = LLMSvc(LLM_URL)
    recsys_svc = RecSysSvc(RECSYS_URL)
    if not await llm_svc.check_alive():
        raise ValueError(f"Can't connect to `{llm_svc.svc_url}`")
    if not await recsys_svc.check_alive():
        raise ValueError(f"Can't connect to `{recsys_svc.svc_url}`")
    
    yield
    
    if pool:
        await pool.close()

app: FastAPI = FastAPI(lifespan=lifespan)

@app.get("/ping")
async def ping() -> dict[str, str]:
    return {"service": "api"}

@app.get("/check-db")
async def check_db() -> dict[str, Any]:
    try:
        async with pool.acquire() as conn:
            conn: Connection
            result = await conn.fetchval("SELECT 1")
            if result == 1:
                return {"database": "connected"}
            else:
                raise ValueError(f"`SELECT 1` returned `{result}`")
    except Exception as e:
        return {"database": "error", "error": str(e)}

@app.post("/add-comment-data")
async def add_comment_data(full_data: dict[str, Any]) -> dict[str, Any]:
    try:
        user_id: str = full_data["user_id"]
        place_id: int = full_data["place_id"]
        name: str = full_data["name"]
        town: str = full_data["town"]
        place_type: str = full_data["place_type"]
        score: float = full_data["score"]
        features: dict[str, float] = full_data["features"]
    except KeyError as e:
        return {"status": "error", "error": f"Required key `{e}` missed"}
    for feature in places_worker.FEATURES:
        if feature not in features:
            return {"status": "error", "error": f"Feature `{feature}` missed"}
    await users_worker.add_user(user_id)
    ok_vote: bool = await users_worker.vote(user_id, place_id, score)
    if ok_vote:
        await places_worker.upsert_place(place_id, name, town, place_type, features)
    return {"status": "ok"}

@app.post("/add-comment")
async def add_comment(messages: list[dict[str, str]]) -> dict[str, str]:
    ...

@app.post("/get-recommendation")
async def add_comment(messages: list[dict[str, str]]) -> dict[str, str]:
    ...

@app.post("/process-messages")
async def process_messages(request: dict[str, Any]) -> dict[str, Any]:
    ...