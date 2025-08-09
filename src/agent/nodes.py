import asyncio
import base64
import time
from functools import lru_cache
from typing import Dict, List

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI
from PIL import Image, ImageDraw
from pydantic import SecretStr

from agent.models import DecisionResponse, ClickAction, TypeAction, CommandAction, WaitAction, VerificationResult
from agent.prompt_loader import render_prompt
from agent.state import AgentState
from utils.config import CONFIG
from utils.log import get_logger

logger = get_logger()


@lru_cache(maxsize=None)
def _get_base_llm():
    api_key = SecretStr(CONFIG.gpt.token) if isinstance(CONFIG.gpt.token, str) else CONFIG.gpt.token
    return ChatOpenAI(base_url=CONFIG.gpt.url, api_key=api_key, model=CONFIG.gpt.model, temperature=0)


def get_llm(structured_output_class=None):
    llm = _get_base_llm()
    if structured_output_class:
        return llm.with_structured_output(structured_output_class)
    return llm


async def _retry_llm_call(llm, messages, max_retries: int = 3):
    last_exception = None
    for attempt in range(max_retries):
        try:
            return await llm.ainvoke(messages)
        except Exception as e:
            last_exception = e
            logger.warning(f"LLM вызов не удался (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise last_exception
            await asyncio.sleep(2**attempt)
    raise last_exception


def _draw_click_point_on_screenshot(screenshot_path: str, x: int, y: int, output_path: str = None) -> str:
    try:
        if output_path is None:
            output_path = screenshot_path.replace(".png", "_with_click.png")

        with Image.open(screenshot_path) as img:
            draw = ImageDraw.Draw(img)
            radius = 8
            draw.ellipse([x - radius, y - radius, x + radius, y + radius], fill="red", outline="darkred", width=2)
            line_length = 12
            draw.line([x - line_length, y, x + line_length, y], fill="red", width=2)
            draw.line([x, y - line_length, x, y + line_length], fill="red", width=2)
            img.save(output_path)
            return output_path
    except Exception as e:
        logger.error(f"Ошибка рисования точки клика: {e}")
        return screenshot_path


def _convert_actions_to_queue(actions: List) -> List[Dict]:
    actions_list = []
    for action in actions:
        if isinstance(action, ClickAction):
            action_dict = {"action": "click_element", "params": {"element_description": action.element_description, "x": action.x, "y": action.y}}
        elif isinstance(action, TypeAction):
            action_dict = {"action": "type", "params": {"text": action.text}}
        elif isinstance(action, CommandAction):
            action_dict = {"action": "command", "params": {"command": action.command}}
        elif isinstance(action, WaitAction):
            action_dict = {"action": "wait", "params": {"seconds": action.seconds}}
        else:
            continue
        actions_list.append(action_dict)
    return actions_list


async def decision_maker(state: AgentState) -> AgentState:
    if state.get("completed") or state.get("history"):
        screenshot = await state["browser"].get_screenshot(save_to_disk=False)
        with open(screenshot, "rb") as f:
            state["screenshot"] = base64.b64encode(f.read()).decode("utf-8")

    llm = get_llm(DecisionResponse)

    system_prompt = render_prompt("decision_maker", original_task=state["task"], history=", ".join(state.get("history", [])))

    logger.info(f"Отправляем запрос на принятие решения: {state['task']}")

    try:
        messages = [
            HumanMessage(
                content=[
                    {"type": "text", "text": system_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{state['screenshot']}"}},
                ]
            )
        ]

        response = await _retry_llm_call(llm, messages)
        logger.info(f"Ответ модели: {response}")

        if response.status == "success":
            state["goal_achieved"] = True
            state["completed"] = True
            logger.info("Цель достигнута!")
        elif response.status == "failed":
            state["goal_failed"] = True
            state["error"] = response.reason or "Невозможно достичь цели"
            logger.error(f"Цель не может быть достигнута: {response.reason}")
        else:
            if response.actions:
                state["action_queue"] = _convert_actions_to_queue(response.actions)
                state["current_step"] = -1
                state["completed"] = False
                state["goal_achieved"] = None
                state["goal_failed"] = None
                logger.info(f"План создан: {len(state['action_queue'])} действий")
            else:
                state["goal_failed"] = True
                state["error"] = "Не удалось создать план действий"

        if not state.get("messages"):
            state["messages"] = []
        state["messages"].append(AIMessage(content=response.reason or "Принятие решения завершено"))

    except Exception as e:
        if not state.get("messages"):
            state["messages"] = []
        state["messages"].append(AIMessage(content=f"Ошибка structured output: {e}"))
        logger.error(f"Ошибка structured output: {e}")
        raise

    return state


async def execute_click(state: AgentState) -> AgentState:
    try:
        action = state["action_queue"][state["current_step"]]
        params = action["params"]

        if "x" not in params or "y" not in params:
            state["error"] = "Не указаны координаты для клика"
            return state

        x, y = int(params["x"]), int(params["y"])
        screenshot_before = await state["browser"].get_screenshot(save_to_disk=False)
        element_desc = params.get("element_description", f"координаты ({x}, {y})")

        if CONFIG.debug:
            click_screenshot_path = f"{CONFIG.output_dir}/click_{int(time.time())}_{x}_{y}.png"
            screenshot_with_click = _draw_click_point_on_screenshot(screenshot_before, x, y, click_screenshot_path)
            logger.info(f"Клик по координатам ({x}, {y}) - скриншот с точкой: {screenshot_with_click}")
            if not state.get("history"):
                state["history"] = []
            state["history"].append(f"Клик по {element_desc} ({x}, {y}) - скриншот: {screenshot_with_click}")
        else:
            if not state.get("history"):
                state["history"] = []
            state["history"].append(f"Клик по {element_desc} ({x}, {y})")

        await state["browser"].click_by_position(x, y)

        if not state.get("messages"):
            state["messages"] = []
        state["messages"].append(AIMessage(content=f"Выполнен клик по {element_desc}"))

    except Exception as e:
        state["error"] = f"Ошибка клика: {str(e)}"

    return state


async def execute_type(state: AgentState) -> AgentState:
    try:
        action = state["action_queue"][state["current_step"]]
        params = action["params"]

        await state["browser"].type_text(params["text"])

        if not state.get("history"):
            state["history"] = []
        state["history"].append(f"Введен текст: {params['text']}")

        if not state.get("messages"):
            state["messages"] = []
        state["messages"].append(AIMessage(content=f"Введен текст: {params['text']}"))

    except Exception as e:
        state["error"] = f"Ошибка ввода: {str(e)}"

    return state


async def execute_command(state: AgentState) -> AgentState:
    try:
        action = state["action_queue"][state["current_step"]]
        params = action["params"]

        await state["browser"].execute_command(params["command"])

        if not state.get("history"):
            state["history"] = []
        state["history"].append(f"Выполнена команда: {params['command']}")

        if not state.get("messages"):
            state["messages"] = []
        state["messages"].append(AIMessage(content=f"Выполнена команда: {params['command']}"))

    except Exception as e:
        state["error"] = f"Ошибка команды: {str(e)}"

    return state


async def execute_wait(state: AgentState) -> AgentState:
    try:
        action = state["action_queue"][state["current_step"]]
        params = action["params"]
        seconds = int(params.get("seconds", 3))

        logger.info(f"Ожидание {seconds} секунд...")
        await asyncio.sleep(seconds)

        screenshot = await state["browser"].get_screenshot(save_to_disk=False)
        with open(screenshot, "rb") as f:
            state["screenshot"] = base64.b64encode(f.read()).decode("utf-8")

        if not state.get("history"):
            state["history"] = []
        state["history"].append(f"Ожидание {seconds} секунд")

        if not state.get("messages"):
            state["messages"] = []
        state["messages"].append(AIMessage(content=f"Ожидание {seconds} секунд завершено"))

    except Exception as e:
        state["error"] = f"Ошибка ожидания: {str(e)}"

    return state


def next_step(state: AgentState) -> AgentState:
    state["current_step"] += 1
    logger.info(f"Переход к шагу {state['current_step'] + 1} из {len(state['action_queue'])}")

    if state["current_step"] >= len(state["action_queue"]):
        logger.info("Все действия выполнены, переходим к проверке цели")
        state["completed"] = True

    return state


async def success_node(state: AgentState) -> AgentState:
    logger.info("Задача успешно выполнена!")
    state["completed"] = True
    return state


async def fail_node(state: AgentState) -> AgentState:
    logger.error("Не удалось выполнить задачу")
    state["completed"] = True
    return state


async def verify_final_result(screenshot: str, expected_result: str, all_history: list) -> dict:
    llm = get_llm(VerificationResult)

    system_prompt = render_prompt("verify_final_result", expected_result=expected_result, all_history=", ".join(all_history))

    logger.info("Проверяем финальный результат")

    try:
        messages = [
            HumanMessage(
                content=[
                    {"type": "text", "text": system_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{screenshot}"}},
                ]
            )
        ]

        response = await _retry_llm_call(llm, messages)
        logger.info(f"Ответ на проверку результата: {response}")
        return {"success": response.success, "details": response.details, "summary": response.summary}
    except Exception as e:
        logger.error(f"Ошибка проверки результата: {e}")
        return {"success": False, "details": "Ошибка анализа результата", "summary": "Не удалось проанализировать результат"}


def should_continue(state: AgentState) -> str:
    if state.get("error"):
        return "error_node"
    if state.get("goal_achieved"):
        return "success_node"
    if state.get("goal_failed"):
        return "fail_node"

    if state["current_step"] >= len(state["action_queue"]):
        return "decision_node"

    current_action = state["action_queue"][state["current_step"]]["action"]
    return f"{current_action}_node"
