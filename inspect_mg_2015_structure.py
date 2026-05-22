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

def is_liquidada_col(col):
    col = normalize_str(col)
    return ("despesas liquidadas" in col and "ate o bimestre" in col) or "ate o bimestre (d)" in col

items = cache.get("MG_2015", [])
print("==================== MG 2015 SEQUECIAL ====================")

ssp_idx = -1
for idx, it in enumerate(items):
    conta = it.get("conta", "")
    coluna = it.get("coluna", "")
    
    if is_liquidada_col(coluna):
        if normalize_str(conta) == "seguranca publica":
            ssp_idx = idx
            break

if ssp_idx != -1:
    print(f"Encontrei 'Segurança Pública' no índice {ssp_idx}. Mostrando vizinhança:")
    # Show 30 items before and 30 items after
    # We only show items with is_liquidada_col to see the hierarchy
    for i in range(max(0, ssp_idx - 30), min(len(items), ssp_idx + 45)):
        it = items[i]
        coluna = it.get("coluna", "")
        if is_liquidada_col(coluna):
            print(f"Index {i:4d} | Conta: {it.get('conta'):35s} | Cod: {it.get('cod_conta'):20s} | Valor: R$ {it.get('valor')}")
else:
    print("Não encontrei a conta 'Segurança Pública' com coluna de liquidadas.")
