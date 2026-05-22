import json
import os
import unicodedata
import pandas as pd

CACHE_FILE = "siconfi_raw_cache.json"

def normalize_str(s):
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s

if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        cache = json.load(f)
        
    records = []
    
    for key, items in cache.items():
        if not items:
            continue
        parts = key.split("_")
        uf = parts[0]
        ano = int(parts[1])
        
        # Procurar custódia e reintegração social
        custodia_val_exceto = 0.0
        custodia_val_intra = 0.0
        
        for it in items:
            conta = normalize_str(it.get("conta"))
            coluna = normalize_str(it.get("coluna"))
            cod_conta = str(it.get("cod_conta", "")).strip()
            
            try:
                valor = float(str(it.get("valor", 0)).replace(",", "."))
            except (ValueError, TypeError):
                valor = 0.0
                
            if conta == "custodia e reintegracao social":
                # verificar se é despesa liquidada
                if ("despesas liquidadas" in coluna and "ate o bimestre" in coluna) or "ate o bimestre (d)" in coluna:
                    if cod_conta == "RREO2TotalDespesasIntra":
                        custodia_val_intra = valor
                    elif cod_conta == "RREO2TotalDespesas" or cod_conta == "":
                        custodia_val_exceto = valor
                        
        records.append({
            "UF": uf,
            "Ano": ano,
            "Custodia_Exceto": custodia_val_exceto,
            "Custodia_Intra": custodia_val_intra,
            "Custodia_Total": custodia_val_exceto + custodia_val_intra
        })
        
    df = pd.DataFrame(records)
    print("Resumo do DF de Custódia:")
    print(f"Total registros: {len(df)}")
    print(f"Registros com Custódia > 0: {len(df[df['Custodia_Total'] > 0])}")
    print(f"Registros com Custódia == 0: {len(df[df['Custodia_Total'] == 0])}")
    
    if len(df[df['Custodia_Total'] == 0]) > 0:
        print("\nExemplo de estados/anos onde Custódia é 0:")
        print(df[df['Custodia_Total'] == 0].head(20))
        
else:
    print("Cache não encontrado.")
