import os
import requests


def _discord_webhook_url():
    return os.environ.get("DISCORD_WEBHOOK_URL").strip()

def send_down_alert(target, reason):
    _fire_alert(
        target=target,
        title=f"{target['name']} is DOWN",
        description=reason,
        color=0xEF4444,
        event="down",
    )


def send_recovery_alert(target, downtime_str):
    _fire_alert(
        target=target,
        title=f"{target['name']} recovered",
        description=f"Back up after {downtime_str}.",
        color=0x22C55E,
        event="up",
    )


def _fire_alert(target, title, description, color, event):
    discord_url = _discord_webhook_url()
    if discord_url:
        try:
            requests.post(
                discord_url,
                json={
                    "embeds": [
                        {
                            "title": title,
                            "description": description,
                            "color": color,
                            "fields": [{"name": "URL", "value": target["url"]}],
                        }
                    ]
                },
                timeout=5,
            )
        except requests.exceptions.RequestException as e:
            print(f"[alerts] Discord webhook failed: {e}")