import pandas as pd
import numpy as np

# Load subfunctions
df_sub = pd.read_csv("all_states_safety_subfunctions.csv", sep=";")

# Clean Pct to float
df_sub["Pct"] = df_sub["Pct"].astype(str).str.replace(",", ".").astype(float)
df_sub["Valor"] = df_sub["Valor"].astype(str).str.replace(",", ".").astype(float)

states_demais = []
for uf in sorted(df_sub["UF"].unique()):
    df_uf = df_sub[(df_sub["UF"] == uf) & (df_sub["Ano"] >= 2020)].copy()
    demais_pct = df_uf[df_uf["Subfunção"] == "Demais Subfunções"]["Pct"].mean()
    states_demais.append({
        "UF": uf,
        "Demais Pct Mean": demais_pct
    })

df_res = pd.DataFrame(states_demais).sort_values(by="Demais Pct Mean", ascending=False)
print(df_res.to_string(index=False))
