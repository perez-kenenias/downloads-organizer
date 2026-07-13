import json
import os
import re
import urllib.request
import urllib.error
from typing import Optional, Tuple


class LLMClassifier:
    """LLM-based classifier supporting Ollama (local) and any OpenAI-compatible API
    (OpenAI, DeepSeek, Groq, Together...) via llm_base_url."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.provider = self.config.get("llm_provider", "ollama")
        self.model = self.config.get("llm_model", "llama3.2")
        self.enabled = self.config.get("use_llm_for_ambiguous", False)

        if self.provider == "ollama":
            self.base_url = self.config.get("llm_ollama_url", "http://localhost:11434")
        elif self.provider == "openai":
            self.api_key = self.config.get("llm_api_key") or os.getenv("OPENAI_API_KEY")
            # Empty means the openai library default (api.openai.com); set
            # e.g. https://api.deepseek.com to use another compatible provider
            self.base_url = self.config.get("llm_base_url", "") or None
            self.enabled = self.enabled and bool(self.api_key)

    @staticmethod
    def _extract_category(raw: str, categories: list) -> Optional[str]:
        """Normalize an LLM reply to a category name.
        Reasoning models (deepseek-r1, qwq...) prepend <think>...</think> blocks;
        strip them, then match the remainder case-insensitively."""
        text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
        text = text.strip().strip('"\'`.').strip()
        # Keep only the last non-empty line (some models add preamble)
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        if lines:
            text = lines[-1]
        lookup = {c.lower(): c for c in categories}
        return lookup.get(text.lower())

    def classify(self, filename: str, categories: list,
                 content_snippet: Optional[str] = None) -> Tuple[Optional[str], float, str]:
        """
        Use LLM to classify an ambiguous file.
        content_snippet: optional extracted text from inside the file — greatly
        improves accuracy for generically-named files like 'documento(3).pdf'.
        Returns: (category, confidence, reason)
        """
        if not self.enabled:
            return None, 0, "LLM not enabled in config"

        content_block = ""
        if content_snippet:
            content_block = f'\nContent excerpt from the file:\n"""\n{content_snippet[:1500]}\n"""\n'

        prompt = (
            f"You are a file classification assistant. "
            f"Given a filename, classify it into ONE of these categories: {', '.join(categories)}.\n\n"
            f"Rules:\n"
            f"- Respond ONLY with the category name, nothing else\n"
            f"- If uncertain, respond with 'Otros'\n"
            f"- Consider the filename context, not just extension\n"
            f'Filename: "{filename}"\n'
            f"{content_block}\n"
            f"Category:"
        )

        try:
            if self.provider == "ollama":
                return self._classify_ollama(prompt, categories)
            elif self.provider == "openai":
                return self._classify_openai(prompt, categories)
            else:
                return None, 0, f"Unknown provider: {self.provider}"
        except Exception as e:
            return None, 0, f"LLM error: {e}"

    def _classify_ollama(self, prompt: str, categories: list) -> Tuple[Optional[str], float, str]:
        url = f"{self.base_url}/api/chat"
        body = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.1}
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            result = data.get("message", {}).get("content", "").strip()

        category = self._extract_category(result, categories)
        if category:
            return category, 0.75, f"Ollama ({self.model}) classified as {category}"
        else:
            return "Otros", 0.4, f"Ollama suggested '{result[:80]}' but not in categories"

    def _classify_openai(self, prompt: str, categories: list) -> Tuple[Optional[str], float, str]:
        try:
            import openai
            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url  # DeepSeek, Groq, Together, etc.
            client = openai.OpenAI(**kwargs)

            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=200  # reasoning models spend tokens thinking before answering
            )

            result = response.choices[0].message.content.strip()

            category = self._extract_category(result, categories)
            provider_name = self.base_url or "OpenAI"
            if category:
                return category, 0.75, f"{provider_name} ({self.model}) classified as {category}"
            else:
                return "Otros", 0.4, f"{provider_name} suggested '{result[:80]}' but not in categories"

        except ImportError:
            return None, 0, "OpenAI library not installed (pip install openai)"
