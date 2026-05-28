import csv
from collections import defaultdict
from pathlib import Path


LOG_FILE = Path(__file__).resolve().parent / "latency_logs" / "raspi_latency.csv"


def summarize():
    if not LOG_FILE.exists():
        print(f"No latency log found: {LOG_FILE}")
        return

    values_by_process = defaultdict(list)
    with LOG_FILE.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row.get("status") not in ("success", "matched"):
                continue
            try:
                values_by_process[row["process"]].append(float(row["latency_sec"]))
            except (KeyError, ValueError):
                continue

    print("\nRaspberry Pi Latency Summary")
    print("-" * 86)
    print(f"{'Process Tested':40} {'Trials':>8} {'Average':>10} {'Fastest':>10} {'Slowest':>10}")
    print("-" * 86)

    for process in sorted(values_by_process):
        values = values_by_process[process]
        average = sum(values) / len(values)
        print(
            f"{process[:40]:40} "
            f"{len(values):8d} "
            f"{average:10.3f} "
            f"{min(values):10.3f} "
            f"{max(values):10.3f}"
        )


if __name__ == "__main__":
    summarize()
