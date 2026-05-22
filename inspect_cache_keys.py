import json
import os

CACHE_FILE = "siconfi_raw_cache.json"

if os.path.exists(CACHE_FILE):
    # Just read the keys without loading the whole 254MB into memory if possible, 
    # but since it's a JSON file we have to load it or stream it. Let's load the keys.
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        cache = json.load(f)
    print(f"Total keys in cache: {len(cache)}")
    print("Some sample keys:")
    for k in list(cache.keys())[:20]:
        print(f"  - {k} (length: {len(cache[k])})")
else:
    print("Cache not found.")
