"""
Unified LLM client — abstracts Gemini and OpenRouter.
Always use this; never call AI providers directly from services.
"""
import json
import time
import logging
import asyncio
from typing import Optional, Literal
import google.generativeai as genai
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure Gemini
genai.configure(api_key=settings.GEMINI_API_KEY)

Model = Literal[
    "gemini-2.5-flash-lite",
    "mistralai/mistral-7b-instruct",
    "openai/gpt-4o-mini",
]

# Cost per 1k tokens (input/output average)
MODEL_COSTS = {
    "gemini-2.5-flash-lite": 0.0001,
    "mistralai/mistral-7b-instruct": 0.0002,
    "openai/gpt-4o-mini": 0.00015,
}


class LLMResponse:
    def __init__(self, text: str, tokens: int, cost_usd: float, model: str, latency_ms: int):
        self.text = text
        self.tokens = tokens
        self.cost_usd = cost_usd
        self.model = model
        self.latency_ms = latency_ms

    def as_json(self) -> dict:
        """Parse JSON response — strips markdown code fences if present."""
        import re
        text = self.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Fallback: extract the first {...} block from the response
            match = re.search(r'\{[\s\S]*\}', text)
            if match:
                return json.loads(match.group())
            raise


class LLMClient:
    def __init__(self):
        self.gemini_flash = genai.GenerativeModel("gemini-2.5-flash-lite")
        self.gemini_pro = genai.GenerativeModel("gemini-2.5-flash-lite")

    async def complete(
        self,
        prompt: str,
        model: Model = "gemini-2.5-flash-lite",
        max_tokens: int = 2048,
        temperature: float = 0.3,
        json_mode: bool = True,
    ) -> LLMResponse:
        start = time.time()

        if model.startswith("gemini"):
            response = await self._call_gemini(prompt, model, max_tokens, temperature, json_mode)
        else:
            response = await self._call_openrouter(prompt, model, max_tokens, temperature)

        latency_ms = int((time.time() - start) * 1000)
        tokens = response.get("tokens", 0)
        cost = (tokens / 1000) * MODEL_COSTS.get(model, 0.001)

        logger.info(
            f"LLM call | model={model} tokens={tokens} "
            f"cost=${cost:.5f} latency={latency_ms}ms"
        )

        return LLMResponse(
            text=response["text"],
            tokens=tokens,
            cost_usd=cost,
            model=model,
            latency_ms=latency_ms,
        )

    async def _call_gemini(
        self, prompt: str, model: str, max_tokens: int, temperature: float, json_mode: bool
    ) -> dict:
        gemini_model = self.gemini_flash
        config = genai.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        )
        full_prompt = prompt if not json_mode else prompt + "\n\nRespond with valid JSON only, no markdown fences."

        last_exc = None
        for attempt in range(4):  # up to 3 retries
            if attempt > 0:
                wait = 2 ** attempt  # 2s, 4s, 8s
                logger.warning(f"Gemini rate limit — retrying in {wait}s (attempt {attempt+1}/4)")
                await asyncio.sleep(wait)
            try:
                response = await asyncio.wait_for(
                    gemini_model.generate_content_async(full_prompt, generation_config=config),
                    timeout=30.0,
                )
                # response.text raises ValueError if content was blocked; access candidates directly
                try:
                    text = response.text
                except Exception:
                    # Safety block or empty response — try extracting from candidates
                    text = ""
                    if response.candidates:
                        for part in response.candidates[0].content.parts:
                            text += part.text
                if not text:
                    raise ValueError("Gemini returned empty response (possible safety block or MAX_TOKENS)")
                try:
                    tokens = response.usage_metadata.total_token_count
                except Exception:
                    tokens = len(text.split()) * 2
                return {"text": text, "tokens": tokens}
            except Exception as e:
                err_str = str(e)
                # Daily quota exhausted — retrying won't help, fail immediately
                if "exceeded your current quota" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    raise RuntimeError(
                        "GEMINI_QUOTA_EXCEEDED: Daily AI quota reached. Resets at midnight PT (~12:30 PM IST). Try again tomorrow or enable billing at https://ai.google.dev"
                    ) from e
                # Per-minute rate limit — retry with backoff
                if "429" in err_str or "rate" in err_str.lower():
                    last_exc = e
                    continue
                raise
        raise last_exc

    async def _call_openrouter(
        self, prompt: str, model: str, max_tokens: int, temperature: float
    ) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=60.0,
            )
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", 0)
            return {"text": text, "tokens": tokens}

    async def embed(self, text: str) -> list[float]:
        """Generate embedding using Gemini text-embedding-004."""
        result = await asyncio.to_thread(
            genai.embed_content,
            model=settings.EMBEDDING_MODEL,
            content=text,
            task_type="retrieval_document",
        )
        return result["embedding"]


# Singleton
llm_client = LLMClient()
