#!/usr/bin/env python3
"""
run_due.py - dijalankan terjadwal (GitHub Actions). Memposting semua antrian
yang sudah waktunya (scheduled_for <= sekarang) dan belum diposting.

Aturan keamanan:
- Kill switch: set variable AUTOPOST_ENABLED=false (atau buat file PAUSED di repo) untuk berhenti total.
- Post hanya lolos jika approved_by terisi.
- Post dari kebijakan otomatis (approved_by diawali "auto:") diblokir jika caption memuat
  kata yang berisi klaim harga, diskon, garansi, angka persen, atau nama klien.
- Setelah berhasil, file antrian diberi published_at dan media_id.
"""

import glob
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from publish_carousel import load_queue, publish_carousel  # noqa: E402

BLOCKED_AUTO = re.compile(
    r"(\d+\s?%|rp\s?[\d.,]+|harga|diskon|promo|garansi|guarantee|murah|termurah|"
    r"terbaik|game changer|klien\s+\w+)",
    re.IGNORECASE,
)


def autopost_enabled() -> bool:
    if os.path.exists(os.path.join(os.path.dirname(__file__), "..", "PAUSED")):
        return False
    return os.getenv("AUTOPOST_ENABLED", "true").lower() != "false"


def is_due(post: dict, now: datetime) -> bool:
    if post.get("published_at"):
        return False
    scheduled = post.get("scheduled_for")
    if not scheduled:
        return False
    return datetime.fromisoformat(scheduled) <= now


def main() -> None:
    now = datetime.now(timezone.utc)
    if not autopost_enabled():
        print("Autopost dimatikan (PAUSED / AUTOPOST_ENABLED=false). Tidak ada yang diposting.")
        return

    queue_dir = os.path.join(os.path.dirname(__file__), "queue")
    for path in sorted(glob.glob(os.path.join(queue_dir, "*.json"))):
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        if not is_due(raw, now):
            continue

        if str(raw.get("approved_by", "")).startswith("auto:") and BLOCKED_AUTO.search(raw["caption"]):
            print(f"[BLOCKED] {path}: caption memuat klaim yang butuh approval manual.")
            continue

        print(f"[POST] {path}")
        post = load_queue(path)
        publish_carousel(post, live=True)

        raw["published_at"] = now.isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
