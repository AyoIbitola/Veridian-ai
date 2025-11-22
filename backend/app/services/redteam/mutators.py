import random
import base64

from app.engines.llm import llm_engine

class Mutator:
    def apply_encoding(self, text: str) -> str:
        # Simple base64 encoding as a mutation
        return base64.b64encode(text.encode()).decode()

    def apply_synonyms(self, text: str) -> str:
        # Use LLM for synonyms if available
        prompt = f"Rewrite the following text using synonyms but keeping the same meaning: '{text}'. Return ONLY the rewritten text."
        rewritten = llm_engine.generate_text(prompt, temperature=0.7)
        if rewritten:
            return rewritten.strip()
            
        # Fallback to simple replacement
        replacements = {"delete": "remove", "drop": "discard", "exec": "run"}
        for k, v in replacements.items():
            text = text.replace(k, v)
        return text

    def apply_temperature(self, text: str) -> str:
        # Use LLM to rephrase with high temperature
        prompt = f"Rephrase the following text in a creative way: '{text}'. Return ONLY the rephrased text."
        rewritten = llm_engine.generate_text(prompt, temperature=0.9)
        if rewritten:
            return rewritten.strip()
            
        return f"{text} {random.randint(0, 100)}"

mutator = Mutator()
