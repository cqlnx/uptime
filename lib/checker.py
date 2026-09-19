import time
import requests


def check_target(target):
    method = target.get("method", "GET")
    timeout = target.get("timeout_seconds", 8)
    expected = set(target.get("expected_status", [200]))

    start = time.monotonic()
    try:
        resp = requests.request(
            method,
            target["url"],
            timeout=timeout,
            allow_redirects=True,
            headers={"User-Agent": "MineScan-StatusMonitor/1.0"},
        )
        latency_ms = round((time.monotonic() - start) * 1000)
        ok = resp.status_code in expected
        return {
            "ok": ok,
            "http_status": resp.status_code,
            "latency_ms": latency_ms,
            "error": None if ok else f"Unexpected status code {resp.status_code}",
        }
    except requests.exceptions.Timeout:
        return {
            "ok": False,
            "http_status": None,
            "latency_ms": None,
            "error": f"Timed out after {timeout}s",
        }
    except requests.exceptions.RequestException as e:
        return {
            "ok": False,
            "http_status": None,
            "latency_ms": None,
            "error": str(e),
        }
