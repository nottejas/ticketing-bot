import json
import os
import logging

logger = logging.getLogger(__name__)

DEFAULT_PATH = os.path.join("data", "seen_issues.json")
MAX_ENTRIES = 5000


class SeenIssuesStore:
    def __init__(self, path: str = DEFAULT_PATH, max_entries: int = MAX_ENTRIES):
        self.path = path
        self.max_entries = max_entries
        self._seen: list[str] = []
        self.load()

    def load(self) -> None:
        if not os.path.exists(self.path):
            self._seen = []
            return
        try:
            with open(self.path, "r") as f:
                data = json.load(f)
            if isinstance(data, list):
                self._seen = data
            else:
                logger.warning("Corrupt state file, starting fresh")
                self._seen = []
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load state file: {e}. Starting fresh.")
            # Back up corrupt file
            backup = self.path + ".bak"
            try:
                os.rename(self.path, backup)
                logger.info(f"Backed up corrupt state file to {backup}")
            except OSError:
                pass
            self._seen = []

    def has_seen(self, issue_id: str) -> bool:
        return issue_id in self._seen

    def mark_seen(self, issue_id: str) -> None:
        if issue_id not in self._seen:
            self._seen.append(issue_id)
            # Trim oldest entries if over limit
            if len(self._seen) > self.max_entries:
                self._seen = self._seen[-self.max_entries:]
            self.save()

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self._seen, f, indent=2)

    def count(self) -> int:
        return len(self._seen)
