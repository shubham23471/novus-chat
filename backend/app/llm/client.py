import httpx
from backend.app.schemas.message import ChatMessage
from typing import List, AsyncGenerator
import json


class LMStudioClient:
    DEFAULT_TIMEOUT = 30.0
    HEADER = {"Content-Type": "application/json"}

    def __init__(self, api_url: str | None, model:str | None):
        self.api_url = api_url
        self.model = model

    async def generate_chat_completion(self, messages: List[ChatMessage], 
                            max_tokens: int = 256) -> str:
        payload = {
                    "model": self.model,
                    "messages": [m.model_dump() for m in messages], # Enables multi-turn chat
                    "max_tokens": max_tokens,
                    "temperature": 0.7
                }
        
        try: 
            async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
                response = await client.post(
                    f"{self.api_url}/chat/completions",
                    json=payload,
                    headers=self.HEADER
                )
                response.raise_for_status()
                data = response.json()
        except httpx.RequestError as exc:
            raise RuntimeError(f"An error occurred while requesting {exc.request.url!r}.") from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"LLM Returned an error response {exc.response.status_code} while requesting {exc.request.url!r}.") from exc

        return data["choices"][0]["message"]["content"]


    async def stream_chat_completion(self, 
                                     message: List[ChatMessage],
                                     max_token: int = 256
                                     ) -> AsyncGenerator[str, None]:
        """Stream chat completion from LM Studio API"""
        payload = {
                    "model": self.model,
                    "messages": [m.model_dump() for m in message],
                    "max_tokens": max_token,
                    "temperature": 0.7,
                    "stream": True
                }
        try: 
            async with httpx.AsyncClient(timeout=None) as client:
                response = await client.post(
                    f"{self.api_url}/chat/completions",
                    json=payload,
                    headers=self.HEADER
                )
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line.removeprefix("data: ")
                    if data == "[DONE]":
                        break

                    chunk = json.loads(data)
                    delta = chunk["choices"][0]["delta"]
                    if "content" in delta:
                        yield delta["content"]
        except httpx.RequestError as exc:
            raise RuntimeError(f"An error occurred while requesting {exc.request.url!r}.") from exc

