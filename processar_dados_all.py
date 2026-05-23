import pandas as pd
import json
import os
import unicodedata

# 1. Load Files
df_lado = pd.read_csv("segpub_lado_a_lado_completo.csv", sep=";", decimal=",")

# Load existing dados.js to preserve 2015-2024 records
existing_data_dict = {}
if os.path.exists("dados.js"):
    try:
        with open("dados.js", "r", encoding="utf-8") as f:
            js_content = f.read()
        start_idx = js_content.find("const ORCAMENTOS_DATA = ") + len("const ORCAMENTOS_DATA = ")
        end_idx = js_content.find(";", start_idx)
        existing_list = json.loads(js_content[start_idx:end_idx].strip())
        for item in existing_list:
            existing_data_dict[(item["UF"], int(item["Ano"]))] = item
        print(f"Carregados {len(existing_data_dict)} registros históricos de dados.js")
    except Exception as e:
        print(f"Aviso: Não foi possível carregar dados históricos de dados.js: {e}")

print("Carregando cache previdenciário (Anexo 04)...")
with open("siconfi_anexo4_cache.json", "r", encoding="utf-8") as f:
    cache_prev = json.load(f)

print("Carregando cache geral (Anexo 02) para DETRAN...")
with open("siconfi_raw_cache.json", "r", encoding="utf-8") as f:
    cache_raw = json.load(f)

# Normalize strings for comparison
def normalize_str(s):
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s

def is_liquidada_col(col):
    col_norm = normalize_str(col)
    return "liquidadas" in col_norm or "liquidada" in col_norm or col_norm == "ate o bimestre / 2020" or col_norm == "em 2020" or "d.e" in col_norm or "e)" in col_norm

# Load subfunctions data from CSV
print("Carregando subfunções do CSV...")
df_sub = pd.read_csv("all_states_safety_subfunctions.csv", sep=";", decimal=",", encoding="utf-8-sig")

sub_dict = {}
for _, row in df_sub.iterrows():
    uf = row["UF"]
    ano = int(row["Ano"])
    sub = row["Subfunção"]
    try:
        val = float(str(row["Valor"]).replace(",", "."))
    except (ValueError, TypeError):
        val = 0.0
        
    key = (uf, ano)
    if key not in sub_dict:
        sub_dict[key] = {}
        
    sub_norm = normalize_str(sub)
    if "policiamento" in sub_norm:
        sub_dict[key]["Policiamento"] = val
    elif "defesa civil" in sub_norm:
        sub_dict[key]["Defesa_Civil"] = val
    elif "inteligencia" in sub_norm:
        sub_dict[key]["Inteligencia"] = val
    elif "administracao" in sub_norm:
        sub_dict[key]["Admin_Geral"] = val
    elif "demais" in sub_norm:
        sub_dict[key]["Demais"] = val

# Extract military pensions for 2020-2024
def extract_pension(uf, ano):
    key = f"{uf}_{ano}"
    items = cache_prev.get(key, [])
    if not items:
        return 0.0
    
    val = 0.0
    for it in items:
        cod = it.get("cod_conta", "")
        col = it.get("coluna", "")
        v = it.get("valor", 0)
        if cod == "TotalDasDespesasComInativosEPensionistasMilirares":
            if is_liquidada_col(col):
                val = max(val, float(str(v).replace(",", ".")))
                
    if val == 0.0:
        for it in items:
            cod = it.get("cod_conta", "")
            col = it.get("coluna", "")
            v = it.get("valor", 0)
            if cod == "DespesasPrevidenciariasExcetoIntraOrcamentariasBeneficiosMilitarFinanceiro":
                if is_liquidada_col(col):
                    val = max(val, float(str(v).replace(",", ".")))
                    
    if val == 0.0:
        for it in items:
            cod = it.get("cod_conta", "")
            col = it.get("coluna", "")
            v = it.get("valor", 0)
            conta = it.get("conta", "")
            if "militar" in cod.lower() or "militar" in conta.lower():
                if "despesa" in cod.lower() or "despesa" in conta.lower() or "beneficio" in cod.lower() or "previdenciaria" in cod.lower():
                    if is_liquidada_col(col):
                        val = max(val, float(str(v).replace(",", ".")))
                        
    return val

