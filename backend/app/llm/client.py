import httpx
from backend.app.schemas.message import ChatMessage
from typing import List



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


# if __name__ == "__main__":
    # import os
    # import asyncio
    # from dotenv import load_dotenv

    # load_dotenv()

    # API_URL = os.getenv("LM_STUDIO_API_URL")
    # LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL")

    # lm_client = LMStudioClient(api_url=API_URL, model=LM_STUDIO_MODEL)
    # response = asyncio.run(lm_client.generate_text(prompt="Hello, how are you?"))
    # print(response)