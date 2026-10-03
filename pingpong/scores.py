"""Wins, best rally, mute, and the last level.

Remembered on this computer, or in the browser on the web build.
"""

import os
import sys
from pathlib import Path

from .settings import LEVEL_ORDER

_WEB_KEY = "ping-pong-stats"


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


def _blank():
    return {"wins": 0, "rally": 0, "muted": False, "level": "match"}


def _from_text(text):
    stats = _blank()
    raw = _parse(text)
    try:
        stats["wins"] = max(0, int(raw.get("wins", 0)))
        stats["rally"] = max(0, int(raw.get("rally", 0)))
    except ValueError:
        pass
    stats["muted"] = raw.get("muted") == "1"
    level = raw.get("level", "match")
    stats["level"] = level if level in LEVEL_ORDER else "match"
    return stats


def _format(stats):
    return "\n".join((
        f"wins={max(0, int(stats['wins']))}",
        f"rally={max(0, int(stats['rally']))}",
        f"muted={'1' if stats['muted'] else '0'}",
        f"level={stats['level'] if stats['level'] in LEVEL_ORDER else 'match'}",
        "",
    ))


def note_arcade(game, score, note=""):
    """Leave this run for Melted Arcade, on the name signed in there."""
    if sys.platform != "emscripten":
        return
    try:
        import json
        import time

        storage = _web_storage()
        player = str(storage.getItem("melted-arcade-player") or "").strip()
        score = max(0, int(score))
        if not player or score <= 0:
            return
        raw = storage.getItem("melted-arcade-slips") or "[]"
        try:
            slips = json.loads(str(raw))
        except ValueError:
            slips = []
        if not isinstance(slips, list):
            slips = []
        slips.append({
            "game": str(game),
            "score": score,
            "player": player,
            "note": "win" if note == "win" else "",
            "at": int(time.time() * 1000),
        })
        storage.setItem("melted-arcade-slips", json.dumps(slips[-40:]))
    except Exception:
        return


def _web_storage():
    from platform import window

    return window.localStorage


def load():
    if sys.platform == "emscripten":
        try:
            raw = _web_storage().getItem(_WEB_KEY)
        except (AttributeError, OSError, TypeError, ValueError):
            return _blank()
        if not raw:
            return _blank()
        return _from_text(str(raw))
    for folder in _dirs():
        path = folder / "stats.txt"
        try:
            return _from_text(path.read_text(encoding="utf-8"))
        except OSError:
            continue
    return _blank()


def save(stats):
    text = _format(stats)
    if sys.platform == "emscripten":
        try:
            _web_storage().setItem(_WEB_KEY, text)
        except (AttributeError, OSError, TypeError, ValueError):
            pass
        return
    for folder in _dirs():
        try:
            folder.mkdir(parents=True, exist_ok=True)
            (folder / "stats.txt").write_text(text, encoding="utf-8")
            return
        except OSError:
            continue
