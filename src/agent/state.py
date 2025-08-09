from typing import List, Optional, TypedDict

from langchain_core.messages import BaseMessage

from browser_controller.base import BaseBrowserController


class AgentState(TypedDict):
    task: str
    browser: "BaseBrowserController"
    screenshot: Optional[str]
    messages: List[BaseMessage]
    action_queue: list
    current_step: int
    completed: bool
    error: Optional[str]
    history: List[str]
    goal_achieved: Optional[bool]
    goal_failed: Optional[bool]
