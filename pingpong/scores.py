"""Wins, best rally, mute, and the last level, remembered on this computer."""

import os
from pathlib import Path

from .settings import LEVEL_ORDER


def _dirs():
    found = []
    base = os.environ.get("LOCALAPPDATA")
    if base:
        found.append(Path(base) / "PingPong")
    found.append(Path.home() / ".ping-pong")
    return found


def _parse(text):
    data = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def load():
    stats = {"wins": 0, "rally": 0, "muted": False, "level": "match"}
    for folder in _dirs():
        path = folder / "stats.txt"
        try:
            raw = _parse(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        try:
            stats["wins"] = max(0, int(raw.get("wins", 0)))
            stats["rally"] = max(0, int(raw.get("rally", 0)))
        except ValueError:
            pass
        stats["muted"] = raw.get("muted") == "1"
        level = raw.get("level", "match")
        stats["level"] = level if level in LEVEL_ORDER else "match"
        return stats
    return stats


def save(stats):
    text = "\n".join((
        f"wins={max(0, int(stats['wins']))}",
        f"rally={max(0, int(stats['rally']))}",
        f"muted={'1' if stats['muted'] else '0'}",
        f"level={stats['level'] if stats['level'] in LEVEL_ORDER else 'match'}",
        "",
    ))
    for folder in _dirs():
        try:
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "stats.txt").write_text(text, encoding="utf-8")
            return
        except OSError:
            continue
