import dataclasses
import logging
from playwright.async_api import Page
from src.state import SeenIssuesStore

logger = logging.getLogger(__name__)

# Redmine issue tracker selectors (discovered from page dump)
ISSUE_ROW_SELECTOR = "table.list.issues tbody tr.issue"
ISSUE_ID_SELECTOR = "td.id a"
ISSUE_SUBJECT_SELECTOR = "td.subject a"

BASE_URL = "https://support.website4sg.saint-gobain.io"


@dataclasses.dataclass
class Issue:
    issue_id: str
    subject: str
    url: str
    created_at: str | None = None


async def parse_issues(page: Page, base_url: str) -> list[Issue]:
    """Parse all visible issues from the Redmine issues table."""
    issues = []

    rows = await page.query_selector_all(ISSUE_ROW_SELECTOR)
    if not rows:
        logger.warning("No issue rows found on page. The page structure may have changed.")
        return issues

    for row in rows:
        try:
            # Get issue ID and link from td.id a
            id_el = await row.query_selector(ISSUE_ID_SELECTOR)
            if not id_el:
                continue
            issue_id = (await id_el.inner_text()).strip()
            href = await id_el.get_attribute("href") or ""

            # Build full URL
            if href and not href.startswith("http"):
                href = BASE_URL + href

            # Get subject from td.subject a
            subject_el = await row.query_selector(ISSUE_SUBJECT_SELECTOR)
            subject = (await subject_el.inner_text()).strip() if subject_el else "(no subject)"

            issues.append(Issue(
                issue_id=issue_id,
                subject=subject,
                url=href or base_url,
            ))
        except Exception as e:
            logger.debug(f"Failed to parse issue row: {e}")
            continue

    logger.info(f"Parsed {len(issues)} issues from page")
    return issues


def filter_new_issues(
    issues: list[Issue],
    state: SeenIssuesStore,
) -> list[Issue]:
    """Return issues that have not been seen before."""
    return [issue for issue in issues if not state.has_seen(issue.issue_id)]


async def dump_page_html(page: Page, output_path: str = "data/page_dump.html") -> None:
    """Dump the current page HTML to a file for selector inspection."""
    import os
    content = await page.content()
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"Page HTML dumped to {output_path}")
    print(f"\nPage HTML saved to: {output_path}")
    print("Inspect this file to find the correct CSS selectors for issue rows, subjects, and links.")
    print(f"Then update the selectors in src/monitor.py")
