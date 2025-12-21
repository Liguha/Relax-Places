from typing import Any
from fastapi import FastAPI

app: FastAPI = FastAPI()

@app.get("/ping")
async def ping() -> dict[str, str]:
    return {"service": "recsys"}

# {
#     "voted_places": [
#         {
#             "type": <place_type_str>
#             "natural_scenery": <0-1_float>,
#             "cultural_richness": <0-1_float>,
#             "adventure_level": <0-1_float>,
#             "family_friendliness": <0-1_float>,
#             "beach_quality": <0-1_float>,
#             "mountain_terrain": <0-1_float>,
#             "urban_vibrancy": <0-1_float>,
#             "food_variety": <0-1_float>,
#             "accommodation_quality": <0-1_float>,
#             "transportation_accessibility": <0-1_float>,
#             "cost_level": <0-1_float>,
#             "safety": <0-1_float>,
#             "relaxation_level": <0-1_float>,
#             "nightlife_intensity": <0-1_float>,
#             "historical_significance": <0-1_float>
#         },
#         ...
#     ],
#     "places_scores": [<0-1_float>, ...],
#     "estimated_places": [
#         {
#             "type": <place_type_str>
#             "natural_scenery": <0-1_float>,
#             "cultural_richness": <0-1_float>,
#             "adventure_level": <0-1_float>,
#             "family_friendliness": <0-1_float>,
#             "beach_quality": <0-1_float>,
#             "mountain_terrain": <0-1_float>,
#             "urban_vibrancy": <0-1_float>,
#             "food_variety": <0-1_float>,
#             "accommodation_quality": <0-1_float>,
#             "transportation_accessibility": <0-1_float>,
#             "cost_level": <0-1_float>,
#             "safety": <0-1_float>,
#             "relaxation_level": <0-1_float>,
#             "nightlife_intensity": <0-1_float>,
#             "historical_significance": <0-1_float>
#         },
#         ...
#     ]
# }
@app.post("/predict-scores")
async def predict_scores(request: dict[str, Any]) -> dict[str, Any]:
    # PLACEHOLDER / ANSWER TEMPLATE
    return {
        "status": "ok",
        "estimated_scores": [0.5] * len(request["estimated_places"])
    }