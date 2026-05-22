import json
import os
import unicodedata
import pandas as pd

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

records = []
for ano in range(2015, 2025):
    key = f"SP_{ano}"
    items = cache.get(key, [])
    
    total_f06 = 0.0
    subfuncs = {}
    
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
                conta_norm = normalize_str(conta)
                if conta_norm == "seguranca publica":
                    total_f06 = max(total_f06, valor)
                elif any(sub in conta_norm for sub in ["policiamento", "defesa civil", "inteligencia", "fu06", "demais subfuncoes", "demais"]):
                    # Wait, let's filter if it is inside Função 06 or contains fu06
                    if "fu06" in conta_norm or conta_norm in ["policiamento", "defesa civil", "informacao e inteligencia", "demais subfuncoes", "demais"]:
                        subfuncs[conta] = max(subfuncs.get(conta, 0.0), valor)

    for sub, val in subfuncs.items():
        records.append({
            "Ano": ano,
            "Subfunção": sub,
            "Valor (R$ Mi)": round(val / 1e6, 2),
            "Total F06 (R$ Mi)": round(total_f06 / 1e6, 2),
            "Pct (%)": round((val / total_f06) * 100, 2) if total_f06 > 0 else 0.0
        })

df = pd.DataFrame(records)
if not df.empty:
    df = df.groupby(["Ano", "Subfunção"], as_index=False)[["Valor (R$ Mi)", "Total F06 (R$ Mi)", "Pct (%)"]].max()
    df = df.sort_values(by=["Ano", "Valor (R$ Mi)"], ascending=[True, False])
    print(df.to_string(index=False))
else:
    print("Nenhum registro encontrado.")
