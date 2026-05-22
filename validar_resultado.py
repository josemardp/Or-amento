import json
import re

def test_validation():
    # 1. Load dados.js
    with open("dados.js", "r", encoding="utf-8") as f:
        content = f.read()
        
    # Extract the JSON array
    json_str_match = re.search(r'const ORCAMENTOS_DATA\s*=\s*(\[.*?\]);', content, re.DOTALL)
    if not json_str_match:
        raise ValueError("Não foi possível encontrar a variável ORCAMENTOS_DATA em dados.js")
        
    data = json.loads(json_str_match.group(1))
    print(f"Carregados {len(data)} registros de dados.js para validação.\n")
    
    # 2. Define calculateRowValues logic in Python
    def calc_values(row, mode):
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
                
        comb_val = ssp_val + sap_val
        ssp_pct = (ssp_val / total_est) * 100 if total_est > 0 else 0.0
        sap_pct = (sap_val / total_est) * 100 if total_est > 0 else 0.0
        comb_pct = (comb_val / total_est) * 100 if total_est > 0 else 0.0
        
        return {
            "ssp_val": ssp_val,
            "sap_val": sap_val,
            "comb_val": comb_val,
            "ssp_pct": ssp_pct,
            "sap_pct": sap_pct,
            "comb_pct": comb_pct
        }

    errors = 0
    
    # 3. Test targets
    # RJ 2023:
    rj_2023 = next((r for r in data if r["UF"] == "RJ" and r["Ano"] == 2023), None)
    if rj_2023:
        print("=== TESTANDO RJ 2023 ===")
        print(f"Modelo Previdenciário: {rj_2023['Modelo_Previdenciario']}")
        print(f"SSP Bruto: {rj_2023['SSP (R$ Mi)']:.2f} Mi")
        print(f"SAP Bruto: {rj_2023['SAP (R$ Mi)']:.2f} Mi")
        print(f"Inativos Militares: {rj_2023['Inativos_Militares (R$ Mi)']:.2f} Mi")
        
        # Oficial Mode
        oficial = calc_values(rj_2023, "oficial")
        print(f"Oficial SSP: {oficial['ssp_val']:.2f} Mi ({oficial['ssp_pct']:.2f}%)")
        
        # Ativos Mode (Should match Oficial)
        ativos = calc_values(rj_2023, "ativos")
        print(f"Ativos SSP: {ativos['ssp_val']:.2f} Mi ({ativos['ssp_pct']:.2f}%)")
        if abs(ativos['ssp_val'] - rj_2023['SSP (R$ Mi)']) > 0.01:
            print("ERROR: RJ 2023 Ativos SSP should be equal to Raw SSP (since RPPS is Separate)")
            errors += 1
            
        # Total Mode (Should increase by Inativos)
        total = calc_values(rj_2023, "total")
        print(f"Total SSP: {total['ssp_val']:.2f} Mi ({total['ssp_pct']:.2f}%)")
        expected_total_ssp = rj_2023['SSP (R$ Mi)'] + rj_2023['Inativos_Militares (R$ Mi)']
        if abs(total['ssp_val'] - expected_total_ssp) > 0.01:
            print(f"ERROR: RJ 2023 Total SSP should be {expected_total_ssp:.2f} but got {total['ssp_val']:.2f}")
            errors += 1
        print("RJ 2023 OK!\n")
    else:
        print("ERROR: RJ 2023 não encontrado")
        errors += 1

    # MG 2023:
    mg_2023 = next((r for r in data if r["UF"] == "MG" and r["Ano"] == 2023), None)
    if mg_2023:
        print("=== TESTANDO MG 2023 ===")
        print(f"Modelo Previdenciário: {mg_2023['Modelo_Previdenciario']}")
        print(f"SSP Bruto: {mg_2023['SSP (R$ Mi)']:.2f} Mi")
        print(f"Inativos Militares: {mg_2023['Inativos_Militares (R$ Mi)']:.2f} Mi")
        
        # Oficial Mode
        oficial = calc_values(mg_2023, "oficial")
        print(f"Oficial SSP: {oficial['ssp_val']:.2f} Mi ({oficial['ssp_pct']:.2f}%)")
        
        # Ativos Mode (Should decrease by Inativos)
        ativos = calc_values(mg_2023, "ativos")
        print(f"Ativos SSP: {ativos['ssp_val']:.2f} Mi ({ativos['ssp_pct']:.2f}%)")
        expected_ativos_ssp = mg_2023['SSP (R$ Mi)'] - mg_2023['Inativos_Militares (R$ Mi)']
        if abs(ativos['ssp_val'] - expected_ativos_ssp) > 0.01:
            print(f"ERROR: MG 2023 Ativos SSP should be {expected_ativos_ssp:.2f} but got {ativos['ssp_val']:.2f}")
            errors += 1
            
        # Total Mode (Should match Oficial)
        total = calc_values(mg_2023, "total")
        print(f"Total SSP: {total['ssp_val']:.2f} Mi ({total['ssp_pct']:.2f}%)")
        if abs(total['ssp_val'] - mg_2023['SSP (R$ Mi)']) > 0.01:
            print("ERROR: MG 2023 Total SSP should be equal to Raw SSP (since RPPS is Integrated)")
            errors += 1
        print("MG 2023 OK!\n")
    else:
        print("ERROR: MG 2023 não encontrado")
        errors += 1

    # 4. Consistency checks for all states and years
    print("=== VERIFICANDO CONSISTÊNCIA GERAL ===")
    for row in data:
        uf = row["UF"]
        ano = row["Ano"]
        total_est = row["Orçamento Total Estado (R$ Mi)"]
        
        # Check raw positive
        if total_est <= 0:
            print(f"ERROR: {uf} {ano} Orçamento Total Estado é {total_est}")
            errors += 1
            
        for mode in ["oficial", "ativos", "total"]:
            res = calc_values(row, mode)
            
            # Check negative values
            if res["ssp_val"] < 0 or res["sap_val"] < 0 or res["comb_val"] < 0:
                print(f"ERROR: {uf} {ano} modo {mode} tem valores negativos: {res}")
                errors += 1
                
            # Check percentages
            if res["ssp_pct"] > 100 or res["sap_pct"] > 100 or res["comb_pct"] > 100:
                print(f"ERROR: {uf} {ano} modo {mode} tem percentuais > 100%: {res}")
                errors += 1
                
            if res["ssp_pct"] < 0 or res["sap_pct"] < 0 or res["comb_pct"] < 0:
                print(f"ERROR: {uf} {ano} modo {mode} tem percentuais negativos: {res}")
                errors += 1
                
    if errors == 0:
        print("Sucesso! Todos os testes de validação matemática passaram sem erros.")
    else:
        print(f"Houve {errors} erro(s) de validação matemática.")

if __name__ == "__main__":
    test_validation()
