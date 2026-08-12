"""OpenAI-compatible AI client for summarization and chat."""

import os

from openai import OpenAI

from .config import load_config


class AIWebClient:
    def __init__(self):
        cfg = load_config()
        timeout = float(os.getenv("API_TIMEOUT", "60"))
        self.client = OpenAI(
            base_url=cfg["base_url"], api_key=cfg["api_key"], timeout=timeout
        )
        self.model = cfg["model"]
        self.temperature = cfg["temperature"]

    def chat(self, messages: list[dict]) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=False,
                temperature=self.temperature,
            )
            content = response.choices[0].message.content
        except Exception as e:
            raise Exception(f"AI client error: {str(e)}") from e
        return content or ""

    def chat_stream(self, messages: list[dict]) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                stream=True,
                temperature=self.temperature,
            )
        except Exception as e:
            raise Exception(f"AI client error: {str(e)}") from e
        full_response = ""
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                full_response += chunk.choices[0].delta.content
        return full_response
