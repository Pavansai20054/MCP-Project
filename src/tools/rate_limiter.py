"""Simple persistent rate limiting utilities."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

import fcntl


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after_seconds: int


class FileRateLimiter:
    """File-backed fixed-window limiter keyed by user identifier."""

    def __init__(self, storage_path: str | Path) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def consume(self, key: str, limit: int, window_seconds: int) -> RateLimitResult:
        now = int(time.time())
        with self.storage_path.open("a+", encoding="utf-8") as fp:
            fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
            fp.seek(0)
            raw = fp.read().strip()
            data: dict[str, list[int]] = json.loads(raw) if raw else {}

            timestamps = data.get(key, [])
            cutoff = now - window_seconds
            valid = [ts for ts in timestamps if ts > cutoff]

            if len(valid) >= limit:
                earliest = min(valid)
                retry_after = max(0, window_seconds - (now - earliest))
                data[key] = valid
                fp.seek(0)
                fp.truncate()
                json.dump(data, fp)
                fcntl.flock(fp.fileno(), fcntl.LOCK_UN)
                return RateLimitResult(False, 0, retry_after)

            valid.append(now)
            data[key] = valid
            remaining = max(0, limit - len(valid))
            fp.seek(0)
            fp.truncate()
            json.dump(data, fp)
            fcntl.flock(fp.fileno(), fcntl.LOCK_UN)
            return RateLimitResult(True, remaining, 0)