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
    key = f"MG_{ano}"
    items = cache.get(key, [])
    
    total_f06 = 0.0
    # Let's find all accounts for this year
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
                # Check if it's under Função 06 by examining if it has FU06 prefix or if we match subfunctions
                # We know the main accounts in MG
                # Let's print everything matching safety or having 'fu06' or subfunctions
                if conta_norm == "seguranca publica":
                    total_f06 = max(total_f06, valor)
                elif any(sub in conta_norm for sub in ["policiamento", "defesa civil", "inteligencia", "fu06", "demais subfuncoes"]):
                    # Wait, let's also capture any subfunction that is listed in RREO under Função 06
                    records.append({
                        "Ano": ano,
                        "Conta": conta,
                        "Valor (R$ Mi)": round(valor / 1e6, 2)
                    })

# Filter out duplicates and keep max
df = pd.DataFrame(records)
if not df.empty:
    df = df.groupby(["Ano", "Conta"], as_index=False)["Valor (R$ Mi)"].max()
    df = df.sort_values(by=["Ano", "Valor (R$ Mi)"], ascending=[True, False])
    print(df.to_string(index=False))
else:
    print("Nenhum registro encontrado.")
