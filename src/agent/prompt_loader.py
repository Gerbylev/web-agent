import os
from functools import lru_cache
from typing import Dict, Any

import jinja2
import yaml


@lru_cache(maxsize=1)
def load_prompts() -> Dict[str, str]:
    prompts_path = os.path.join(os.path.dirname(__file__), "prompts.yml")
    with open(prompts_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def render_prompt(prompt_name: str, **kwargs: Any) -> str:
    prompts = load_prompts()
    template = jinja2.Template(prompts[prompt_name])
    return template.render(**kwargs)
