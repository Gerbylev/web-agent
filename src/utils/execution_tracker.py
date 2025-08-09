import time
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class StepResult:
    step_num: int
    total_steps: int
    task: str
    success: bool
    execution_time: float
    error: str = None
    actions: List[str] = field(default_factory=list)


@dataclass
class ExecutionMetrics:
    start_time: float = field(default_factory=time.time)
    steps: List[StepResult] = field(default_factory=list)
    total_time: float = 0.0
    success: bool = False

    def add_step(self, result: StepResult):
        self.steps.append(result)

    def finish(self):
        self.total_time = time.time() - self.start_time

    def get_history(self) -> List[str]:
        history = []
        for step in self.steps:
            if step.error:
                history.append(f"[ШАГ {step.step_num}/{step.total_steps}] ОШИБКА ({step.execution_time:.1f}с): {step.error}")
            else:
                history.append(f"[ШАГ {step.step_num}/{step.total_steps}] ВЫПОЛНЕНО ({step.execution_time:.1f}с): {step.task}")
                for action in step.actions:
                    history.append(f"  → {action}")
        return history


def create_step_result(step_num: int, total_steps: int, task: str, agent_result: Dict, execution_time: float) -> StepResult:
    if agent_result.get("error"):
        return StepResult(step_num=step_num, total_steps=total_steps, task=task, success=False, execution_time=execution_time, error=agent_result["error"])
    else:
        return StepResult(
            step_num=step_num, total_steps=total_steps, task=task, success=True, execution_time=execution_time, actions=agent_result.get("history", [])
        )