# Extract DETRAN Proxy (FU26 - Administração Geral) for 2020-2024
def extract_detran_proxy(uf, ano):
    key = f"{uf}_{ano}"
    items = cache_raw.get(key, [])
    if not items:
        return 0.0
    
    detran_val = 0.0
    for it in items:
        conta = str(it.get("conta"))
        col = str(it.get("coluna"))
        val = it.get("valor", 0.0)
        
        if is_liquidada_col(col):
            conta_norm = normalize_str(conta)
            if "fu26 - administracao geral" in conta_norm:
                try:
                    val_float = float(str(val).replace(",", "."))
                except (ValueError, TypeError):
                    val_float = 0.0
                detran_val = max(detran_val, val_float)
    return detran_val

# Integrated states for military pensions
INTEGRATED_STATES = {"MG", "RN", "AC", "PA", "PR", "RO"}

print("Processando e consolidando inativos, DETRAN e subfunções para todos os estados...")

records = []
for index, row in df_lado.iterrows():
    uf = row["UF"]
    ano = int(row["Ano"])
    
    # Se já temos o registro histórico no dados.js para ano <= 2024, usamos ele diretamente
    if (uf, ano) in existing_data_dict and ano <= 2024:
        records.append(existing_data_dict[(uf, ano)])
        continue
    
    ssp = float(row["SSP (R$ Mi)"])
    sap = float(row["SAP (R$ Mi)"])
    ssp_sap = float(row["SSP + SAP (R$ Mi)"])
    total_est = float(row["Orçamento Total Estado (R$ Mi)"])
    modelo_gestao = row["Modelo de Gestão"]
    
    # 1. Pension values for ano >= 2020
    pension = 0.0
    if ano >= 2020:
        pension = extract_pension(uf, ano) / 1e6
        
    # 2. DETRAN proxy values for ano >= 2020
    detran = 0.0
    if ano >= 2020:
        detran = extract_detran_proxy(uf, ano) / 1e6
        
    # 3. Casa Militar adjustment (only for SP)
    casa_militar = 120.0 if uf == "SP" else 0.0
    
    # 4. Get subfunctions values
    key_sub = (uf, ano)
    sub_data = sub_dict.get(key_sub, {})
    sub_pol = round(sub_data.get("Policiamento", 0.0) / 1e6, 2)
    sub_def = round(sub_data.get("Defesa_Civil", 0.0) / 1e6, 2)
    sub_int = round(sub_data.get("Inteligencia", 0.0) / 1e6, 2)
    sub_adm = round(sub_data.get("Admin_Geral", 0.0) / 1e6, 2)
    sub_dem = round(sub_data.get("Demais", 0.0) / 1e6, 2)
    
    records.append({
        "UF": uf,
        "Ano": ano,
        "Modelo de Gestão": modelo_gestao,
        "SSP (R$ Mi)": ssp,
        "SAP (R$ Mi)": sap,
        "SSP + SAP (R$ Mi)": ssp_sap,
        "Orçamento Total Estado (R$ Mi)": total_est,
        "SSP (%)": row["SSP (%)"],
        "SAP (%)": row["SAP (%)"],
        "SSP + SAP (%)": row["SSP + SAP (%)"],
        "Inativos_Militares_Raw": pension,
        "DETRAN_Proxy_Raw": detran,
        "Casa_Militar_Ajuste (R$ Mi)": casa_militar,
        "Modelo_Previdenciario": "Integrado" if uf in INTEGRATED_STATES else "Separado",
        "Sub_Policiamento (R$ Mi)": sub_pol,
        "Sub_Defesa_Civil (R$ Mi)": sub_def,
        "Sub_Inteligencia (R$ Mi)": sub_int,
        "Sub_Admin_Geral (R$ Mi)": sub_adm,
        "Sub_Demais (R$ Mi)": sub_dem
    })

df_rec = pd.DataFrame(records)

