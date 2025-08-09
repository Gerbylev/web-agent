import time
from asyncio import sleep
from pathlib import Path
from typing import Dict, Optional

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from browser_controller.base import BaseBrowserController
from utils.config import CONFIG
from utils.log import get_logger

logger = get_logger()


class PlaywrightController(BaseBrowserController):
    def __init__(self, headless: bool = True, browser_type: str = "chromium", viewport_size: Dict[str, int] = None):
        self.headless = headless
        self.browser_type = browser_type
        self.viewport_size = viewport_size or {"width": 1280, "height": 720}

        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

        logger.debug(f"Initialized Playwright controller: {browser_type}, headless={headless}")

    async def start(self):
        try:
            self.playwright = await async_playwright().start()

            browser_engines = {"chromium": self.playwright.chromium, "firefox": self.playwright.firefox, "webkit": self.playwright.webkit}

            if self.browser_type not in browser_engines:
                raise ValueError(f"Unsupported browser type: {self.browser_type}")

            self.browser = await browser_engines[self.browser_type].launch(
                headless=self.headless,
                args=[
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                ],
            )

            self.context = await self.browser.new_context(
                viewport=self.viewport_size,
            )

            self.page = await self.context.new_page()

            logger.info(f"Browser started: {self.browser_type}")

        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            await self.close()
            raise

    async def close(self):
        try:
            if self.page:
                await self.page.close()
                self.page = None

            if self.context:
                await self.context.close()
                self.context = None

            if self.browser:
                await self.browser.close()
                self.browser = None

            if self.playwright:
                await self.playwright.stop()
                self.playwright = None

            logger.debug("Browser closed")

        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    async def navigate_to(self, url: str, wait_until: str = "domcontentloaded"):
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")

        try:
            await self.page.goto(url, wait_until=wait_until)
            logger.debug(f"Navigated to: {url}")

        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {e}")
            raise

    async def execute_command(self, command: str):
        keyboard = self.page.keyboard

        await keyboard.press(command)

    async def type_text(self, text: str) -> bool:
        try:
            if self.page:
                keyboard = self.page.keyboard
                await keyboard.type(text)
                return True
            else:
                logger.error("Browser page not available for typing")
                return False
        except:
            return False

    async def click_by_position(self, x: int, y: int):
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")

        try:
            await self.page.mouse.click(x, y)
            logger.debug(f"Clicked at position: ({x}, {y})")

        except Exception as e:
            logger.error(f"Failed to click at position ({x}, {y}): {e}")
            raise

    async def get_screenshot(self, path: Optional[str] = None, full_page: bool = False, save_to_disk: bool = True) -> str:
        if not self.page:
            raise RuntimeError("Browser not started. Call start() first.")

        try:
            await sleep(1)
            if path is None:
                screenshots_dir = Path(CONFIG.output_dir)
                screenshots_dir.mkdir(exist_ok=True)
                path = str(screenshots_dir / f"screenshot_{int(time.time())}.png")

            if save_to_disk:
                await self.page.screenshot(path=path, full_page=full_page)
                logger.debug(f"Screenshot saved: {path}")
                return path
            else:
                # Возвращаем временный путь для encode_image, но не сохраняем на диск
                buffer = await self.page.screenshot(full_page=full_page)
                temp_path = f"/tmp/temp_screenshot_{int(time.time())}.png"
                with open(temp_path, "wb") as f:
                    f.write(buffer)
                return temp_path

        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            raise
