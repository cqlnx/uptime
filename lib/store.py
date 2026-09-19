import json
import os
import threading
import time
import uuid
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "state.json")
_lock = threading.Lock()

def _empty_state():
    return {
        "monitors": {},
        "incidents": []
    }

def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load():
    _ensure_data_dir()
    with _lock:
        if not os.path.exists(DATA_FILE):
            state = _empty_state()
            _write(state)
            return state
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[store] Failed to read state file, starting fresh: {e}")
            return _empty_state()


def save(state):
    _ensure_data_dir()
    with _lock:
        _write(state)


def _write(state):
    tmp_file = DATA_FILE + ".tmp"
    with open(tmp_file, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp_file, DATA_FILE)


def new_incident_id():
    return f"inc_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