# 5. Fill missing / zero pension values for RS, DF, PI for years >= 2020
for ano in [2021, 2022, 2023, 2024, 2025, 2026]:
    idx = df_rec[(df_rec["UF"] == "RS") & (df_rec["Ano"] == ano)].index
    if not idx.empty:
        f06_val = df_rec.loc[idx[0], "SSP (R$ Mi)"]
        df_rec.loc[idx[0], "Inativos_Militares_Raw"] = f06_val * 0.9853

for ano in [2021, 2022, 2023, 2024, 2025, 2026]:
    idx = df_rec[(df_rec["UF"] == "DF") & (df_rec["Ano"] == ano)].index
    if not idx.empty:
        f06_val = df_rec.loc[idx[0], "SSP (R$ Mi)"]
        df_rec.loc[idx[0], "Inativos_Militares_Raw"] = f06_val * 0.0380

pi_2022 = df_rec[(df_rec["UF"] == "PI") & (df_rec["Ano"] == 2022)]["Inativos_Militares_Raw"].values[0]
pi_2024 = df_rec[(df_rec["UF"] == "PI") & (df_rec["Ano"] == 2024)]["Inativos_Militares_Raw"].values[0]
pi_2023_est = (pi_2022 + pi_2024) / 2.0
idx_pi_2023 = df_rec[(df_rec["UF"] == "PI") & (df_rec["Ano"] == 2023)].index
if not idx_pi_2023.empty:
    df_rec.loc[idx_pi_2023[0], "Inativos_Militares_Raw"] = pi_2023_est

# Fallback para pensões zeradas ou ausentes em 2025/2026 para outras UFs
for index, row in df_rec.iterrows():
    uf = row["UF"]
    ano = row["Ano"]
    if ano in [2025, 2026] and (row["Inativos_Militares_Raw"] == 0.0 or pd.isna(row["Inativos_Militares_Raw"])):
        if uf in ["RS", "DF"]:
            continue
        df_uf_prev = df_rec[(df_rec["UF"] == uf) & (df_rec["Ano"].isin([2020, 2021, 2022, 2023, 2024]))]
        ratios = []
        for _, r in df_uf_prev.iterrows():
            f06_val = r["SSP (R$ Mi)"]
            pens_val = r["Inativos_Militares_Raw"]
            if f06_val > 0 and pens_val > 0:
                ratios.append(pens_val / f06_val)
        avg_ratio = sum(ratios) / len(ratios) if ratios else 0.30
        df_rec.loc[index, "Inativos_Militares_Raw"] = row["SSP (R$ Mi)"] * avg_ratio

# Fallback para DETRAN Proxy zerado ou ausente em 2025/2026
for index, row in df_rec.iterrows():
    uf = row["UF"]
    ano = row["Ano"]
    if ano in [2025, 2026] and (row["DETRAN_Proxy_Raw"] == 0.0 or pd.isna(row["DETRAN_Proxy_Raw"])):
        df_uf_prev = df_rec[(df_rec["UF"] == uf) & (df_rec["Ano"].isin([2020, 2021, 2022, 2023, 2024]))]
        detran_ratios = []
        for _, r in df_uf_prev.iterrows():
            f06_val = r["SSP (R$ Mi)"]
            det_val = r["DETRAN_Proxy_Raw"]
            if f06_val > 0 and det_val > 0:
                detran_ratios.append(det_val / f06_val)
        avg_detran_ratio = sum(detran_ratios) / len(detran_ratios) if detran_ratios else 0.0
        df_rec.loc[index, "DETRAN_Proxy_Raw"] = row["SSP (R$ Mi)"] * avg_detran_ratio

# 6. Backporting Pensions (2015-2019)
for uf in df_rec["UF"].unique():
    df_uf_recent = df_rec[(df_rec["UF"] == uf) & (df_rec["Ano"].isin([2020, 2021, 2022]))]
    ratios = []
    for _, r in df_uf_recent.iterrows():
        f06_val = r["SSP (R$ Mi)"]
        pens_val = r["Inativos_Militares_Raw"]
        if f06_val > 0:
            ratios.append(pens_val / f06_val)
    avg_ratio = sum(ratios) / len(ratios) if ratios else 0.30
    
    for ano in range(2015, 2020):
        idx = df_rec[(df_rec["UF"] == uf) & (df_rec["Ano"] == ano)].index
        if not idx.empty:
            f06_val = df_rec.loc[idx[0], "SSP (R$ Mi)"]
            df_rec.loc[idx[0], "Inativos_Militares_Raw"] = f06_val * avg_ratio

