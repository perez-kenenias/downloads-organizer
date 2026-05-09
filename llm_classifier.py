import json
import os
from typing import Optional, Tuple

class LLMClassifier:
    """Optional LLM-based classifier for ambiguous files."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.enabled = bool(self.api_key)
        
    def classify(self, filename: str, categories: list) -> Tuple[Optional[str], float, str]:
        """
        Use OpenAI to classify an ambiguous file.
        Returns: (category, confidence, reason)
        """
        if not self.enabled:
            return None, 0, "LLM not configured"
        
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            
            prompt = f"""You are a file classification assistant. 
Given a filename, classify it into one of these categories:
{', '.join(categories)}

Rules:
- Respond ONLY with the category name
- If uncertain, respond with "Otros"
- Consider the filename context, not just extension

Filename: "{filename}"

Category:"""
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=20
            )
            
            result = response.choices[0].message.content.strip()
            
            # Validate the result is one of our categories
            if result in categories:
                return result, 0.75, f"LLM classified as {result}"
            else:
                return "Otros", 0.4, f"LLM suggested '{result}' but not in categories"
                
        except Exception as e:
            return None, 0, f"LLM error: {str(e)}"
