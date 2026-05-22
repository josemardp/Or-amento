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
for uf in cache.keys():
    if not uf.endswith("_2023"):
        continue
    uf_name = uf.split("_")[0]
    items = cache[uf]
    
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
                elif any(sub in conta_norm for sub in ["policiamento", "defesa civil", "inteligencia", "administracao geral", "demais subfuncoes", "fu06", "previdencia"]):
                    # Group by conta
                    subfuncs[conta] = max(subfuncs.get(conta, 0.0), valor)

    for sub, val in subfuncs.items():
        records.append({
            "UF": uf_name,
            "Subfunção": sub,
            "Valor (R$ Mi)": round(val / 1e6, 2),
            "Total F06 (R$ Mi)": round(total_f06 / 1e6, 2),
            "Pct (%)": round((val / total_f06) * 100, 2) if total_f06 > 0 else 0.0
        })

df = pd.DataFrame(records)
print(f"Total de registros encontrados: {len(df)}")
if not df.empty:
    df_high = df[df["Pct (%)"] > 10.0].sort_values(by=["UF", "Pct (%)"], ascending=[True, False])
    print("\nSubfunções com mais de 10% do orçamento de Segurança Pública em 2023:")
    print(df_high.to_string(index=False))
else:
    print("DataFrame está vazio.")
