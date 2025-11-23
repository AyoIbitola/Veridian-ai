import logging
import json
from typing import Dict
import google.generativeai as genai
from app.core.config import settings

class AgentIntentMonitor:
    def __init__(self):
        self.logger = logging.getLogger("Veridian.AIM")
        
        # Initialize Gemini model for LLM-based action evaluation
        try:
            if settings.GEMINI_API_KEY:
                 genai.configure(api_key=settings.GEMINI_API_KEY)
                 self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')
                 self.logger.info("AIM-Engine initialized with Gemini API")
            else:
                 self.logger.warning("GEMINI_API_KEY not set. AIM-Engine running in limited mode.")
                 self.gemini_model = None
        except Exception as e:
            self.logger.warning(f"Failed to initialize Gemini: {e}. Using keyword detection only.")
            self.gemini_model = None
        
        # Fallback keyword list (used if model is not provided)
        self.destructive_commands = [
            "rm -rf", "rm -r", "rm -f", "drop table", "delete from", "shutdown", "curl", "wget",
            "format", "mkfs", "dd if=", ":(){ :|:& };:", "chmod 777", "chown", "mv /", "cp /"
        ]
    
    def detect_with_llm(self, command: str) -> Dict:
        """Uses Gemini API to evaluate command safety."""
        if not self.gemini_model:
            self.logger.warning("Gemini model not available. Falling back to keyword detection.")
            return self._keyword_fallback(command)
        
        # Craft the safety prompt
        safety_prompt = f"""You are an expert AI safety advisor evaluating agent actions.

Respond ONLY in valid JSON using this structure:
{{
    "label": "safe" or "unsafe",
    "risk_score": float (0.0 to 1.0),
    "reason": "short explanation"
}}

Risk scoring standards:
- 1.0: Confirmed destructive/malicious (rm -rf /, drop table, dd if=/dev/zero, format, shutdown, network attacks)
- 0.8: Highly suspicious (chmod 777 /, chown root, unknown scripts, sensitive paths)
- 0.5: Ambiguous/dual-use (wget without context, reading logs, accessing configs)
- 0.2: Low risk but unusual (minor file edits, potentially unsafe commands)
- 0.0: Completely safe (print, read file, arithmetic, navigation)

Evaluate the command for:
1. Destructive file operations (rm -rf, format, drop table, delete from, mkfs, dd if=)
2. Unauthorized data access/exfiltration (copying secrets, network transfers, DB dumps)
3. Privilege escalation (sudo misuse, chown root, chmod 777)
4. Network attacks/scanning (nmap, nc, port scans, malicious downloads)
5. Malware/injection patterns (encoded payloads, malicious pipes/redirects)

Command to evaluate: {command}"""
        
        try:
            # Generate response using Gemini with JSON mode
            response = self.gemini_model.generate_content(
                safety_prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                    max_output_tokens=200
                )
            )
            
            # Parse JSON response
            result_text = response.text.strip()
            parsed = json.loads(result_text)
            
            risk_score = float(parsed.get("risk_score", 0.0))
            label = parsed.get("label", "safe")
            reason = parsed.get("reason", "")

            return {
                "risk_score": risk_score,
                "label": label,
                "reasons": [reason],
                "method": "gemini"
            }

        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse Gemini JSON: {e}")
            return self._keyword_fallback(command)
        except Exception as e:
            self.logger.error(f"Gemini evaluation failed: {e}")
            return self._keyword_fallback(command)
    
    def _keyword_fallback(self, command: str) -> Dict:
        """Fallback keyword-based detection."""
        risk_score = 0.0
        reasons = []
        
        for keyword in self.destructive_commands:
            if keyword in command.lower():
                risk_score = 1.0
                reasons.append(f"Destructive pattern detected: {keyword}")
                break
        
        return {"risk_score": risk_score, "reasons": reasons, "method": "keyword"}

    def analyze_action(self, action: Dict) -> Dict:
        """Analyzes an agent action for security risks."""
        # Extract command from various possible formats
        command = action.get("args", "") or action.get("command", "") or str(action)
        if isinstance(command, dict):
            command = json.dumps(command)
        
        command_str = str(command)

        # 1. Deterministic Pre-check (Fast & Safe)
        pre_check = self._keyword_fallback(command_str)
        if pre_check["risk_score"] >= 1.0:
            self.logger.warning(f"Blocked by pre-check: {pre_check['reasons']}")
            return pre_check
            
        # 2. LLM Evaluation (Deep Analysis)
        return self.detect_with_llm(command_str)

    def evaluate_agent_action(self, action: Dict) -> Dict:
        """Main entry point for action evaluation."""
        analysis = self.analyze_action(action)
        decision = "allow"
        if analysis["risk_score"] > 0.8:
            decision = "flag"
        elif analysis["risk_score"] > 0.3:
            decision = "flag"
            
        result = {
            "decision": decision,
            "analysis": analysis
        }
        self.logger.info(f"Evaluated action: {decision} (Method: {analysis.get('method', 'unknown')})")
        return result
