import logging
import platform
import subprocess
import requests

logger = logging.getLogger(__name__)

SYSTEM = platform.system()


def notify_desktop(title: str, message: str) -> None:
    """Send a desktop notification (macOS or Windows)."""
    if SYSTEM == "Darwin":
        _notify_macos(title, message)
    elif SYSTEM == "Windows":
        _notify_windows(title, message)
    else:
        logger.warning(f"Desktop notifications not supported on {SYSTEM}")


def _notify_macos(title: str, message: str) -> None:
    safe_title = title.replace('"', '\\"')
    safe_message = message.replace('"', '\\"')
    script = f'display notification "{safe_message}" with title "{safe_title}" sound name "Glass"'
    try:
        subprocess.run(["osascript", "-e", script], check=False, capture_output=True)
        logger.info(f"macOS notification sent: {title}")
    except Exception as e:
        logger.warning(f"Failed to send macOS notification: {e}")


def _notify_windows(title: str, message: str) -> None:
    """Send a Windows toast notification using PowerShell."""
    # Escape single quotes for PowerShell
    safe_title = title.replace("'", "''")
    safe_message = message.replace("'", "''")
    ps_script = f"""
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, ContentType = WindowsRuntime] | Out-Null
    $template = @'
    <toast duration="long">
        <visual>
            <binding template="ToastGeneric">
                <text>{safe_title}</text>
                <text>{safe_message}</text>
            </binding>
        </visual>
        <audio src="ms-winsoundevent:Notification.Default"/>
    </toast>
'@
    $xml = New-Object Windows.Data.Xml.Dom.XmlDocument
    $xml.LoadXml($template)
    $toast = [Windows.UI.Notifications.ToastNotification]::new($xml)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Ticketing Bot').Show($toast)
    """
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_script],
            check=False, capture_output=True
        )
        logger.info(f"Windows notification sent: {title}")
    except Exception as e:
        logger.warning(f"Failed to send Windows notification: {e}")


def notify_telegram(bot_token: str, chat_id: str, message: str) -> None:
    """Send a Telegram message via the Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Telegram notification sent")
    except requests.RequestException as e:
        logger.error(f"Failed to send Telegram notification: {e}")


def send_alerts(subject: str, url: str, config: dict) -> None:
    """Send alerts for a new issue via all enabled channels."""
    title = "New Issue Detected"
    short_msg = f"{subject}\n{url}"
    telegram_msg = f"*{title}*\nSubject: {subject}\nLink: {url}"

    if config["notifications"].get("desktop", True):
        notify_desktop(title, short_msg)

    if config["notifications"].get("telegram"):
        telegram = config.get("telegram", {})
        token = telegram.get("bot_token", "")
        chat_id = telegram.get("chat_id", "")
        if token and chat_id:
            notify_telegram(token, str(chat_id), telegram_msg)
        else:
            logger.warning("Telegram enabled but credentials not configured")
