from typing import Any
from fastapi import FastAPI

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
    # PLACEHOLDER / ANSWER TEMPLATE
    return {
        "status": "ok",
        "type": "recommend"
    }

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
    # PLACEHOLDER / ANSWER TEMPLATE
    return {
        "status": "ok",
        "place_id": 123,
        "name": "Some hotel",
        "description": "...",
        "town": "Moscow",
        "place_type": "Hotel",
        "score": 0.5,
        "features": {
            "natural_scenery": 0.5,
            "cultural_richness": 0.5,
            "adventure_level": 0.5,
            "family_friendliness": 0.5,
            "beach_quality": 0.5,
            "mountain_terrain": 0.5,
            "urban_vibrancy": 0.5,
            "food_variety": 0.5,
            "accommodation_quality": 0.5,
            "transportation_accessibility": 0.5,
            "cost_level": 0.5,
            "safety": 0.5,
            "relaxation_level": 0.5,
            "nightlife_intensity": 0.5,
            "historical_significance": 0.5
        }
    }

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
async def cextract_recommendation_data(request: dict[str, Any]) -> dict[str, Any]:
    # PLACEHOLDER / ANSWER TEMPLATE
    return {
        "status": "ok",
        "allowed_types": ["Hotel", "Park"],
        "allowed_towns": ["Moscow"]
    }