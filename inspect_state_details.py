import pandas as pd
import json

df_sub = pd.read_csv("all_states_safety_subfunctions.csv", sep=";")
df_sub["Pct"] = df_sub["Pct"].astype(str).str.replace(",", ".").astype(float)
df_sub["Valor"] = df_sub["Valor"].astype(str).str.replace(",", ".").astype(float)

df_comp = pd.read_csv("segpub_completo.csv", sep=";", decimal=",")

with open("siconfi_anexo4_cache.json", "r", encoding="utf-8") as f:
    cache = json.load(f)

def get_pension(uf, ano):
    key = f"{uf}_{ano}"
    items = cache.get(key, [])
    val = 0.0
    for it in items:
        cod = it.get("cod_conta", "")
        col = it.get("coluna", "")
        v = it.get("valor", 0)
        if cod == "TotalDasDespesasComInativosEPensionistasMilirares":
            if "liquidadas" in col.lower() or "pagas" in col.lower() or "realizadas" in col.lower() or "e" in col.lower():
                val = max(val, float(str(v).replace(",", ".")))
    if val == 0.0:
        # Check 2020 alternative code
        for it in items:
            cod = it.get("cod_conta", "")
            col = it.get("coluna", "")
            v = it.get("valor", 0)
            if cod == "DespesasPrevidenciariasExcetoIntraOrcamentariasBeneficiosMilitarFinanceiro":
                if "liquidadas" in col.lower() or "pagas" in col.lower() or "realizadas" in col.lower() or "e" in col.lower():
                    val = max(val, float(str(v).replace(",", ".")))
    return val

print("UF | F06 Total | Pension Anexo 04 | Demais Subf | Ativos se Subtrai | Ativos se Mantém")
print("-" * 80)

for uf in sorted(df_comp["UF"].unique()):
    row_2023 = df_comp[(df_comp["UF"] == uf) & (df_comp["Ano"] == 2023)]
    if row_2023.empty:
        continue
    f06_total = row_2023["SSP_Total_R$"].values[0]
    pension = get_pension(uf, 2023)
    
    # Get Demais Subfunções
    df_uf = df_sub[(df_sub["UF"] == uf) & (df_sub["Ano"] == 2023) & (df_sub["Subfunção"] == "Demais Subfunções")]
    demais = df_uf["Valor"].values[0] if not df_uf.empty else 0.0
    
    ativos_sub = f06_total - pension
    ativos_mantem = f06_total
    
    print(f"{uf} | {f06_total/1e6:,.1f} Mi | {pension/1e6:,.1f} Mi | {demais/1e6:,.1f} Mi | {ativos_sub/1e6:,.1f} Mi | {ativos_mantem/1e6:,.1f} Mi")
