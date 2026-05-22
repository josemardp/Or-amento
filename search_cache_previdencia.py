import json
import os
import unicodedata

CACHE_FILE = "siconfi_raw_cache.json"

if not os.path.exists(CACHE_FILE):
    print("Cache não encontrado!")
    exit(1)

with open(CACHE_FILE, "r", encoding="utf-8") as f:
    cache = json.load(f)

def normalize_str(s):
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s

terms = ["militar", "inativo", "pensionista", "reforma"]

seen_contas = set()
for key, items in cache.items():
    for it in items:
        conta = it.get("conta", "")
        conta_norm = normalize_str(conta)
        if any(term in conta_norm for term in terms):
            seen_contas.add(conta)

print("Contas encontradas no cache contendo termos de previdência/inativos:")
for c in sorted(seen_contas):
    print("-", c)
