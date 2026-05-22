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

for ano in [2015, 2016, 2017]:
    key = f"MG_{ano}"
    items = cache.get(key, [])
    print(f"\n==================== MG {ano} ====================")
    
    # We want to see all accounts in RREO Anexo 02 that have liquidada > 0
    # and their cod_conta, and check if they are safety-related
    seen = {}
    for it in items:
        conta = it.get("conta", "")
        coluna = it.get("coluna", "")
        cod_conta = str(it.get("cod_conta", "")).strip()
        
        try:
            valor = float(str(it.get("valor", 0)).replace(",", "."))
        except (ValueError, TypeError):
            valor = 0.0
            
        if is_liquidada_col(coluna) and valor > 0:
            if cod_conta == "RREO2TotalDespesas" or cod_conta == "":
                # Save the max value for this account
                seen[conta] = max(seen.get(conta, 0.0), valor)
                
    for conta, val in sorted(seen.items()):
        conta_norm = normalize_str(conta)
        if any(x in conta_norm for x in ["seguranca", "policiamento", "defesa civil", "inteligencia", "previdencia", "demais", "fu06"]):
            print(f"  - {conta:40s} | R$ {val:,.2f}")
