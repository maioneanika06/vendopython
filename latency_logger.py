import csv
import json
import time
from pathlib import Path


LOG_DIR = Path(__file__).resolve().parent / "latency_logs"
LOG_FILE = LOG_DIR / "raspi_latency.csv"
FIELDS = [
    "timestamp",
    "side",
    "session_id",
    "attendee_id",
    "process",
    "latency_sec",
    "status",
    "metadata",
]


def now():
    return time.perf_counter()


def _ensure_log_file():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if not LOG_FILE.exists():
        with LOG_FILE.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=FIELDS)
            writer.writeheader()


def _write_row(row):
    _ensure_log_file()
    with LOG_FILE.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writerow(row)


class LatencyRun:
    def __init__(self, side, button_pressed_at=None):
        self.side = side
        self.session_id = str(int(time.time() * 1000))
        self.attendee_id = ""
        self.start_time = button_pressed_at or now()

    def set_attendee(self, attendee_id):
        self.attendee_id = str(attendee_id or "")

    def record(self, process, start_time, end_time=None, status="success", metadata=None):
        end_time = end_time or now()
        latency_sec = max(0, end_time - start_time)
        row = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "side": self.side,
            "session_id": self.session_id,
            "attendee_id": self.attendee_id,
            "process": process,
            "latency_sec": f"{latency_sec:.3f}",
            "status": status,
            "metadata": json.dumps(metadata or {}, ensure_ascii=True),
        }
        _write_row(row)
        print(
            f"[LATENCY] {self.side} {process}: {latency_sec:.3f}s "
            f"({status})"
        )
        return latency_sec

    def record_total(self, status="success", metadata=None):
        return self.record("button_to_idle_result", self.start_time, status=status, metadata=metadata)
