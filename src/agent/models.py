from typing import Union, List

from pydantic import BaseModel, Field


class ClickAction(BaseModel):
    action: str = Field("click_element", description="Тип действия")
    element_description: str = Field(..., description="Описание элемента")
    x: int = Field(..., description="Координата X")
    y: int = Field(..., description="Координата Y")


class TypeAction(BaseModel):
    action: str = Field("type", description="Тип действия")
    text: str = Field(..., description="Текст для ввода")


class CommandAction(BaseModel):
    action: str = Field("command", description="Тип действия")
    command: str = Field(..., description="Команда/клавиша")


class WaitAction(BaseModel):
    action: str = Field("wait", description="Тип действия")
    seconds: int = Field(..., description="Количество секунд ожидания")


ActionType = Union[ClickAction, TypeAction, CommandAction, WaitAction]


class DecisionResponse(BaseModel):
    status: str = Field(..., description="Статус: success, failed, или continue")
    reason: str = Field("", description="Объяснение решения")
    actions: List[ActionType] = Field(default=[], description="Список действий если status=continue")


class VerificationResult(BaseModel):
    success: bool = Field(..., description="Успешно ли достигнут результат")
    details: str = Field(..., description="Подробное описание того что видно на экране")
    summary: str = Field(..., description="Краткое резюме результата")
