from app.engines.sdk import sdk

class MLClient:
    def evaluate_message(self, content: str):
        # Use Veridian OSE Engine
        result = sdk.evaluate_output(prompt="User Message", output=content)
        
        if result["decision"] == "block":
            return {
                "classification": "risky",
                "severity": "high",
                "remediation": "Blocked by OSE Engine: Harmful content or PII detected."
            }
        elif result["decision"] == "flag":
             return {
                "classification": "risky",
                "severity": "medium",
                "remediation": "Flagged by OSE Engine: Potential hallucination or low confidence."
            }
            
        return {
            "classification": "safe",
            "severity": "low",
            "remediation": None
        }

    def detect_anomaly(self, features: dict):
        # Placeholder for future AIM integration if needed
        # For now, keep dummy or remove if unused
        import random
        score = random.random()
        return {
            "anomaly_score": score,
            "is_anomaly": score > 0.8
        }

ml_client = MLClient()
