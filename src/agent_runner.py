import asyncio
import base64
import time
from typing import Dict, Tuple

from agent.graph import create_agent_graph
from agent.nodes import verify_final_result
from agent.state import AgentState
from browser_controller.playwright_controller import PlaywrightController
from utils.config import CONFIG
from utils.execution_tracker import ExecutionMetrics, create_step_result
from utils.log import get_logger

log = get_logger()


async def take_screenshot(browser: PlaywrightController, step: int, stage: str) -> str:
    filename = f"{CONFIG.output_dir}/{stage}_{step}.png" if step else f"{CONFIG.output_dir}/{stage}.png"
    return await browser.get_screenshot(filename, save_to_disk=True)


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


async def setup_browser(task_data) -> PlaywrightController:
    browser = PlaywrightController(headless=CONFIG.playwright_headless)
    await browser.start()
    await browser.navigate_to(task_data.url)
    return browser


async def execute_step(browser: PlaywrightController, graph, task: str, step_num: int, total_steps: int, metrics: ExecutionMetrics) -> bool:
    start_time = time.time()
    log.info(f"Выполняем шаг {step_num}/{total_steps}: {task}")

    screenshot_before = await take_screenshot(browser, step_num, "step_before")

    initial_state = AgentState(
        task=task,
        screenshot=encode_image(screenshot_before),
        messages=[],
        action_queue=[],
        current_step=0,
        completed=False,
        error=None,
        history=[],
        browser=browser,
        goal_achieved=None,
        goal_failed=None,
    )

    result = await graph.ainvoke(initial_state, {"recursion_limit": 100})
    await take_screenshot(browser, step_num, "step_after")

    execution_time = time.time() - start_time
    step_result = create_step_result(step_num, total_steps, task, result, execution_time)
    metrics.add_step(step_result)

    if result.get("error"):
        log.error(f"Прерывание выполнения на шаге {step_num}")
        return False

    log.info(f"Шаг {step_num} завершен за {execution_time:.1f}с")
    return True

async def verify_final_result_step(browser: PlaywrightController, task_data, metrics: ExecutionMetrics) -> Dict:
    log.info("Проверяем финальный результат...")

    final_screenshot = await take_screenshot(browser, 0, "final_result")
    final_screenshot_b64 = encode_image(final_screenshot)

    return await verify_final_result(screenshot=final_screenshot_b64, expected_result=task_data.result, all_history=metrics.get_history())

async def run_all_tasks(task_data) -> Tuple[ExecutionMetrics, Dict]:
    metrics = ExecutionMetrics()
    graph = create_agent_graph()
    browser = await setup_browser(task_data)
    verification = {"success": False, "details": "Выполнение не завершено", "summary": "Ошибка выполнения"}

    try:
        for i, task in enumerate(task_data.tasks, 1):
            success = await execute_step(browser, graph, task, i, len(task_data.tasks), metrics)

            if not success:
                return metrics, verification

            await asyncio.sleep(1)

        verification = await verify_final_result_step(browser, task_data, metrics)

    except Exception as e:
        log.error(f"Критическая ошибка: {e}")
        verification = {"success": False, "details": str(e), "summary": f"Критическая ошибка: {e}"}
    finally:
        try:
            await browser.close()
        except Exception as e:
            log.error(f"Ошибка закрытия браузера: {e}")

    return metrics, verification


