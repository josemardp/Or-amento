import json
import os

CACHE_FILE = "siconfi_raw_cache.json"

if not os.path.exists(CACHE_FILE):
    print("Cache não encontrado!")
    exit(1)

with open(CACHE_FILE, "r", encoding="utf-8") as f:
    cache = json.load(f)

# Let's inspect a few items from MG_2023 and MG_2015
for key in ["MG_2023", "MG_2015"]:
    print(f"\n==================== {key} ====================")
    items = cache.get(key, [])
    print(f"Total items: {len(items)}")
    for i, it in enumerate(items[:10]):
        print(f"Item {i}: {it}")
