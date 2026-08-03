import json
from typing import Dict, Any
from .client import call_anthropic
from promppts.CompetencyDiscoveryService import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

def run(input_data: Dict[str, Any]) -> Dict[str, Any]:
    user_prompt = USER_PROMPT_TEMPLATE.format(user_input_json=json.dumps(input_data, indent=2))
    return call_anthropic(SYSTEM_PROMPT, user_prompt)
