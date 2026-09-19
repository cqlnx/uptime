import os
import time
import threading
from datetime import datetime, timezone

from lib import store, checker, alerts

FAILURE_THRESHOLD = int(os.environ.get("FAILURE_THRESHOLD", "2"))


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _format_duration(seconds):
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {seconds}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def _get_or_init_monitor(state, target):
    monitors = state["monitors"]
    if target["id"] not in monitors:
        monitors[target["id"]] = {
            "status": "pending",
            "http_status": None,
            "latency_ms": None,
            "last_checked": None,
            "consecutive_fails": 0,
            "history": [],
        }
    return monitors[target["id"]]


def run_all_checks(config):
    state = store.load()
    retention = config.get("history_retention", 2000)

    for target in config["targets"]:
        m = _get_or_init_monitor(state, target)
        result = checker.check_target(target)
        now = _now_iso()

        m["http_status"] = result["http_status"]
        m["latency_ms"] = result["latency_ms"]
        m["last_checked"] = now
        m["history"].append(
            {
                "t": now,
                "up": result["ok"],
                "http_status": result["http_status"],
                "latency_ms": result["latency_ms"],
            }
        )
        if len(m["history"]) > retention:
            m["history"] = m["history"][-retention:]

        prev_status = m["status"]

        if result["ok"]:
            m["consecutive_fails"] = 0
            if prev_status == "down":
                for inc in reversed(state["incidents"]):
                    if inc["target_id"] == target["id"] and inc["ended_at"] is None:
                        inc["ended_at"] = now
                        started = datetime.fromisoformat(inc["started_at"])
                        ended = datetime.fromisoformat(now)
                        downtime = (ended - started).total_seconds()
                        alerts.send_recovery_alert(target, _format_duration(downtime))
                        break
            m["status"] = "up"
        else:
            m["consecutive_fails"] += 1
            if prev_status != "down" and m["consecutive_fails"] >= FAILURE_THRESHOLD:
                m["status"] = "down"
                state["incidents"].append(
                    {
                        "id": store.new_incident_id(),
                        "target_id": target["id"],
                        "target_name": target["name"],
                        "started_at": now,
                        "ended_at": None,
                        "cause": result["error"],
                    }
                )
                alerts.send_down_alert(target, result["error"] or "No details available.")
            elif prev_status == "pending" or prev_status == "up":
                m["status"] = "pending" if prev_status == "pending" else prev_status

    store.save(state)
    return state


class MonitorLoop:
    """Runs run_all_checks on a background thread at a fixed interval."""

    def __init__(self, config, interval_seconds):
        self.config = config
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._thread = None

    def start(self):
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while not self._stop_event.is_set():
            try:
                run_all_checks(self.config)
            except Exception as e:
                print(f"[monitor] Check pass failed: {e}")
            self._stop_event.wait(self.interval_seconds)

    def stop(self):
        self._stop_event.set()
