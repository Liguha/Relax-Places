import os
import sys

from pathlib import Path
from typing import Any, AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import FastAPI
from asyncpg import create_pool, Connection, Pool

sys.path.append(str(Path(__file__).parent.absolute()))

from core import UsersWorker, PlacesWorker, LLMSvc, RecSysSvc, MessagesType, should_recalculate

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
    global pool, users_worker, places_worker, llm_svc, recsys_svc
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

# {
#     "user_id": <user_id>,
#     "place_id": <place_id>,
#     "name": <place_name>,
#     "description": <description_str>
#     "town": <town_name>,
#     "place_type": <place_type>,
#     "score": <0-1_float>,
#     "features": {
#         "natural_scenery": <0-1_float>,
#         "cultural_richness": <0-1_float>,
#         "adventure_level": <0-1_float>,
#         "family_friendliness": <0-1_float>,
#         "beach_quality": <0-1_float>,
#         "mountain_terrain": <0-1_float>,
#         "urban_vibrancy": <0-1_float>,
#         "food_variety": <0-1_float>,
#         "accommodation_quality": <0-1_float>,
#         "transportation_accessibility": <0-1_float>,
#         "cost_level": <0-1_float>,
#         "safety": <0-1_float>,
#         "relaxation_level": <0-1_float>,
#         "nightlife_intensity": <0-1_float>,
#         "historical_significance": <0-1_float>
#     }
# }
@app.post("/add-comment-data")
async def add_comment_data(full_data: dict[str, Any]) -> dict[str, Any]:
    try:
        user_id: str = full_data["user_id"]
        place_id: int = full_data["place_id"]
        name: str = full_data["name"]
        description: str = full_data["description"]
        town: str = full_data["town"]
        place_type: str = full_data["place_type"]
        score: float = full_data["score"]
        features: dict[str, str | float] = full_data["features"]
        for feature in places_worker.FEATURES:
            if feature not in features:
                return {"status": "error", "error": f"Feature `{feature}` missed"}
        await users_worker.add_user(user_id)
        ok_vote: bool = await users_worker.vote(user_id, place_id, score)
        if ok_vote:
            await places_worker.upsert_place(place_id, name, description, town, place_type, features)
        return {"status": "ok"}
    except KeyError as e:
        return {"status": "error", "error": f"Required key `{e}` missed"}
    except:
        return {"status": "error"}

# {
#     "user_id": <user_id>,
#     "messages": [
#         {
#             "role": "user" / "bot",
#             "content": <content_str>
#         },
#         ...
#     ]
# }
@app.post("/add-comment")
async def add_comment(request: dict[str, Any]) -> dict[str, str]:
    try:
        user_id: str = request["user_id"]
        messages: list[dict[str, str]] = request["messages"]
        comment_data = await llm_svc.extract_comment_data(messages)
        comment_data["user_id"] = user_id
        await add_comment_data(comment_data)
        unproc, total = await users_worker.get_n_votes(user_id)
        if should_recalculate(unproc, total):
            voted_places = await users_worker.get_voted_places(user_id)
            scores: list[float] = []
            for place in voted_places:
                scores.append(place.pop("score"))
            all_places = await places_worker.all_places()
            scores = await recsys_svc.predict_scores(voted_places, scores, all_places)
            if len(scores) > 0:
                places_ids = [place["place_id"] for place in all_places]
                await users_worker.set_virtual_scores(user_id, places_ids, scores)
                await users_worker.clear_unprocessed_votes(user_id)
        return {"status": "ok"}
    except:
        return {"status": "error"}

# {
#     "user_id": <user_id>,
#     "messages": [
#         {
#             "role": "user" / "bot",
#             "content": <content_str>
#         },
#         ...
#     ]
# }
@app.post("/get-recommendation")
async def get_recommendation(request: dict[str, Any]) -> dict[str, str]:
    try:
        user_id: str = request["user_id"]
        messages: list[dict[str, str]] = request["messages"]
        reccomend_data = await llm_svc.extract_recommendation_data(messages)
        disallowed_places = await users_worker.get_voted_place_ids(user_id)
        allowed_types = reccomend_data["allowed_types"]
        allowed_towns = reccomend_data["allowed_towns"]
        best_predicts = await users_worker.best_predicts(user_id, 20, disallowed_places, allowed_types, allowed_towns)
        meta = await places_worker.get_meta(best_predicts)
        return {"status": "ok", "predicts": meta}
    except:
        return {"status": "error"}

# {
#     "user_id": <user_id>,
#     "messages": [
#         {
#             "role": "user" / "bot",
#             "content": <content_str>
#         },
#         ...
#     ]
# }
@app.post("/process-messages")
async def process_messages(request: dict[str, Any]) -> dict[str, Any]:
    try:
        user_id: str = request["user_id"]
        messages: list[dict[str, str]] = request["messages"]
        mtype = await llm_svc.classify_messages(messages)
        if mtype == MessagesType.COMMENT:
            return await add_comment(request)
        if mtype == MessagesType.RECOMMEND:
            return await get_recommendation(request)
        return {"status": "error", "error": "Not enought information provided"}
    except KeyError as e:
        return {"status": "error", "error": f"Required key `{e}` missed"}
    except:
        return {"status": "error"}