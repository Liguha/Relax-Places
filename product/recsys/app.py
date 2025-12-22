import os
from typing import Any
from pathlib import Path
from fastapi import FastAPI
import pandas as pd
import numpy as np
from catboost import CatBoostRegressor

app: FastAPI = FastAPI()

_model: CatBoostRegressor | None = None

# Фичи, используемые в модели 
FEATURES = [
    "natural_scenery",
    "cultural_richness",
    "adventure_level",
    "family_friendliness",
    "beach_quality",
    "mountain_terrain",
    "urban_vibrancy",
    "food_variety",
    "accommodation_quality",
    "transportation_accessibility",
    "cost_level",
    "safety",
    "relaxation_level",
    "nightlife_intensity",
    "historical_significance"
]

def get_model() -> CatBoostRegressor:
    """Загрузка модели"""
    global _model
    if _model is None:
        model_path = os.getenv("MODEL_PATH", "/models/model.cbm")
        if not Path(model_path).exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")
        _model = CatBoostRegressor()
        _model.load_model(model_path)
    return _model

def build_user_profile(voted_places: list[dict[str, Any]], places_scores: list[float]) -> dict[str, Any]:
    """Строит профиль пользователя из оцененных мест"""
    if not voted_places or not places_scores:
        profile = {
            "u_mean_rating": 0.5,
            "u_std_rating": 0.0,
            "u_cnt": 0
        }
        for f in FEATURES:
            profile[f"u_mean_{f}"] = 0.0
        return profile
    
    places_data = []
    for place in voted_places:
        place_data = place.get("place", place)
        place_dict = {}
        for f in FEATURES:
            if f in place_data:
                place_dict[f] = place_data[f]
            else:
                place_dict[f] = 0.0
        places_data.append(place_dict)
    
    df = pd.DataFrame(places_data)
    df["rating"] = places_scores
    
    u_mean_rating = df["rating"].mean()
    u_std_rating = df["rating"].std()
    if pd.isna(u_std_rating):
        u_std_rating = 0.0
    u_cnt = len(df)
    
    profile = {
        "u_mean_rating": float(u_mean_rating),
        "u_std_rating": float(u_std_rating),
        "u_cnt": int(u_cnt)
    }
    
    for f in FEATURES:
        if f in df.columns:
            profile[f"u_mean_{f}"] = float(df[f].mean())
        else:
            profile[f"u_mean_{f}"] = 0.0
    
    return profile

def prepare_features(estimated_places: list[dict[str, Any]], user_profile: dict[str, Any]) -> pd.DataFrame:
    """Подготавливает фичи для предсказания"""
    df = pd.DataFrame(estimated_places)
    
    for key, value in user_profile.items():
        df[key] = value
    
    for f in FEATURES:
        if f in df.columns:
            u_mean_key = f"u_mean_{f}"
            if u_mean_key in df.columns:
                df[f"diff_{f}"] = (df[f].astype(float) - df[u_mean_key].astype(float)).abs()
            else:
                df[f"diff_{f}"] = df[f].astype(float).abs()
        else:
            df[f] = 0.0
            df[f"diff_{f}"] = 0.0
    
    feature_cols = FEATURES + [f"diff_{f}" for f in FEATURES] + ["u_cnt", "u_mean_rating", "u_std_rating"]
    
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0.0
    
    return df[feature_cols]

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
    try:
        voted_places: list[dict[str, Any]] = request.get("voted_places", [])
        places_scores: list[float] = request.get("places_scores", [])
        estimated_places: list[dict[str, Any]] = request.get("estimated_places", [])
        
        if not estimated_places:
            return {
                "status": "ok",
                "estimated_scores": []
            }
        
        model = get_model()
        
        user_profile = build_user_profile(voted_places, places_scores)
        
        features_df = prepare_features(estimated_places, user_profile)
        
        predictions = model.predict(features_df)
        
        estimated_scores = [float(pred) for pred in predictions]
        
        return {
            "status": "ok",
            "estimated_scores": estimated_scores
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "estimated_scores": []
        }