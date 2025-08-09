from abc import ABC, abstractmethod
from typing import Optional


class BaseBrowserController(ABC):
    @abstractmethod
    async def navigate_to(self, url: str):
        pass

    @abstractmethod
    async def click_by_position(self, x: int, y: int):
        pass

    @abstractmethod
    async def type_text(self, text: str):
        pass

    @abstractmethod
    async def execute_command(self, text: str):
        pass

    @abstractmethod
    async def get_screenshot(self, path: Optional[str] = None, full_page: bool = True, save_to_disk: bool = True) -> str:
        pass
