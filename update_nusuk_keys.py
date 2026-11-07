#!/usr/bin/env python3
"""
Nusuk Master Key Synchronizer
Connects directly to the live cloud keys vault at https://nusukkeys.wajed.bd
to sync verified Nusuk referral codes into your local master keys pool.
"""

import json
import os
import sys
import time
import urllib.request
import urllib.error

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
KEYS_FILE = os.path.join(PROJECT_DIR, "nusuk_keys.txt")
LOG_FILE = os.path.join(PROJECT_DIR, "nusuk_orchestrator.log")

# Primary live cloud vault endpoints
SYNC_URLS = [
    "https://nusukkeys.wajed.bd/api/sync",
    "https://nusuk.wajed.bd/api/sync"
]

BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 NusukMaster/2.0"

def log(msg):
    ts = time.strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{ts} [KeySync] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

def fetch_keys_from_cloud():
    """Fetch all crowdsourced & verified keys from the official live vault"""
    for url in SYNC_URLS:
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": BROWSER_UA, "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if data.get("ok"):
                    keys = [k["code"].strip() for k in data.get("keys", []) if isinstance(k, dict) and "code" in k]
                    if keys:
                        return keys
        except Exception as e:
            log(f"Connection notice for {url}: {e}")
            continue
    return []

def sync_keys():
    """Synchronize local pool with the cloud vault with strict case-insensitive deduplication"""
    existing_keys_upper = set()
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r") as f:
            for line in f:
                k = line.strip()
                if k:
                    existing_keys_upper.add(k.upper())

    initial_count = len(existing_keys_upper)
    log(f"Synchronizing keys pool with https://nusukkeys.wajed.bd... Baseline: {initial_count:,} unique keys.")

    cloud_keys = fetch_keys_from_cloud()
    log(f"Received {len(cloud_keys):,} codes from live vault.")

    new_keys = []
    for k in cloud_keys:
        if len(k) >= 8 and k.startswith("NG-"):
            u = k.upper()
            if u not in existing_keys_upper:
                existing_keys_upper.add(u)
                new_keys.append(k)

    if new_keys:
        with open(KEYS_FILE, "a") as f:
            for k in new_keys:
                f.write(k + "\n")
        log(f"✅ Sync Complete! Added {len(new_keys):,} brand new keys to local master pool.")
    else:
        log("✅ Local pool is already fully synchronized with the cloud vault.")

    total_pool = len(existing_keys_upper)
    log(f"Total Local Pool Size: {total_pool:,} unique keys.")
    return len(new_keys), total_pool

def run_sync_daemon(interval_seconds=300):
    log(f"Starting continuous key updater daemon (polling every {interval_seconds}s)...")
    while True:
        try:
            sync_keys()
        except Exception as e:
            log(f"Daemon exception: {e}")
        time.sleep(interval_seconds)

if __name__ == "__main__":
    if "--daemon" in sys.argv:
        run_sync_daemon()
    else:
        new_count, total = sync_keys()
        print(f"\nSummary: Added {new_count:,} new keys. Grand Total: {total:,} keys.")