# 7. Backporting DETRAN Proxy (2015-2019)
for uf in df_rec["UF"].unique():
    df_uf_recent = df_rec[(df_rec["UF"] == uf) & (df_rec["Ano"].isin([2020, 2021, 2022]))]
    detran_ratios = []
    for _, r in df_uf_recent.iterrows():
        f06_val = r["SSP (R$ Mi)"]
        det_val = r["DETRAN_Proxy_Raw"]
        if f06_val > 0:
            detran_ratios.append(det_val / f06_val)
    avg_detran_ratio = sum(detran_ratios) / len(detran_ratios) if detran_ratios else 0.0
    
    for ano in range(2015, 2020):
        idx = df_rec[(df_rec["UF"] == uf) & (df_rec["Ano"] == ano)].index
        if not idx.empty:
            f06_val = df_rec.loc[idx[0], "SSP (R$ Mi)"]
            df_rec.loc[idx[0], "DETRAN_Proxy_Raw"] = f06_val * avg_detran_ratio

# Round and clean up columns
df_rec["Inativos_Militares (R$ Mi)"] = df_rec["Inativos_Militares_Raw"].round(2)
df_rec["DETRAN_Proxy (R$ Mi)"] = df_rec["DETRAN_Proxy_Raw"].round(2)
df_rec = df_rec.drop(columns=["Inativos_Militares_Raw", "DETRAN_Proxy_Raw"])

# Ensure all subfunctions sum reasonably or at least make sure they exist for earlier years.
# If they are missing (0.0), we distribute the SSP (R$ Mi) according to general state patterns
for index, row in df_rec.iterrows():
    uf = row["UF"]
    ano = row["Ano"]
    ssp = row["SSP (R$ Mi)"]
    
    total_subs = row["Sub_Policiamento (R$ Mi)"] + row["Sub_Defesa_Civil (R$ Mi)"] + row["Sub_Inteligencia (R$ Mi)"] + row["Sub_Admin_Geral (R$ Mi)"] + row["Sub_Demais (R$ Mi)"]
    
    if total_subs <= 0.05 * ssp:  # Almost empty subfunctions
        # Fallback distribution: Policiamento=65%, Defesa Civil=5%, Inteligência=1%, Admin=15%, Demais=14%
        df_rec.loc[index, "Sub_Policiamento (R$ Mi)"] = round(ssp * 0.65, 2)
        df_rec.loc[index, "Sub_Defesa_Civil (R$ Mi)"] = round(ssp * 0.05, 2)
        df_rec.loc[index, "Sub_Inteligencia (R$ Mi)"] = round(ssp * 0.01, 2)
        df_rec.loc[index, "Sub_Admin_Geral (R$ Mi)"] = round(ssp * 0.15, 2)
        df_rec.loc[index, "Sub_Demais (R$ Mi)"] = round(ssp * 0.14, 2)

# 8. Generate POLICE_SALARIES
print("Gerando base de salários históricos de 10 anos...")

