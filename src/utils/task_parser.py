import os
from dataclasses import dataclass
from typing import List


@dataclass
class TaskData:
    url: str
    tasks: List[str]
    result: str


class TaskParseError(Exception):
    pass


def task_parse(file_path: str) -> TaskData:
    if not os.path.isfile(file_path):
        raise TaskParseError(f"Файл задач не найден: {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            raise TaskParseError(f"Файл задач пустой: {file_path}")

        lines = [line.strip() for line in content.split("\n") if line.strip()]

        if len(lines) < 3:
            raise TaskParseError(f"Файл задач должен содержать минимум 3 строки (url, задачу, result): {file_path}")

        url = None
        tasks = []
        result = None

        for line in lines:
            if line.startswith("url:"):
                url = line.replace("url:", "").strip()
            elif line.startswith("result:"):
                result = line.replace("result:", "").strip()
            elif line and not line.startswith("url:") and not line.startswith("result:"):
                # Убираем номера задач если есть (1., 2., и т.д.)
                task = line
                if ". " in task and task.split(".")[0].strip().isdigit():
                    task = ".".join(task.split(".")[1:]).strip()
                if task:
                    tasks.append(task)

        if not url:
            raise TaskParseError(f"Не найден URL в файле: {file_path}. Формат: url: https://example.com")

        if not tasks:
            raise TaskParseError(f"Не найдены задачи в файле: {file_path}. Формат: 1. Задача")

        if not result:
            raise TaskParseError(f"Не найден результат в файле: {file_path}. Формат: result: Ожидаемый результат")

        return TaskData(url=url, tasks=tasks, result=result)

    except UnicodeDecodeError:
        raise TaskParseError(f"Ошибка кодировки файла: {file_path}. Файл должен быть в UTF-8")
    except Exception as e:
        if isinstance(e, TaskParseError):
            raise
        raise TaskParseError(f"Ошибка при парсинге файла {file_path}: {str(e)}")
