import yaml
import re

class PolicyEngine:
    def evaluate_policy(self, content: str, rules_yaml: str) -> dict:
        try:
            rules = yaml.safe_load(rules_yaml)
        except Exception:
            return {"allowed": True} # Fail open if invalid YAML

        if not rules:
            return {"allowed": True}

        # Check deny list
        deny_list = rules.get("deny", [])
        for term in deny_list:
            if term.lower() in content.lower():
                return {"allowed": False, "reason": f"Policy violation: found denied term '{term}'"}

        # Check regex
        regex_list = rules.get("regex_deny", [])
        for pattern in regex_list:
            if re.search(pattern, content):
                return {"allowed": False, "reason": f"Policy violation: matches regex '{pattern}'"}

        return {"allowed": True}

policy_engine = PolicyEngine()
