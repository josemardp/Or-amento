import json
import os
import unicodedata

CACHE_FILE = "siconfi_raw_cache.json"

def normalize_str(s):
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s

def is_liquidada_col(col):
    col = normalize_str(col)
    return ("despesas liquidadas" in col and "ate o bimestre" in col) or "ate o bimestre (d)" in col

if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        cache = json.load(f)
    
    ac_2015 = cache.get("AC_2015", [])
    if ac_2015:
        accounts = {}
        for it in ac_2015:
            coluna = it.get("coluna", "")
            if is_liquidada_col(coluna):
                rotulo = it.get("rotulo", "")
                conta = it.get("conta", "")
                cod_conta = it.get("cod_conta", "")
                try:
                    valor = float(str(it.get("valor", 0)).replace(",", "."))
                except:
                    valor = 0.0
                key = (rotulo, conta, cod_conta)
                accounts[key] = accounts.get(key, 0.0) + valor
                
        print("\nUnique Accounts in AC 2015 (Liquidado):")
        for (rotulo, conta, cod_conta), val in sorted(accounts.items()):
            if val > 0:
                print(f"Rotulo: {rotulo} | Conta: {conta} | Cod: {cod_conta} | Valor: {val:,.2f}")
else:
    print("Cache not found")
