#!/usr/bin/env python3
"""
publish_carousel.py - posting carousel ke Instagram Business/Creator account
BINAMU via Instagram Graph API (Content Publishing).

Pemakaian:
  python3 publish_carousel.py queue/2026-11-09-cek-backup.json           # dry-run (default)
  python3 publish_carousel.py queue/2026-11-09-cek-backup.json --live    # posting beneran

Format file queue (JSON):
{
  "caption": "teks caption lengkap termasuk hashtag",
  "images": [
    "https://binamu.id/media/carousel-01/slide-1.jpg",
    "https://binamu.id/media/carousel-01/slide-2.jpg"
  ],
  "approved_by": "Syamsul",
  "approved_at": "2026-11-07T18:00:00+07:00"
}

Aturan:
- Post TANPA field approved_by tidak akan diposting (dicegah di kode).
- Gambar harus JPEG, URL publik, maksimal 10 slide, rasio 4:5 disarankan (1080x1350).
- Token dan ID dibaca dari environment, tidak pernah ditulis di file ini.

Environment yang dibutuhkan (isi di .env, jangan dibagikan):
  IG_USER_ID=...            # ID akun IG Business BINAMU
  IG_ACCESS_TOKEN=...       # long-lived token (berlaku sekitar 60 hari)
  GRAPH_VERSION=v21.0       # cek versi terbaru di dokumentasi Meta
"""

import json
import os
import sys
import time
from datetime import datetime

import requests

GRAPH_VERSION = os.getenv("GRAPH_VERSION", "v21.0")
BASE = f"https://graph.facebook.com/{GRAPH_VERSION}"
IG_USER_ID = os.getenv("IG_USER_ID", "")
TOKEN = os.getenv("IG_ACCESS_TOKEN", "")
MAX_SLIDES = 10


def fail(msg: str) -> None:
    print(f"[ERROR] {msg}")
    sys.exit(1)


def load_queue(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        post = json.load(f)

    if not post.get("approved_by"):
        fail("Post belum di-approve (field approved_by kosong). Dibatalkan.")
    if not post.get("caption"):
        fail("Caption kosong.")
    images = post.get("images", [])
    if not 2 <= len(images) <= MAX_SLIDES:
        fail(f"Carousel harus 2-{MAX_SLIDES} gambar, sekarang {len(images)}.")
    for url in images:
        if not url.startswith("https://"):
            fail(f"URL gambar harus https publik: {url}")
    return post


def graph_post(endpoint: str, data: dict) -> dict:
    data = {**data, "access_token": TOKEN}
    r = requests.post(f"{BASE}/{endpoint}", data=data, timeout=60)
    if r.status_code != 200:
        fail(f"Graph API {endpoint} gagal: {r.status_code} {r.text}")
    return r.json()


def graph_get(path: str, params: dict) -> dict:
    r = requests.get(f"{BASE}/{path}", params={**params, "access_token": TOKEN}, timeout=60)
    if r.status_code != 200:
        fail(f"Graph API GET {path} gagal: {r.status_code} {r.text}")
    return r.json()


def wait_until_ready(container_id: str, timeout_s: int = 300) -> None:
    """Container gambar/video perlu diproses Meta sebelum bisa dipublish."""
    start = time.time()
    while time.time() - start < timeout_s:
        status = graph_get(container_id, {"fields": "status_code"}).get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            fail(f"Container {container_id} status {status}")
        time.sleep(5)
    fail(f"Timeout menunggu container {container_id}")


def publish_carousel(post: dict, live: bool) -> None:
    images = post["images"]
    caption = post["caption"]

    print(f"Caption ({len(caption)} karakter):")
    print("-" * 40)
    print(caption)
    print("-" * 40)
    print(f"Jumlah slide: {len(images)}")

    if not live:
        print("[DRY-RUN] Tidak ada yang diposting. Jalankan dengan --live untuk posting beneran.")
        return

    if not (IG_USER_ID and TOKEN):
        fail("IG_USER_ID atau IG_ACCESS_TOKEN belum di-set di environment.")

    # 1. Buat container untuk tiap slide
    child_ids = []
    for url in images:
        res = graph_post(
            f"{IG_USER_ID}/media",
            {"image_url": url, "is_carousel_item": "true"},
        )
        child_ids.append(res["id"])
        print(f"  slide container dibuat: {res['id']}")

    for cid in child_ids:
        wait_until_ready(cid)

    # 2. Buat container carousel induk
    parent = graph_post(
        f"{IG_USER_ID}/media",
        {
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
        },
    )
    wait_until_ready(parent["id"])

    # 3. Publish
    published = graph_post(
        f"{IG_USER_ID}/media_publish",
        {"creation_id": parent["id"]},
    )
    print(f"[OK] Posted. Media ID: {published.get('id')} at {datetime.now().isoformat()}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        fail("Pemakaian: publish_carousel.py <queue.json> [--live]")
    live_mode = "--live" in sys.argv
    queue_path = sys.argv[1]
    publish_carousel(load_queue(queue_path), live=live_mode)
