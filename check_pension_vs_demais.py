import pandas as pd
import json

df_sub = pd.read_csv("all_states_safety_subfunctions.csv", sep=";")
df_sub["Pct"] = df_sub["Pct"].astype(str).str.replace(",", ".").astype(float)
df_sub["Valor"] = df_sub["Valor"].astype(str).str.replace(",", ".").astype(float)

with open("siconfi_anexo4_cache.json", "r", encoding="utf-8") as f:
    cache = json.load(f)

print("UF | 2023 F06 Total | 2023 Demais Subf | 2023 Anexo 04 Milit | Proporção (%)")
print("-" * 75)

for uf in sorted(df_sub["UF"].unique()):
    # Get Demais Subfunções for 2023
    df_uf = df_sub[(df_sub["UF"] == uf) & (df_sub["Ano"] == 2023) & (df_sub["Subfunção"] == "Demais Subfunções")]
    if df_uf.empty:
        continue
    f06_total = df_uf["Total F06"].values[0]
    # Clean f06_total if string
    if isinstance(f06_total, str):
        f06_total = float(f06_total.replace(",", "."))
    demais_val = df_uf["Valor"].values[0]
    
    # Get Anexo 04 military pension value for 2023
    key = f"{uf}_2023"
    items = cache.get(key, [])
    anexo_val = 0.0
    for it in items:
        cod = it.get("cod_conta", "")
        col = it.get("coluna", "")
        val = it.get("valor", 0)
        if cod == "TotalDasDespesasComInativosEPensionistasMilirares":
            if "liquidadas" in col.lower() or "pagas" in col.lower() or "realizadas" in col.lower() or "e" in col.lower():
                anexo_val = max(anexo_val, float(str(val).replace(",", ".")))
                
    prop = (anexo_val / demais_val) * 100 if demais_val > 0 else 0
    print(f"{uf} | {f06_total/1e6:,.1f} Mi | {demais_val/1e6:,.1f} Mi | {anexo_val/1e6:,.1f} Mi | {prop:.1f}%")
