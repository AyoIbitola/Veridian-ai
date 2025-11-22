import re
import logging
from typing import Dict, List, Optional

class PromptRiskEvaluator:
    def __init__(self):
        self.logger = logging.getLogger("Veridian.PRE")
        
        # 1. Heuristic / Regex Patterns for known attacks
        self.jailbreak_patterns = [
            r"ignore previous instructions",
            r"do anything now",
            r"you are now in developer mode",
            r"act as a",
            r"unfiltered",
            r"always answer",
            r"DAN mode",
            r"developer mode",
            r"jailbreak",
            r"override all previous",
            r"disregard prior directives"
        ]
        
        self.injection_patterns = [
            r"system prompt",
            r"override",
            r"delete",
            r"update",
            r"ignore",
            r"disregard",
            r"forget",
            r"modify",
            r"alter",
            r"change",
            r"execute",
            r"run",
            r"command",
            r"instruction",
            r"confidential",
            r"secret",
            r"private",
            r"leak",
            r"reveal",
            r"disclose"
        ]
        
        # 2. Advanced ML Classifier (DeBERTa v2)
        try:
            from transformers import pipeline
            self.classifier = pipeline("text-classification", model="protectai/deberta-v3-base-prompt-injection-v2")
            self.logger.info("PRE-Engine DeBERTa v2 model initialized.")
        except ImportError:
            self.logger.warning("Transformers library not found. Falling back to regex only.")
            self.classifier = None
        except Exception as e:
             self.logger.warning(f"Failed to load Transformers model: {e}. Falling back to regex only.")
             self.classifier = None

    def classify_prompt(self, prompt: str) -> Dict[str, float]:
        """Classifies the prompt using Regex and ML."""
        scores = {
            "jailbreak": 0.0,
            "injection": 0.0,
            "harmful_intent": 0.0
        }
        
        # Regex Checks
        for pattern in self.jailbreak_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                scores["jailbreak"] = 1.0
                break
        
        for pattern in self.injection_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                scores["injection"] = 0.8
                break
                
        # ML Check (DeBERTa v2)
        if self.classifier:
            try:
                result = self.classifier(prompt)[0]
                if result['label'] == 'INJECTION':
                    scores["harmful_intent"] = float(result['score'])
                else:
                    scores["harmful_intent"] = 1.0 - float(result['score'])
            except Exception as e:
                self.logger.error(f"Classifier failed: {e}")
        
        return scores

    def calculate_risk_score(self, scores: Dict[str, float]) -> float:
        return max(scores.values())

    def sanitize_prompt(self, prompt: str) -> str:
        sanitized = prompt
        for pattern in self.jailbreak_patterns + self.injection_patterns:
            sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)
        return sanitized

    def evaluate_prompt(self, prompt: str) -> Dict:
        scores = self.classify_prompt(prompt)
        risk_score = self.calculate_risk_score(scores)
        
        decision = "allow"
        if risk_score > 0.7:
            decision = "block"
        elif risk_score > 0.3:
            decision = "flag"
            
        result = {
            "risk_level": "critical" if risk_score > 0.8 else "high" if risk_score > 0.5 else "medium" if risk_score > 0.2 else "low",
            "score": round(risk_score, 2),
            "scores": scores,
            "decision": decision
        }
        
        if risk_score > 0.0:
            result["remediation_suggestion"] = self.sanitize_prompt(prompt)
            
        self.logger.info(f"Evaluated prompt: {decision} (Score: {risk_score:.2f})")
        return result
