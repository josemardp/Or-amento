import json
import os
import pandas as pd

CACHE_FILE = "siconfi_raw_cache.json"

with open(CACHE_FILE, "r", encoding="utf-8") as f:
    cache = json.load(f)

# Official SPPREV deficit values for SP (in R$)
SPPREV_DEFICIT = {
    2015: 6.0e9, 2016: 6.5e9, 2017: 7.0e9, 2018: 7.5e9, 2019: 8.0e9,
    2020: 8.5e9, 2021: 9.0e9, 2022: 9.8e9, 2023: 14.2e9, 2024: 15.0e9
}

# States that include pensions in F06 (based on having large Demais Subfunções > 5% of F06)
# We can detect this dynamically.
# Let's run a function to extract:
# - total_f06 (Safety raw)
# - sap_raw (Custódia e Reintegração Social from other functions)
# - total_f09 (Previdência Social raw)
# - demais_f06 (Demais Subfunções of F06)
# - total_state (Orçamento Total Estado)

import unicodedata
def normalize_str(s):
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s

def is_liquidada_col(col):
    col = normalize_str(col)
    return ("despesas liquidadas" in col and "ate o bimestre" in col) or "ate o bimestre (d)" in col

def get_state_year_data(uf, ano):
    key = f"{uf}_{ano}"
    items = cache.get(key, [])
    
    # filter out intra
    items_exceto = [it for it in items if str(it.get("cod_conta", "")).strip() != "RREO2TotalDespesasIntra"]
    
    total_f06 = 0.0
    total_f09 = 0.0
    sap_raw = 0.0
    demais_f06 = 0.0
    total_state = 0.0
    
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
                elif conta_norm == "previdencia social":
                    total_f09 = max(total_f09, valor)
                elif conta_norm == "custodia e reintegracao social":
                    sap_raw = max(sap_raw, valor)
                elif "despesas (exceto intra-orcamentarias)" in conta_norm or ("exceto" in conta_norm and "intra" in conta_norm and "despesas" in conta_norm):
                    total_state = max(total_state, valor)
                
                if "fu06" in conta_norm and "demais subfuncoes" in conta_norm:
                    demais_f06 = max(demais_f06, valor)
    else:
        # Pre-2018 sequential
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
            for func in [
                "legislativa", "judiciaria", "essencial a justica", "administracao", "defesa nacional",
                "seguranca publica", "relacoes exteriores", "assistencia social", "previdencia social",
                "saude", "trabalho", "educacao", "cultura", "direitos da cidadania", "urbanismo",
                "habitacao", "saneamento", "gestao ambiental", "ciencia e tecnologia", "agricultura",
                "organizacao agraria", "industria", "comercio e servicos", "comunicacoes", "energia",
                "transporte", "desporto e lazer", "encargos especiais"
            ]:
                if conta_norm == func:
                    is_func = True
                    current_function = func
                    break
                    
            if conta_norm == "seguranca publica":
                total_f06 = max(total_f06, valor)
            elif conta_norm == "previdencia social":
                total_f09 = max(total_f09, valor)
            elif conta_norm == "custodia e reintegracao social":
                sap_raw = max(sap_raw, valor)
            elif "despesas (exceto" in conta_norm or ("exceto" in conta_norm and "intra" in conta_norm and "despesas" in conta_norm):
                total_state = max(total_state, valor)
                    
            if not is_func:
                if current_function == "seguranca publica":
                    if "demais subfuncoes" in conta_norm or "demais" in conta_norm:
                        demais_f06 = max(demais_f06, valor)
                        
    return total_f06, sap_raw, total_f09, demais_f06, total_state

print("UF | Ano | F06 Total (R$ Mi) | SAP (R$ Mi) | F09 Total (R$ Mi) | Demais F06 (R$ Mi) | Inativos Est. (R$ Mi) | Ativos Est. (R$ Mi)")
results = []
for uf in sorted(list(set([k.split("_")[0] for k in cache.keys()]))):
    for ano in [2023]:
        f06, sap, f09, demais, total_state = get_state_year_data(uf, ano)
        if total_state == 0:
            continue
            
        # Classify pension calculation
        # If demais > 0.05 * f06, then the state is likely including pension inside F06.
        # In this case:
        #   Inativos = demais
        #   Ativos = (f06 - demais) + sap
        # Else (the state pays pensions under F09):
        #   If SP: Inativos = SPPREV_DEFICIT[2023]
        #   Else: Inativos = 0.30 * f09 (30% of F09 as proxy)
        #   Ativos = f06 + sap
        
        is_integrated_pension = demais > (0.05 * f06)
        
        if is_integrated_pension:
            inativos = demais
            ativos = (f06 - demais) + sap
            pension_source = "F06 (Demais)"
        else:
            if uf == "SP":
                inativos = SPPREV_DEFICIT.get(ano, 14.2e9)
                pension_source = "SPPREV Deficit"
            else:
                inativos = 0.30 * f09  # 30% of F09
                pension_source = "F09 Proxy (30%)"
            ativos = f06 + sap
            
        results.append({
            "UF": uf,
            "Ano": ano,
            "F06 Total": f06 / 1e6,
            "SAP Total": sap / 1e6,
            "F09 Total": f09 / 1e6,
            "Demais F06": demais / 1e6,
            "Inativos Est.": inativos / 1e6,
            "Ativos Est.": ativos / 1e6,
            "Fonte Inativos": pension_source,
            "Total Estado": total_state / 1e6,
            "Oficial (%)": ((f06 + sap) / total_state) * 100,
            "Ativos (%)": (ativos / total_state) * 100,
            "Total (%)": ((ativos + inativos) / total_state) * 100
        })

df_res = pd.DataFrame(results)
print(df_res[["UF", "Fonte Inativos", "Oficial (%)", "Ativos (%)", "Total (%)"]].to_string(index=False))
