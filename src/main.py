import asyncio

from agent_runner import run_all_tasks
from utils.config import CONFIG
from utils.log import get_logger
from utils.result_formatter import format_final_output, save_results
from utils.task_parser import task_parse

log = get_logger()


async def run_agent():
    task_data = task_parse(CONFIG.task_file_path)
    log.info(f"Загружена задача: {task_data.url}")
    log.info(f"Количество шагов: {len(task_data.tasks)}")

    metrics, verification = await run_all_tasks(task_data)
    metrics.finish()

    output_text = format_final_output(verification, metrics.get_history(), metrics.total_time)
    save_results(output_text)


if __name__ == "__main__":
    asyncio.run(run_agent())
