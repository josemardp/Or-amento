import json
import os

CACHE_FILE = "siconfi_raw_cache.json"

with open(CACHE_FILE, "r", encoding="utf-8") as f:
    cache = json.load(f)

for key in ["MG_2023", "MG_2015"]:
    print(f"\n==================== {key} ====================")
    items = cache.get(key, [])
    cols = set(it.get("coluna", "") for it in items)
    for c in cols:
        print(f"  - {c}")
