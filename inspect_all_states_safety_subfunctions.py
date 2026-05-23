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

STANDARD_FUNCTIONS = [
    "legislativa", "judiciaria", "essencial a justica", "administracao", "defesa nacional",
    "seguranca publica", "relacoes exteriores", "assistencia social", "previdencia social",
    "saude", "trabalho", "educacao", "cultura", "direitos da cidadania", "urbanismo",
    "habitacao", "saneamento", "gestao ambiental", "ciencia e tecnologia", "agricultura",
    "organizacao agraria", "industria", "comercio e servicos", "comunicacoes", "energia",
    "transporte", "desporto e lazer", "encargos especiais"
]

def extract_safety_subfunctions(uf, ano):
    key = f"{uf}_{ano}"
    items = cache.get(key, [])
    
    # Filter out intra
    items_exceto = [it for it in items if str(it.get("cod_conta", "")).strip() != "RREO2TotalDespesasIntra"]
    
    subfuncs = {}
    total_f06 = 0.0
    
    if ano >= 2018:
        for it in items_exceto:
            conta = it.get("conta", "")
            coluna = it.get("coluna", "")
            cod_conta = str(it.get("cod_conta", "")).strip()
            
            try:
                valor = float(str(it.get("valor", 0)).replace(",", "."))
            except (ValueError, TypeError):
                valor = 0.0
                
            if is_liquidada_col(coluna) and valor > 0:
                conta_norm = normalize_str(conta)
                if conta_norm == "seguranca publica":
                    total_f06 = max(total_f06, valor)
                
                if "fu06" in conta_norm:
                    sub_name = conta.replace("FU06 - ", "").strip()
                    subfuncs[sub_name] = max(subfuncs.get(sub_name, 0.0), valor)
                elif conta_norm in ["policiamento", "defesa civil", "informacao e inteligencia"]:
                    # Fallback for standard safety subfunctions if prefix is missing
                    subfuncs[conta] = max(subfuncs.get(conta, 0.0), valor)
    else:
        # Sequential parser
        current_function = None
        for it in items_exceto:
            conta = it.get("conta", "")
            coluna = it.get("coluna", "")
            cod_conta = str(it.get("cod_conta", "")).strip()
            
            try:
                valor = float(str(it.get("valor", 0)).replace(",", "."))
            except (ValueError, TypeError):
                valor = 0.0
                
            if not is_liquidada_col(coluna) or valor <= 0:
                continue
                
            conta_norm = normalize_str(conta)
            
            is_func = False
            for func in STANDARD_FUNCTIONS:
                if conta_norm == func:
                    is_func = True
                    current_function = func
                    break
                    
            if conta_norm == "seguranca publica":
                total_f06 = max(total_f06, valor)
                    
            if not is_func:
                if current_function == "seguranca publica":
                    subfuncs[conta] = max(subfuncs.get(conta, 0.0), valor)
                    
    return total_f06, subfuncs

records = []
for key in cache.keys():
    parts = key.split("_")
    if len(parts) != 2:
        continue
    uf, ano_str = parts
    try:
        ano = int(ano_str)
    except ValueError:
        continue
        
    tot, subs = extract_safety_subfunctions(uf, ano)
    if tot > 0:
        for sub, val in subs.items():
            records.append({
                "UF": uf,
                "Ano": ano,
                "Total F06": tot,
                "Subfunção": sub,
                "Valor": val,
                "Pct": (val / tot) * 100
            })

df_new = pd.DataFrame(records)
if os.path.exists("all_states_safety_subfunctions.csv"):
    try:
        df_old = pd.read_csv("all_states_safety_subfunctions.csv", sep=";", decimal=",")
        df_old = df_old[~df_old["Ano"].isin([2025, 2026])]
        df = pd.concat([df_old, df_new], ignore_index=True)
    except Exception as e:
        print(f"Erro ao ler all_states_safety_subfunctions.csv: {e}")
        df = df_new
else:
    df = df_new
df.to_csv("all_states_safety_subfunctions.csv", index=False, sep=";", decimal=",", encoding="utf-8-sig")
print("Análise concluída e salva em 'all_states_safety_subfunctions.csv'.")

# Mostrar os estados que têm "Demais Subfunções" ou "Previdência" com valores altos em 2023
df_2023 = df[df["Ano"] == 2023].copy()
df_demais = df_2023[df_2023["Subfunção"].str.contains("Demais|Previdência", case=False, na=False)]
print("\nSubfunções com 'Demais' ou 'Previdência' dentro de F06 (Segurança Pública) em 2023:")
print(df_demais.sort_values(by="Pct", ascending=False).to_string(index=False))
