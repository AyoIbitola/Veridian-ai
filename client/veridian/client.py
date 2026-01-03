import requests
from typing import Dict, Any, Optional

class Veridian:
    def __init__(self, api_key: str, base_url: str = "https://veridian-ai.onrender.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

    def check_prompt(self, text: str, agent_id: int = 1) -> Dict[str, Any]:
        """
        Check if an inbound user prompt is safe.
        """
        url = f"{self.base_url}/monitor/message"
        payload = {
            "content": text,
            "direction": "in",
            "agent_id": agent_id,
            "tenant_id": 1 # Should be inferred from key in real app
        }
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"allowed": False, "reason": f"Connection Error: {e}"}

    def check_output(self, text: str, agent_id: int = 1) -> Dict[str, Any]:
        """
        Check if an outbound agent response is safe.
        """
        url = f"{self.base_url}/monitor/message"
        payload = {
            "content": text,
            "direction": "out",
            "agent_id": agent_id,
            "tenant_id": 1
        }
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"allowed": False, "reason": f"Connection Error: {e}"}

    def log_action(self, tool_name: str, tool_args: str, agent_id: int = 1) -> Dict[str, Any]:
        """
        Log and check an agent tool call.
        """
        url = f"{self.base_url}/webhook/agent_event"
        payload = {
            "event_type": "tool_call",
            "agent_id": agent_id,
            "tool_name": tool_name,
            "tool_args": tool_args,
            "timestamp": "2023-01-01T00:00:00Z" # Should be current time
        }
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "reason": str(e)}

    def run_redteam(self, user_intent: str, target_description: str) -> Dict[str, Any]:
        """
        Trigger a red team campaign.
        """
        url = f"{self.base_url}/redteam/campaign"
        payload = {
            "tenant_id": 1,
            "user_intent": user_intent,
            "target_description": target_description
        }
        try:
            response = requests.post(url, json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "reason": str(e)}

    def sandbox_process(self, filename: str, content: bytes, instruction: str = "extract_summary") -> Dict[str, Any]:
        """
        Send a file to the Veridian Sandbox for safe extraction.
        """
        url = f"{self.base_url}/sandbox/process"
        files = {
            'file': (filename, content)
        }
        data = {
            'instruction': instruction
        }
        # Override headers to remove Content-Type JSON, allowing requests to set multipart boundary
        headers = self.headers.copy()
        headers.pop("Content-Type", None)
        
        try:
            response = requests.post(url, files=files, data=data, headers=headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "reason": str(e)}
