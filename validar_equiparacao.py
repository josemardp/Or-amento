# -*- coding: utf-8 -*-
"""
Script de validação matemática da equiparação orçamentária (Denominador Comum).
Este script carrega a base de dados em dados.js e valida as somas do modo Equiparado para SP e MG (exercício de 2023).
"""

import json
import os
import sys

def calculate_row_values(row, mode):
    ssp_raw = row["SSP (R$ Mi)"]
    sap_raw = row["SAP (R$ Mi)"]
    total_est = row["Orçamento Total Estado (R$ Mi)"]
    inativos = row.get("Inativos_Militares (R$ Mi)", 0.0)
    modelo_prev = row["Modelo_Previdenciario"]
    
    ssp_val = ssp_raw
    sap_val = sap_raw
    
    if mode == "ativos":
        if modelo_prev == "Integrado":
            ssp_val = max(0.0, ssp_raw - inativos)
    elif mode == "total":
        if modelo_prev == "Separado":
            ssp_val = ssp_raw + inativos
    elif mode == "equiparado":
        if modelo_prev == "Separado":
            ssp_val = ssp_raw + inativos
        detran = row.get("DETRAN_Proxy (R$ Mi)", 0.0)
        casa_mil = row.get("Casa_Militar_Ajuste (R$ Mi)", 0.0)
        ssp_val = ssp_val + detran + casa_mil
        
    comb_val = ssp_val + sap_val
    ssp_pct = (ssp_val / total_est) * 100.0 if total_est > 0 else 0.0
    sap_pct = (sap_val / total_est) * 100.0 if total_est > 0 else 0.0
    comb_pct = (comb_val / total_est) * 100.0 if total_est > 0 else 0.0
    
    return {
        "ssp_val": ssp_val,
        "sap_val": sap_val,
        "comb_val": comb_val,
        "ssp_pct": ssp_pct,
        "sap_pct": sap_pct,
        "comb_pct": comb_pct
    }

def main():
    print("Iniciando testes de validação do modo Equiparado...")
    
    # 1. Carregar dados.js
    dados_path = "dados.js"
    if not os.path.exists(dados_path):
        print(f"Erro: arquivo {dados_path} não encontrado.")
        sys.exit(1)
        
    with open(dados_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    import re
    json_str_match = re.search(r'const ORCAMENTOS_DATA\s*=\s*(\[.*?\]);', content, re.DOTALL)
    if not json_str_match:
        print("Erro: não foi possível encontrar a array de dados em dados.js")
        sys.exit(1)
        
    try:
        data = json.loads(json_str_match.group(1))
    except Exception as e:
        print(f"Erro ao parsear o JSON de dados: {e}")
        sys.exit(1)
        
    # 2. Localizar registros de 2023 de SP e MG
    sp_2023 = next((x for x in data if x["UF"] == "SP" and x["Ano"] == 2023), None)
    mg_2023 = next((x for x in data if x["UF"] == "MG" and x["Ano"] == 2023), None)
    
    if not sp_2023 or not mg_2023:
        print("Erro: registros de 2023 para SP e/ou MG não encontrados nos dados.")
        sys.exit(1)
        
    # 3. Validar SP 2023 Equiparado
    # Formula Esperada:
    # ssp_raw (15168.50) + inativos (13475.25) + detran (927.05) + casa_militar (120.00) = 29690.80
    # sap_raw (4049.76)
    # comb_val = 33740.56
    vals_sp = calculate_row_values(sp_2023, "equiparado")
    
    expected_sp_ssp = 15168.4988865 + 13475.25 + 927.05 + 120.0
    expected_sp_sap = 4049.76050651
    expected_sp_comb = expected_sp_ssp + expected_sp_sap
    
    print(f"\nSP 2023 (Equiparado):")
    print(f"  SSP Calculado: R$ {vals_sp['ssp_val']:.2f} Mi | Esperado: R$ {expected_sp_ssp:.2f} Mi")
    print(f"  SAP Calculado: R$ {vals_sp['sap_val']:.2f} Mi | Esperado: R$ {expected_sp_sap:.2f} Mi")
    print(f"  Combinado Calculado: R$ {vals_sp['comb_val']:.2f} Mi | Esperado: R$ {expected_sp_comb:.2f} Mi")
    
    assert abs(vals_sp["ssp_val"] - expected_sp_ssp) < 1e-4, "Erro: SSP de SP inválido no modo equiparado!"
    assert abs(vals_sp["sap_val"] - expected_sp_sap) < 1e-4, "Erro: SAP de SP inválido no modo equiparado!"
    assert abs(vals_sp["comb_val"] - expected_sp_comb) < 1e-4, "Erro: Combinado de SP inválido no modo equiparado!"
    print("  => SP 2023 validado com sucesso!")
    
    # 4. Validar MG 2023 Equiparado
    # Formula Esperada:
    # ssp_raw (18922.94) + inativos (0, pois é Integrado) + detran (0, pois é Integrado) + casa_militar (0) = 18922.94
    # sap_raw (0.0)
    # comb_val = 18922.94
    vals_mg = calculate_row_values(mg_2023, "equiparado")
    
    expected_mg_ssp = 18922.94003875
    expected_mg_sap = 0.0
    expected_mg_comb = expected_mg_ssp
    
    print(f"\nMG 2023 (Equiparado):")
    print(f"  SSP Calculado: R$ {vals_mg['ssp_val']:.2f} Mi | Esperado: R$ {expected_mg_ssp:.2f} Mi")
    print(f"  SAP Calculado: R$ {vals_mg['sap_val']:.2f} Mi | Esperado: R$ {expected_mg_sap:.2f} Mi")
    print(f"  Combinado Calculado: R$ {vals_mg['comb_val']:.2f} Mi | Esperado: R$ {expected_mg_comb:.2f} Mi")
    
    assert abs(vals_mg["ssp_val"] - expected_mg_ssp) < 1e-4, "Erro: SSP de MG inválido no modo equiparado!"
    assert abs(vals_mg["sap_val"] - expected_mg_sap) < 1e-4, "Erro: SAP de MG inválido no modo equiparado!"
    assert abs(vals_mg["comb_val"] - expected_mg_comb) < 1e-4, "Erro: Combinado de MG inválido no modo equiparado!"
    print("  => MG 2023 validado com sucesso!")
    
    # 5. Validar que para todos os estados de 2020 a 2024, o modo equiparado não gera valores nulos ou negativos
    for record in data:
        if record["Ano"] >= 2020:
            res = calculate_row_values(record, "equiparado")
            if res["ssp_val"] < 0 or res["sap_val"] < 0 or res["comb_val"] < 0:
                print(f"Erro: Valor negativo detectado para {record['UF']} em {record['Ano']}: {res}")
                sys.exit(1)
                
    print("\nTodos os testes de sanidade e validação foram aprovados com sucesso!")

if __name__ == "__main__":
    main()
