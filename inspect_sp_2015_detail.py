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

items = cache.get("SP_2015", [])
print("==================== SP 2015 DETALHADO ====================")
for it in items:
    conta = it.get("conta", "")
    coluna = it.get("coluna", "")
    cod_conta = str(it.get("cod_conta", "")).strip()
    
    try:
        valor = float(str(it.get("valor", 0)).replace(",", "."))
    except (ValueError, TypeError):
        valor = 0.0
        
    if is_liquidada_col(coluna) and valor > 0:
        conta_norm = normalize_str(conta)
        if "seguranca" in conta_norm or "policiamento" in conta_norm or "defesa civil" in conta_norm or "inteligencia" in conta_norm or "demais" in conta_norm or "fu06" in conta_norm:
            print(f"Conta: {conta:40s} | Cod: {cod_conta:20s} | Coluna: {coluna:35s} | Valor: R$ {valor:,.2f}")