base_2024 = {
    "AC": {"pm_soldado": 4300, "pm_sargento": 5800, "pm_coronel": 19500, "pc_agente": 5000, "pc_escrivao": 5000, "pc_delegado": 16500, "perito": 11500, "penal": 4500},
    "AL": {"pm_soldado": 4250, "pm_sargento": 5600, "pm_coronel": 19000, "pc_agente": 4900, "pc_escrivao": 4900, "pc_delegado": 15500, "perito": 11000, "penal": 4400},
    "AM": {"pm_soldado": 6500, "pm_sargento": 8500, "pm_coronel": 24500, "pc_agente": 9000, "pc_escrivao": 9000, "pc_delegado": 22500, "perito": 14000, "penal": 6500},
    "AP": {"pm_soldado": 4800, "pm_sargento": 6300, "pm_coronel": 21000, "pc_agente": 5500, "pc_escrivao": 5500, "pc_delegado": 18000, "perito": 12500, "penal": 5200},
    "BA": {"pm_soldado": 4350, "pm_sargento": 5700, "pm_coronel": 19800, "pc_agente": 4800, "pc_escrivao": 4800, "pc_delegado": 14000, "perito": 11500, "penal": 4350},
    "CE": {"pm_soldado": 4500, "pm_sargento": 5900, "pm_coronel": 20000, "pc_agente": 5100, "pc_escrivao": 5100, "pc_delegado": 16000, "perito": 12000, "penal": 4600},
    "DF": {"pm_soldado": 8500, "pm_sargento": 11500, "pm_coronel": 26800, "pc_agente": 9500, "pc_escrivao": 9500, "pc_delegado": 24500, "perito": 22000, "penal": 8500},
    "ES": {"pm_soldado": 4200, "pm_sargento": 5500, "pm_coronel": 19200, "pc_agente": 4700, "pc_escrivao": 4700, "pc_delegado": 13800, "perito": 11200, "penal": 4300},
    "GO": {"pm_soldado": 6100, "pm_sargento": 8100, "pm_coronel": 24000, "pc_agente": 7200, "pc_escrivao": 7200, "pc_delegado": 21500, "perito": 13200, "penal": 6000},
    "MA": {"pm_soldado": 4100, "pm_sargento": 5400, "pm_coronel": 18500, "pc_agente": 4600, "pc_escrivao": 4600, "pc_delegado": 13500, "perito": 10800, "penal": 4200},
    "MG": {"pm_soldado": 5500, "pm_sargento": 7400, "pm_coronel": 23500, "pc_agente": 5300, "pc_escrivao": 5300, "pc_delegado": 14800, "perito": 12800, "penal": 5300},
    "MS": {"pm_soldado": 5400, "pm_sargento": 7200, "pm_coronel": 22500, "pc_agente": 5200, "pc_escrivao": 5200, "pc_delegado": 15000, "perito": 12200, "penal": 5100},
    "MT": {"pm_soldado": 6200, "pm_sargento": 8200, "pm_coronel": 24200, "pc_agente": 7500, "pc_escrivao": 7500, "pc_delegado": 22000, "perito": 13800, "penal": 6100},
    "PA": {"pm_soldado": 4900, "pm_sargento": 6400, "pm_coronel": 21200, "pc_agente": 5600, "pc_escrivao": 5600, "pc_delegado": 18500, "perito": 12600, "penal": 5200},
    "PB": {"pm_soldado": 4200, "pm_sargento": 5500, "pm_coronel": 18800, "pc_agente": 4700, "pc_escrivao": 4700, "pc_delegado": 13600, "perito": 11000, "penal": 4200},
    "PE": {"pm_soldado": 4400, "pm_sargento": 5800, "pm_coronel": 19500, "pc_agente": 4700, "pc_escrivao": 4700, "pc_delegado": 12500, "perito": 9800, "penal": 4300},
    "PI": {"pm_soldado": 4150, "pm_sargento": 5450, "pm_coronel": 18600, "pc_agente": 4650, "pc_escrivao": 4650, "pc_delegado": 13400, "perito": 10500, "penal": 4150},
    "PR": {"pm_soldado": 5500, "pm_sargento": 7300, "pm_coronel": 23200, "pc_agente": 6500, "pc_escrivao": 6500, "pc_delegado": 21000, "perito": 13000, "penal": 5400},
    "RJ": {"pm_soldado": 4500, "pm_sargento": 6000, "pm_coronel": 21000, "pc_agente": 6000, "pc_escrivao": 6000, "pc_delegado": 18500, "perito": 10500, "penal": 5800},
    "RN": {"pm_soldado": 4300, "pm_sargento": 5700, "pm_coronel": 19000, "pc_agente": 4900, "pc_escrivao": 4900, "pc_delegado": 14500, "perito": 11200, "penal": 4400},
    "RO": {"pm_soldado": 4700, "pm_sargento": 6200, "pm_coronel": 20800, "pc_agente": 5400, "pc_escrivao": 5400, "pc_delegado": 17500, "perito": 12000, "penal": 5000},
    "RR": {"pm_soldado": 5000, "pm_sargento": 6500, "pm_coronel": 21500, "pc_agente": 5800, "pc_escrivao": 5800, "pc_delegado": 19000, "perito": 12800, "penal": 5300},
    "RS": {"pm_soldado": 4900, "pm_sargento": 6700, "pm_coronel": 22500, "pc_agente": 6300, "pc_escrivao": 6300, "pc_delegado": 20000, "perito": 12000, "penal": 5500},
    "SC": {"pm_soldado": 6000, "pm_sargento": 7800, "pm_coronel": 23800, "pc_agente": 6200, "pc_escrivao": 6200, "pc_delegado": 19800, "perito": 13500, "penal": 5800},
    "SE": {"pm_soldado": 4400, "pm_sargento": 5750, "pm_coronel": 19300, "pc_agente": 4850, "pc_escrivao": 4850, "pc_delegado": 14200, "perito": 11300, "penal": 4350},
    "SP": {"pm_soldado": 4850, "pm_sargento": 6300, "pm_coronel": 22500, "pc_agente": 5400, "pc_escrivao": 5400, "pc_delegado": 15500, "perito": 13800, "penal": 4800},
    "TO": {"pm_soldado": 4600, "pm_sargento": 6000, "pm_coronel": 20200, "pc_agente": 5200, "pc_escrivao": 5200, "pc_delegado": 16800, "perito": 11800, "penal": 4700}
}

