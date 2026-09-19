import json
import os
from datetime import datetime, timezone, timedelta

from lib import store, monitor

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE_DIR, "config.json")) as f:
    CONFIG = json.load(f)

API_DIR = os.path.join(store.DATA_DIR, "api")
HISTORY_DIR = os.path.join(API_DIR, "history")


def _uptime_pct(history, since):
    recent = [h for h in history if datetime.fromisoformat(h["t"]) >= since]
    if not recent:
        return None
    up_count = sum(1 for h in recent if h["up"])
    return round((up_count / len(recent)) * 100, 2)


def build_status(state, now):
    since_24h = now - timedelta(hours=24)
    since_7d = now - timedelta(days=7)

    out = []
    for target in CONFIG["targets"]:
        base = {"id": target["id"], "name": target["name"], "url": target["url"]}
        m = state["monitors"].get(target["id"])
        if not m:
            out.append({
                **base,
                "status": "pending",
                "http_status": None,
                "latency_ms": None,
                "last_checked": None,
                "uptime_24h": None,
                "uptime_7d": None,
                "history": [],
            })
            continue
        out.append({
            **base,
            "status": m["status"],
            "http_status": m["http_status"],
            "latency_ms": m["latency_ms"],
            "last_checked": m["last_checked"],
            "uptime_24h": _uptime_pct(m["history"], since_24h),
            "uptime_7d": _uptime_pct(m["history"], since_7d),
            "history": m["history"][-30:],
        })

    return {"generated_at": now.isoformat(), "monitors": out}


def build_incidents(state):
    ordered = sorted(state["incidents"], key=lambda i: i["started_at"], reverse=True)
    return {"incidents": ordered[:100]}


def _write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, separators=(",", ":"))
    os.replace(tmp, path)


def export(state):
    now = datetime.now(timezone.utc)

    _write_json(os.path.join(API_DIR, "status.json"), build_status(state, now))
    _write_json(os.path.join(API_DIR, "incidents.json"), build_incidents(state))

    for target in CONFIG["targets"]:
        m = state["monitors"].get(target["id"])
        _write_json(
            os.path.join(HISTORY_DIR, f"{target['id']}.json"),
            {"id": target["id"], "history": m["history"] if m else []},
        )


def main():
    state = monitor.run_all_checks(CONFIG)  # checks, updates state.json, fires alerts
    export(state)
    print(f"[run_once] Checked {len(CONFIG['targets'])} targets, wrote {API_DIR}")


if __name__ == "__main__":
    main()