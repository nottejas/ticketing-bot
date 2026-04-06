import asyncio
import logging
from playwright.async_api import async_playwright, BrowserContext, Page

logger = logging.getLogger(__name__)

# Selectors to detect authenticated vs login page (Redmine)
ISSUES_PAGE_SELECTOR = "table.list.issues"
OKTA_LOGIN_INDICATOR = "okta"


async def launch_browser(config: dict) -> tuple[BrowserContext, Page]:
    """Launch a persistent Chromium browser context and navigate to the target URL."""
    browser_config = config["browser"]
    pw = await async_playwright().start()

    context = await pw.chromium.launch_persistent_context(
        user_data_dir=browser_config["user_data_dir"],
        headless=browser_config["headless"],
        viewport={"width": 1280, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
    )

    # Use existing page or create one
    page = context.pages[0] if context.pages else await context.new_page()
    await page.goto(config["target_url"], wait_until="domcontentloaded",
                    timeout=browser_config["timeout_ms"])

    logger.info(f"Browser launched, navigated to {config['target_url']}")
    return context, page


async def is_session_valid(page: Page) -> bool:
    """Check if we're on the authenticated issues page (not redirected to Okta)."""
    current_url = page.url.lower()
    if OKTA_LOGIN_INDICATOR in current_url:
        return False

    # Try to find any issues-related content on the page
    try:
        element = await page.query_selector(ISSUES_PAGE_SELECTOR)
        return element is not None
    except Exception:
        return False


async def wait_for_login(page: Page, config: dict, timeout_minutes: int = 10) -> None:
    """Wait for the user to manually complete Okta login.

    Polls every 3 seconds for up to timeout_minutes for the issues page to appear.
    """
    logger.info("Waiting for manual login (Okta)... Please log in via the browser window.")
    deadline = asyncio.get_event_loop().time() + (timeout_minutes * 60)

    while asyncio.get_event_loop().time() < deadline:
        if await is_session_valid(page):
            logger.info("Login detected! Session is valid.")
            return
        await asyncio.sleep(3)

    raise TimeoutError(
        f"Login was not completed within {timeout_minutes} minutes. "
        "Please restart the bot and try again."
    )


async def refresh_page(page: Page, config: dict) -> bool:
    """Reload the page and return whether the session is still valid."""
    try:
        await page.reload(wait_until="domcontentloaded",
                          timeout=config["browser"]["timeout_ms"])
        return await is_session_valid(page)
    except Exception as e:
        logger.error(f"Page reload failed: {e}")
        return False
