import pandas as pd
import numpy as np

def main():
    # 1. Carregar os dados completos
    df = pd.read_csv("segpub_completo.csv", sep=";", decimal=",")
    df = df[df["Status"] == "OK"].copy()
    
    # 2. Criar as colunas formatadas em milhões de R$
    df["SSP_Exceto_Mi"] = df["SSP_Exceto_R$"] / 1_000_000
    df["SAP_Exceto_Mi"] = df["SAP_Exceto_R$"] / 1_000_000
    df["SSP_SAP_Exceto_Mi"] = df["SSP_SAP_Exceto_R$"] / 1_000_000
    df["Total_Exceto_Mi"] = df["Total_Exceto_R$"] / 1_000_000
    
    # 3. Identificar se o estado tem SAP separada ou SSP integrada
    # Um estado tem SAP separada se em algum ano o valor de SAP_Exceto for maior que zero
    # Vamos agrupar por UF e verificar se o máximo de SAP_Exceto_R$ é maior que zero
    def determinar_estrutura(row):
        if row["SAP_Exceto_R$"] > 0:
            return "SAP Separada"
        else:
            return "SSP Integrada (Tudo na SSP)"
            
    df["Estrutura"] = df.apply(determinar_estrutura, axis=1)
    
    # Selecionar e ordenar as colunas para a visão "Lado a Lado"
    colunas_lado_a_lado = [
        "UF", "Ano", "Estrutura",
        "SSP_Exceto_Mi", "SAP_Exceto_Mi", "SSP_SAP_Exceto_Mi", "Total_Exceto_Mi",
        "Pct_SSP_Exceto_%", "Pct_SAP_Exceto_%", "Pct_SSP_SAP_Exceto_%"
    ]
    
    df_lado_a_lado = df[colunas_lado_a_lado].copy()
    
    # Renomear colunas para torná-las mais amigáveis
    df_lado_a_lado.columns = [
        "UF", "Ano", "Modelo de Gestão",
        "SSP (R$ Mi)", "SAP (R$ Mi)", "SSP + SAP (R$ Mi)", "Orçamento Total Estado (R$ Mi)",
        "SSP (%)", "SAP (%)", "SSP + SAP (%)"
    ]
    
    # Ordenar por UF e Ano
    df_lado_a_lado = df_lado_a_lado.sort_values(by=["UF", "Ano"])
    
    # 4. Salvar os CSVs correspondentes
    df_lado_a_lado.to_csv("segpub_lado_a_lado_completo.csv", sep=";", decimal=",", index=False, encoding="utf-8-sig")
    
    # Filtrar apenas 2026 para termos uma visão do ano mais recente
    df_2026 = df_lado_a_lado[df_lado_a_lado["Ano"] == 2026].copy()
    df_2026.to_csv("segpub_lado_a_lado_2026.csv", sep=";", decimal=",", index=False, encoding="utf-8-sig")
    
    print("CSVs 'segpub_lado_a_lado_completo.csv' e 'segpub_lado_a_lado_2026.csv' gerados com sucesso.")
    
    # 5. Adicionar/Atualizar planilhas no arquivo Excel existente
    excel_path = "segpub_estados_2015_2026.xlsx"
    
    # Ler as outras abas para não perdê-las ao reescrever o arquivo
    with pd.ExcelWriter(excel_path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        df_lado_a_lado.to_excel(writer, sheet_name="Lado_a_Lado_Completo", index=False)
        df_2026.to_excel(writer, sheet_name="Lado_a_Lado_2026", index=False)
        
    print(f"Planilhas 'Lado_a_Lado_Completo' e 'Lado_a_Lado_2026' gravadas no Excel '{excel_path}'.")
    
    # 6. Exibir uma prévia de 2026
    print("\n--- PRÉVIA 2026 LADO A LADO ---")
    print(df_2026.to_string(index=False))

if __name__ == "__main__":
    main()
