import json
import os
import urllib.request
import urllib.error
from typing import Optional, Tuple


class LLMClassifier:
    """LLM-based classifier supporting Ollama (local) and OpenAI."""

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.provider = self.config.get("llm_provider", "ollama")
        self.model = self.config.get("llm_model", "llama3.2")
        self.enabled = self.config.get("use_llm_for_ambiguous", False)

        if self.provider == "ollama":
            self.base_url = self.config.get("llm_ollama_url", "http://localhost:11434")
        elif self.provider == "openai":
            self.api_key = self.config.get("llm_api_key") or os.getenv("OPENAI_API_KEY")
            self.enabled = self.enabled and bool(self.api_key)

    def classify(self, filename: str, categories: list) -> Tuple[Optional[str], float, str]:
        """
        Use LLM to classify an ambiguous file.
        Returns: (category, confidence, reason)
        """
        if not self.enabled:
            return None, 0, "LLM not enabled in config"

        prompt = (
            f"You are a file classification assistant. "
            f"Given a filename, classify it into ONE of these categories: {', '.join(categories)}.\n\n"
            f"Rules:\n"
            f"- Respond ONLY with the category name, nothing else\n"
            f"- If uncertain, respond with 'Otros'\n"
            f"- Consider the filename context, not just extension\n\n"
            f'Filename: "{filename}"\n\n'
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

        if result in categories:
            return result, 0.75, f"Ollama ({self.model}) classified as {result}"
        else:
            return "Otros", 0.4, f"Ollama suggested '{result}' but not in categories"

    def _classify_openai(self, prompt: str, categories: list) -> Tuple[Optional[str], float, str]:
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)

            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=20
            )

            result = response.choices[0].message.content.strip()

            if result in categories:
                return result, 0.75, f"OpenAI ({self.model}) classified as {result}"
            else:
                return "Otros", 0.4, f"OpenAI suggested '{result}' but not in categories"

        except ImportError:
            return None, 0, "OpenAI library not installed (pip install openai)"
