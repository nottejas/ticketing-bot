import os
import yaml

DEFAULTS = {
    "poll_interval_seconds": 30,
    "subject_filters": [],
    "browser": {
        "user_data_dir": "./data/browser_profile",
        "headless": False,
        "timeout_ms": 10000,
    },
    "notifications": {
        "desktop": True,
        "telegram": True,
    },
}


def load_config(path: str = "config.yaml") -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r") as f:
        config = yaml.safe_load(f) or {}

    # Apply defaults for missing keys
    for key, default in DEFAULTS.items():
        if key not in config:
            config[key] = default
        elif isinstance(default, dict):
            for sub_key, sub_default in default.items():
                config[key].setdefault(sub_key, sub_default)

    # Validate required fields
    if not config.get("target_url"):
        raise ValueError("config: 'target_url' is required")

    telegram = config.get("telegram", {})
    if config["notifications"].get("telegram"):
        if not telegram.get("bot_token") or telegram["bot_token"] == "YOUR_BOT_TOKEN":
            raise ValueError("config: 'telegram.bot_token' must be set (see README for setup)")
        if not telegram.get("chat_id") or telegram["chat_id"] == "YOUR_CHAT_ID":
            raise ValueError("config: 'telegram.chat_id' must be set (see README for setup)")

    # Resolve relative browser data dir to absolute
    user_data_dir = config["browser"]["user_data_dir"]
    if not os.path.isabs(user_data_dir):
        config["browser"]["user_data_dir"] = os.path.abspath(user_data_dir)

    return config
