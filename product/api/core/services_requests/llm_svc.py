from typing import Any
from enum import Enum
from .base import BaseSvc

__all__ = ["MessagesType", "LLMSvc"]

class MessagesType(Enum):
    COMMENT = "comment"
    RECOMMEND = "recommend"
    OTHER = "other"

class LLMSvc(BaseSvc):
    CLASSIFY_MSG_ENDPOINT = "/classify-message"
    COMMENT_DATA_ENDPOINT = "/extract-comment-data"
    RECOMMEND_DATA_ENDPOINT = "/extract-recommendation-data"

    async def classify_messages(self, messages: list[dict[str, str]]) -> MessagesType:
        request = {"messages": messages}
        response = await self.post(self.CLASSIFY_MSG_ENDPOINT, request)
        resp_data: dict[str, str] = response.json()
        return MessagesType(resp_data.get("type", "other"))
    
    async def extract_comment_data(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        request = {"messages": messages}
        response = await self.post(self.COMMENT_DATA_ENDPOINT, request)
        return response.json()
    
    async def extract_recommendation_data(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        request = {"messages": messages}
        response = await self.post(self.RECOMMEND_DATA_ENDPOINT, request)
        return response.json()
