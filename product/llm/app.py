import os
import sys
from typing import Any
from pathlib import Path
from fastapi import FastAPI
from openai import AsyncOpenAI

sys.path.append(str(Path(__file__).parent.absolute()))

from core import get_messages_type, get_recommendation_data, get_place_features, get_place_geopos_id

LLM_BASE_URL: str = os.getenv("LLM_BASE_URL")
LLM_API_KEY: str = os.getenv("LLM_API_KEY")
LLM_CLIENT = AsyncOpenAI(
    base_url=LLM_BASE_URL,
    api_key=LLM_API_KEY
)

app: FastAPI = FastAPI()

@app.get("/ping")
async def ping() -> dict[str, str]:
    return {"service": "llm"}

# {
#     "messages": [
#         {
#             "role": "user" / "bot",
#             "content": <content_str>
#         },
#         ...
#     ]
# }
@app.post("/classify-message")
async def classify_message(request: dict[str, Any]) -> dict[str, Any]:
    try:
        messages = request["messages"]
        mtype = await get_messages_type(LLM_CLIENT, messages)
        return {
            "status": "ok",
            "type": mtype
        }
    except KeyError as e:
        return {"status": "error", "error": f"Required key `{e}` missed"}
    except:
        return {"status": "error"}

# {
#     "messages": [
#         {
#             "role": "user" / "bot",
#             "content": <content_str>
#         },
#         ...
#     ]
# }
@app.post("/extract-comment-data")
async def extract_comment_data(request: dict[str, Any]) -> dict[str, Any]:
    try:
        messages = request["messages"]
        place_data = await get_place_features(LLM_CLIENT, messages)
        place_id = await get_place_geopos_id(LLM_CLIENT, messages)
        place_data["place_id"] = place_id
        if place_data is None:
            return {"status": "error", "error": "Can't extract place information"}
    except KeyError as e:
        return {"status": "error", "error": f"Required key `{e}` missed"}
    except:
        return {"status": "error"}

# {
#     "messages": [
#         {
#             "role": "user" / "bot",
#             "content": <content_str>
#         },
#         ...
#     ]
# }
@app.post("/extract-recommendation-data")
async def extract_recommendation_data(request: dict[str, Any]) -> dict[str, Any]:
    try:
        messages = request["messages"]
        types, towns = get_recommendation_data(LLM_CLIENT, messages)
        return {
            "status": "ok",
            "allowed_types": types,
            "allowed_towns": towns
        }
    except KeyError as e:
        return {"status": "error", "error": f"Required key `{e}` missed"}
    except:
        return {"status": "error"}