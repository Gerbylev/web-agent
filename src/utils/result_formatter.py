import time
from typing import Dict, List

from utils.config import CONFIG
from utils.log import get_logger

log = get_logger()


def format_final_output(verification: Dict, history: List[str], total_time: float) -> str:
    status = "УСПЕХ" if verification["success"] else "НЕУДАЧА"

    output_lines = [
        "\n" + "=" * 80,
        f"РЕЗУЛЬТАТ: {status} (Общее время: {total_time:.1f}с)",
        f"КРАТКОЕ РЕЗЮМЕ: {verification['summary']}",
        f"\nДЕТАЛИ: {verification['details']}",
        "\nИСТОРИЯ ВЫПОЛНЕНИЯ:",
    ]
    output_lines.extend(history)
    output_lines.append("=" * 80)

    return "\n".join(output_lines)


def save_results(output_text: str) -> None:
    print(output_text)

    result_filename = f"{CONFIG.output_dir}/result_{int(time.time())}.txt"
    with open(result_filename, "w", encoding="utf-8") as f:
        f.write(output_text)

    log.info(f"Результаты сохранены в: {result_filename}")
