from pathlib import Path

from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright


class BrowserSession:
    def __init__(self, headless: bool = False, slow_mo_ms: int = 250) -> None:
        self.headless = headless
        self.slow_mo_ms = slow_mo_ms
        self._playwright = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    def __enter__(self) -> "BrowserSession":
        self._playwright = sync_playwright().start()
        self.browser = self._playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo_ms,
        )
        self.context = self.browser.new_context(
            viewport={"width": 1440, "height": 1000},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        self.page = self.context.new_page()
        return self

    def goto(self, url: str, wait_until: str = "domcontentloaded") -> None:
        if self.page is None:
            raise RuntimeError("Browser session is not initialized.")

        self.page.goto(url, wait_until=wait_until, timeout=60_000)

    def screenshot(self, output_path: str) -> None:
        if self.page is None:
            raise RuntimeError("Browser session is not initialized.")

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.page.screenshot(path=str(path), full_page=True)

    def title(self) -> str:
        if self.page is None:
            raise RuntimeError("Browser session is not initialized.")

        return self.page.title()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self.context is not None:
            self.context.close()
        if self.browser is not None:
            self.browser.close()
        if self._playwright is not None:
            self._playwright.stop()