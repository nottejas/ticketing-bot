import asyncio
import argparse
import logging
import sys
import os
from logging.handlers import RotatingFileHandler

from src.config_loader import load_config
from src.state import SeenIssuesStore
from src.browser import launch_browser, is_session_valid, wait_for_login, refresh_page
from src.monitor import parse_issues, filter_new_issues, dump_page_html
from src.notifier import send_alerts, notify_desktop

logger = logging.getLogger("ticketing_bot")


def setup_logging() -> None:
    """Configure logging to stdout and a rotating log file."""
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    formatter = logging.Formatter(log_format)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.setLevel(logging.INFO)

    # File handler
    os.makedirs("data", exist_ok=True)
    file_handler = RotatingFileHandler(
        "data/bot.log", maxBytes=5_000_000, backupCount=3
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(console)
    root.addHandler(file_handler)


async def run_bot(config: dict, dump_html: bool = False) -> None:
    """Main bot loop: launch browser, wait for login, poll for issues."""
    state = SeenIssuesStore()
    logger.info(f"Loaded {state.count()} previously seen issues")

    consecutive_failures = 0

    # Launch browser
    context, page = await launch_browser(config)
    logger.info("Browser launched successfully")

    try:
        # Check if already logged in
        if not await is_session_valid(page):
            notify_desktop("Ticketing Bot", "Please log in via the browser window")
            print("\n" + "=" * 60)
            print("  Please log in via the Chromium browser window.")
            print("  Complete the Okta authentication (including MFA).")
            print("  The bot will start monitoring once login is detected.")
            print("=" * 60 + "\n")
            await wait_for_login(page, config)
        else:
            logger.info("Existing session is valid, skipping login")

        # Dump HTML if requested (for selector discovery)
        if dump_html:
            await dump_page_html(page)
            print("\nHTML dumped. Exiting. Update selectors in src/monitor.py and restart.")
            return

        # Mark all current issues as seen on first run to avoid alert flood
        logger.info("Initial scan: marking existing issues as seen...")
        initial_issues = await parse_issues(page, config["target_url"])
        for issue in initial_issues:
            state.mark_seen(issue.issue_id)
        logger.info(f"Marked {len(initial_issues)} existing issues as seen")
        print(f"\nBot is now monitoring. Polling every {config['poll_interval_seconds']}s...")
        print("Press Ctrl+C to stop.\n")

        # Polling loop
        while True:
            await asyncio.sleep(config["poll_interval_seconds"])

            # Reload page
            session_ok = await refresh_page(page, config)

            if not session_ok:
                logger.warning("Session expired! Requesting re-login...")
                notify_desktop("Ticketing Bot", "Session expired — please re-login in the browser")
                print("\n⚠️  Session expired. Please re-login in the browser window.\n")
                await wait_for_login(page, config)
                consecutive_failures = 0
                continue

            # Parse and filter issues
            try:
                issues = await parse_issues(page, config["target_url"])
                new_issues = filter_new_issues(issues, state)
                consecutive_failures = 0
            except Exception as e:
                consecutive_failures += 1
                logger.error(f"Failed to parse issues (attempt {consecutive_failures}): {e}")
                if consecutive_failures >= 5:
                    send_alerts(
                        "Bot Error: Unable to parse issues page",
                        f"The bot has failed {consecutive_failures} times in a row. Check the logs.",
                        config,
                    )
                continue

            # Alert on new matching issues
            for issue in new_issues:
                logger.info(f"New issue detected: [{issue.issue_id}] {issue.subject}")
                send_alerts(issue.subject, issue.url, config)
                state.mark_seen(issue.issue_id)

            if new_issues:
                logger.info(f"Alerted on {len(new_issues)} new issue(s)")

    except KeyboardInterrupt:
        print("\nShutting down...")
    except TimeoutError as e:
        logger.error(str(e))
        print(f"\n{e}")
    finally:
        state.save()
        await context.close()
        logger.info("Bot stopped, state saved")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ticketing Bot — Issue Monitor")
    parser.add_argument(
        "--config", default="config.yaml",
        help="Path to config file (default: config.yaml)"
    )
    parser.add_argument(
        "--dump-html", action="store_true",
        help="Dump the issues page HTML for selector inspection, then exit"
    )
    args = parser.parse_args()

    setup_logging()

    try:
        config = load_config(args.config)
    except (FileNotFoundError, ValueError) as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

    logger.info("Ticketing Bot starting...")
    asyncio.run(run_bot(config, dump_html=args.dump_html))


if __name__ == "__main__":
    main()
