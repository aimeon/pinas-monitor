#!/usr/bin/env python3
"""Collect SMART health and disk space measurements for PiNAS Monitor.

Based on the original PiNAS collector. Configure DRIVES for your own devices
before installing. Do not commit machine-specific device IDs or serial numbers.
"""
import csv
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

# Example only. Replace device, mount, and smartctl_type for each drive.
# For stable device paths, use /dev/disk/by-id locally, but don't commit IDs
# containing drive serial numbers.
DRIVES = {
    "Disk 1": {
        "device": "/dev/sda",
        "mount": "/mnt/disk1",
        "smartctl_type": "sntasmedia",
    },
}

LOG = Path("/var/log/pinas-smart/history.csv")
LOG.parent.mkdir(parents=True, exist_ok=True)

fields = [
    "timestamp", "drive", "temperature_c", "wear_pct",
    "spare_pct", "power_on_hours", "unsafe_shutdowns",
    "media_errors", "free_gb", "status",
]


def check(name, config):
    row = dict.fromkeys(fields, "")
    row["timestamp"] = datetime.now().astimezone().isoformat(timespec="seconds")
    row["drive"] = name
    alerts = []

    mount = config["mount"]
    device = config["device"]

    if not subprocess.run(
        ["mountpoint", "-q", mount], check=False
    ).returncode == 0:
        alerts.append("NOT_MOUNTED")
    else:
        usage = shutil.disk_usage(mount)
        row["free_gb"] = round(usage.free / 1e9, 2)
        if usage.free / usage.total < 0.05:
            alerts.append("LOW_SPACE")

    result = subprocess.run(
        ["smartctl", "-a", "-j", "-d", config.get("smartctl_type", "sntasmedia"), device],
        capture_output=True, text=True
    )

    try:
        data = json.loads(result.stdout)
        health = data["nvme_smart_health_information_log"]

        mapping = {
            "temperature_c": "temperature",
            "wear_pct": "percentage_used",
            "spare_pct": "available_spare",
            "power_on_hours": "power_on_hours",
            "unsafe_shutdowns": "unsafe_shutdowns",
            "media_errors": "media_errors",
        }
        for field, source in mapping.items():
            row[field] = health.get(source, "")

        if data.get("smart_status", {}).get("passed") is False:
            alerts.append("SMART_FAILED")
        if health.get("critical_warning", 0):
            alerts.append("CRITICAL_WARNING")
        if health.get("temperature", 0) >= 65:
            alerts.append("HIGH_TEMPERATURE")
        if health.get("percentage_used", 0) >= 90:
            alerts.append("HIGH_WEAR")
        if health.get("media_errors", 0) > 0:
            alerts.append("MEDIA_ERRORS")
    except (ValueError, KeyError, TypeError):
        alerts.append("SMART_UNAVAILABLE")

    row["status"] = ",".join(alerts) if alerts else "OK"
    return row


rows = [check(name, config) for name, config in DRIVES.items()]

new_file = not LOG.exists()
with LOG.open("a", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    if new_file:
        writer.writeheader()
    writer.writerows(rows)

for row in rows:
    print(
        f"{row['drive']}: {row['status']} | "
        f"{row['temperature_c']}°C | "
        f"wear {row['wear_pct']}% | "
        f"free {row['free_gb']} GB"
    )
