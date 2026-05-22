import pandas as pd

df = pd.read_csv("segpub_completo.csv", sep=";", decimal=",")

for uf in ["RS", "DF"]:
    print(f"\n=== {uf} Safety Budgets ===")
    df_uf = df[(df["UF"] == uf) & (df["Status"] == "OK")].copy()
    print(df_uf[["Ano", "SSP_Total_R$", "SAP_Total_R$", "Total_Geral_R$"]])
