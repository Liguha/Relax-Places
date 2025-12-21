from httpx import AsyncClient, Response
from typing import Any

__all__ = ["BaseSvc"]

class BaseSvc:
    def __init__(self, svc_url: str) -> None:
        self._svc_url = svc_url
    
    async def check_alive(self) -> bool:
        resp = await self.get("/ping")
        return resp.status_code == 200

    @property
    def svc_url(self) -> str:
        return self._svc_url
    
    def endpoint_url(self, endpoint: str) -> str:
        return f"{self.svc_url}{endpoint}"
    
    async def get(self, endpoint: str) -> Response:
        async with AsyncClient() as client:
            return await client.get(self.endpoint_url(endpoint))
        return None
    
    async def post(self, endpoint: str, data: dict[str, Any]) -> Response:
        async with AsyncClient() as client:
            return await client.post(self.endpoint_url(endpoint), json=data)
        return None