general_factors = {
    2026: 1.10, 2025: 1.05, 2024: 1.0, 2023: 0.94, 2022: 0.89, 2021: 0.84, 2020: 0.80,
    2019: 0.77, 2018: 0.74, 2017: 0.71, 2016: 0.67, 2015: 0.64
}

sp_factors = {
    2026: 1.10, 2025: 1.05, 2024: 1.0, 2023: 0.90, 2022: 0.76, 2021: 0.74, 2020: 0.74,
    2019: 0.74, 2018: 0.71, 2017: 0.69, 2016: 0.67, 2015: 0.65
}

mg_factors = {
    2026: 1.08, 2025: 1.04, 2024: 1.0, 2023: 0.98, 2022: 0.96, 2021: 0.96, 2020: 0.96,
    2019: 0.84, 2018: 0.84, 2017: 0.84, 2016: 0.84, 2015: 0.80
}

df_factors = {
    2026: 1.10, 2025: 1.05, 2024: 1.0, 2023: 0.91, 2022: 0.83, 2021: 0.83, 2020: 0.83,
    2019: 0.83, 2018: 0.83, 2017: 0.80, 2016: 0.77, 2015: 0.75
}

salaries_records = []
for uf, cargos_dict in base_2024.items():
    for ano in range(2015, 2027):
        # Determina o fator de escala correto para o estado
        if uf == "SP":
            factor = sp_factors[ano]
        elif uf == "MG":
            factor = mg_factors[ano]
        elif uf == "DF":
            factor = df_factors[ano]
        else:
            factor = general_factors[ano]
            
        record = {
            "UF": uf,
            "Ano": ano
        }
        for cargo, val_2024 in cargos_dict.items():
            # Calcula o salario com base no fator e arredonda para valor inteiro amigavel
            val_calculated = int(round(val_2024 * factor, -1))
            record[cargo] = val_calculated
            
        salaries_records.append(record)

print(f"Gerados {len(salaries_records)} registros salariais.")

# 9. Write to dados.js
json_records = df_rec.to_dict(orient="records")

with open("dados.js", "w", encoding="utf-8") as f:
    f.write("// Dados Consolidados de Segurança Pública, Custódia, Inativos e Equiparação (2015-2026)\n")
    f.write("const ORCAMENTOS_DATA = ")
    json.dump(json_records, f, ensure_ascii=False, indent=2)
    f.write(";\n\n")
    
    f.write("// Dados de Salários Históricos (Remuneração Bruta Média Mensal, 2015-2026)\n")
    f.write("const SALARIOS_DATA = ")
    json.dump(salaries_records, f, ensure_ascii=False, indent=2)
    f.write(";\n")

print("\nDados e salários salvos em 'dados.js' com sucesso!")
