# Ticketing Bot

Monitors the [Website4SG Support Ticketing](https://support.website4sg.saint-gobain.io/issues) portal (Redmine) for **all new issues** and sends alerts via **desktop notifications** (macOS/Windows) and **Telegram**.

## How It Works

1. Bot opens a Chromium browser window
2. You log in manually (Okta SSO + MFA)
3. Bot saves your session and starts polling every 30s
4. When a new issue appears, you get notified on desktop + Telegram
5. If the session expires, bot pauses and asks you to re-login

---

## Installation

### Prerequisites

- Python 3.10+
- pip

### Step 1: Clone / navigate to the project

```bash
cd /Users/nottejas/Desktop/code/ticketing-bot
```

### Step 2: Install Python dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Install Chromium for Playwright

```bash
playwright install chromium
```

### Step 4: Set up Telegram bot

1. Open Telegram, search for `@BotFather`
2. Send `/newbot`, follow the prompts to create a bot
3. Copy the **bot token** you receive

4. Send any message (e.g., "hi") to your new bot in Telegram

5. Get your chat ID:
   ```bash
   curl -s "https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates" | python -m json.tool
   ```
   Look for `"chat": {"id": 123456789}` — that number is your `chat_id`.

### Step 5: Configure

Edit `config.yaml`:

```yaml
target_url: "https://support.website4sg.saint-gobain.io/issues"
poll_interval_seconds: 30

telegram:
  bot_token: "YOUR_BOT_TOKEN"
  chat_id: "YOUR_CHAT_ID"

browser:
  user_data_dir: "./data/browser_profile"
  headless: false
  timeout_ms: 10000

notifications:
  desktop: true
  telegram: true
```

- `poll_interval_seconds` — how often to check for new issues
- `headless` — set to `true` to hide the browser window (only after first login)

---

## Usage

### First run (discover page selectors)

```bash
python -m src.main --dump-html
```

Log in via the browser window. The bot saves the page HTML to `data/page_dump.html` for debugging, then exits.

### Normal run

```bash
python -m src.main
```

1. Browser opens — log in if needed (session is remembered across restarts)
2. Bot marks all existing issues as "seen" on first launch
3. Polls for new issues every 30 seconds
4. Press `Ctrl+C` to stop

### Custom config path

```bash
python -m src.main --config /path/to/config.yaml
```

---

## Running as a Cron Job

Since the bot requires a browser session and manual login, a traditional cron job doesn't work well for the initial start. Instead, use one of these approaches:

### Option A: Auto-restart on crash (recommended)

Create a wrapper script:

```bash
cat > /Users/nottejas/Desktop/code/ticketing-bot/run.sh << 'EOF'
#!/bin/bash
cd /Users/nottejas/Desktop/code/ticketing-bot
while true; do
    echo "[$(date)] Starting ticketing bot..."
    python -m src.main
    echo "[$(date)] Bot exited. Restarting in 10 seconds..."
    sleep 10
done
EOF
chmod +x /Users/nottejas/Desktop/code/ticketing-bot/run.sh
```

Run it:
```bash
./run.sh
```

### Option B: macOS Launch Agent (auto-start on login)

Create the plist file:

```bash
cat > ~/Library/LaunchAgents/com.ticketingbot.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ticketingbot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/opt/homebrew/opt/python@3.14/Frameworks/Python.framework/Versions/3.14/bin/python3</string>
        <string>-m</string>
        <string>src.main</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/nottejas/Desktop/code/ticketing-bot</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/nottejas/Desktop/code/ticketing-bot/data/bot_stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/nottejas/Desktop/code/ticketing-bot/data/bot_stderr.log</string>
</dict>
</plist>
EOF
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.ticketingbot.plist
```

Stop it:
```bash
launchctl unload ~/Library/LaunchAgents/com.ticketingbot.plist
```

**Note:** The Launch Agent starts the bot on login. You still need to log in to Okta manually the first time (or when the session expires). The bot will show a desktop notification when login is needed.

### Option C: Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task > Name: "Ticketing Bot"
3. Trigger: "When I log on"
4. Action: Start a Program
   - Program: `python`
   - Arguments: `-m src.main`
   - Start in: `C:\path\to\ticketing-bot`
5. Check "Restart the task if it fails" in Settings tab

---

## Project Structure

```
ticketing-bot/
├── config.yaml              # Settings (URL, Telegram, polling)
├── requirements.txt         # Python dependencies
├── run.sh                   # Auto-restart wrapper script
├── src/
│   ├── main.py              # Entry point + polling loop
│   ├── browser.py           # Playwright browser session management
│   ├── monitor.py           # Issue parsing + new-issue detection
│   ├── notifier.py          # Desktop + Telegram alerts
│   ├── state.py             # Seen issues tracking (JSON)
│   └── config_loader.py     # Config loading + validation
└── data/
    ├── browser_profile/     # Chromium session data (auto-created)
    ├── seen_issues.json     # Previously alerted issue IDs
    └── bot.log              # Rotating log file
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `No issue rows found` | Run `--dump-html`, check if page structure changed, update selectors in `src/monitor.py` |
| Session keeps expiring | Increase `poll_interval_seconds` to reduce load; Okta sessions typically last 1-8 hours |
| No Telegram message | Verify `bot_token` and `chat_id` in config; make sure you messaged the bot first |
| No desktop notification | macOS: check System Settings > Notifications; Windows: check notification center settings |
| Browser won't launch | Run `playwright install chromium` again |
