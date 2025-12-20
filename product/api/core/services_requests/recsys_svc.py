from typing import Any
from .base import BaseSvc

__all__ = ["RecSysSvc"]

class RecSysSvc(BaseSvc):
    PREDICT_SCORES_ENNDPOINT = "/predict-scores"

    async def predict_scores(self, 
                             voted_places: list[dict[str, Any]], 
                             places_scores: list[float], 
                             estimated_places: list[dict[str, Any]]
                            ) -> list[float]:
        if len(voted_places) != len(places_scores):
            raise ValueError("`voted_places` and `places_scores` should have a same length.")
        request = {
            "voted_places": voted_places,
            "places_scores": places_scores,
            "estimated_places": estimated_places
        }
        response = await self.post(self.PREDICT_SCORES_ENNDPOINT, request)
        resp_data: dict[str, Any] = response.json()
        return resp_data.get("estimated_scores", [])