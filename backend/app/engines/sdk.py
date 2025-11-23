import logging
from typing import Dict, List
from app.engines.pre import PromptRiskEvaluator
from app.engines.ose import OutputSafetyEvaluator
from app.engines.aim import AgentIntentMonitor
from app.engines.rts import RedTeamEngine

class VeridianSDK:
    def __init__(self):
        self.logger = logging.getLogger("Veridian.SDK")
        
        self.pre = PromptRiskEvaluator()
        self.ose = OutputSafetyEvaluator()
        self.aim = AgentIntentMonitor()
        self.rte = RedTeamEngine(safety_evaluator=self.ose)
        
        self.logger.info("Veridian SDK Initialized")

    def evaluate_prompt(self, prompt: str) -> Dict:
        return self.pre.evaluate_prompt(prompt)

    def evaluate_output(self, prompt: str, output: str) -> Dict:
        return self.ose.evaluate_output(prompt, output)

    def evaluate_action(self, action: Dict) -> Dict:
        return self.aim.evaluate_agent_action(action)

    def run_redteam(self, user_prompt: str, target_description: str = "general AI assistant", target_url: str = None, target_config: Dict = None) -> List[Dict]:
        """
        Run red team stress test on a simulated target model.
        
        Args:
            user_prompt: The user intent to test (e.g., "how to make a bomb")
            target_description: Description of target model behavior
            target_url: Optional URL to probe
        
        Returns:
            List of attack results with evaluations
        """
        return self.rte.run_red_team_test(user_prompt, target_description, target_url, target_config)

sdk = VeridianSDK()
