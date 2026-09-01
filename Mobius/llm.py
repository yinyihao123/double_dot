from openai import OpenAI
from httpx2 import Client
from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT

class LLMClient:
    def __init__(self, api_key=LLM_API_KEY, base_url=LLM_BASE_URL,
                 model=LLM_MODEL, timeout=LLM_TIMEOUT):
        self.model = model
        self._client_args = {
            "api_key": api_key,
            "base_url": base_url,
            "timeout": timeout,
            "http_client": Client(timeout=timeout, trust_env=False),
        }
        self.client = None

    def ask(self, context: str):
        if self.client is None:
            self.client = OpenAI(**self._client_args)
        response = self.client.chat.completions.create(
            model=self.model, messages=[{"role": "user", "content": context}])
        return response.choices[0].message.content

_default_client = LLMClient()
ask_llm = _default_client.ask
ask_llm_with_context = _default_client.ask
ask_llm_agent = _default_client.ask
