import json
import os
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

CATALOG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "3b_catalog.json")

def _load_catalog() -> dict:
    try:
        with open(CATALOG_PATH, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Catalog not found at {CATALOG_PATH}")
        return {"capabilities": {}}
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON in catalog at {CATALOG_PATH}")
        return {"capabilities": {}}

# Load catalog into memory
CATALOG = _load_catalog()

def resolve_tools_for_capability(capability_id: str, dynamic_tools: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Resolves a capability ID to a list of 3-4 tool options.
    If capability is 'industry_specific', it validates and returns the dynamic_tools from the LLM.
    Otherwise, it pulls from the curated catalog.
    """
    if capability_id == "industry_specific":
        if dynamic_tools and isinstance(dynamic_tools, list):
            # Ensure the dynamic tools have the required shape
            valid_tools = []
            for t in dynamic_tools:
                if isinstance(t, dict) and "name" in t:
                    valid_tools.append({
                        "name": str(t.get("name")),
                        "cost_tier": str(t.get("cost_tier", "Professional")),
                        "feasibility": str(t.get("feasibility", "Self-serve")),
                        "pros": str(t.get("pros", "")),
                        "cons": str(t.get("cons", ""))
                    })
            return valid_tools[:4]
        return []
        
    cap_data = CATALOG.get("capabilities", {}).get(capability_id)
    if not cap_data:
        logger.warning(f"Capability '{capability_id}' not found in curated catalog.")
        return []
        
    tools = cap_data.get("tools", [])
    # Return the first 4 tools to ensure a variety of feasibility/cost tiers
    return tools[:4]

def get_all_capabilities() -> List[str]:
    """Returns a list of all valid capability IDs (plus industry_specific) to pass to the LLM."""
    caps = list(CATALOG.get("capabilities", {}).keys())
    if "industry_specific" not in caps:
        caps.append("industry_specific")
    return caps
