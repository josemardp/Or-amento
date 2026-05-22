import requests
import json
import os
import time
import unicodedata
import pandas as pd

# IBGE codes for all 27 Brazilian states (UF -> code IBGE)
ESTADOS = {
    "AC": 12, "AL": 27, "AM": 13, "AP": 16, "BA": 29,
    "CE": 23, "DF": 53, "ES": 32, "GO": 52, "MA": 21,
    "MG": 31, "MS": 50, "MT": 51, "PA": 15, "PB": 25,
    "PE": 26, "PI": 22, "PR": 41, "RJ": 33, "RN": 24,
    "RO": 11, "RR": 14, "RS": 43, "SC": 42, "SE": 28,
    "SP": 35, "TO": 17,
}

ANOS = list(range(2015, 2025))
BASE_URL = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo"
CACHE_FILE = "siconfi_raw_cache.json"

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar cache: {e}")
            return {}
    return {}

def save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erro ao salvar cache: {e}")

def normalize_str(s):
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s

def buscar_despesas_por_funcao(co_ibge: int, ano: int) -> list:
    """
    Busca o Anexo 02 do RREO de um estado/ano.
    Inclui lógica de retry com exponencial backoff.
    """
    params = {
        "an_exercicio": ano,
        "in_periodicidade": "A",   # Anual (6º bimestre)
        "nr_periodo": 6,
        "co_tipo_demonstrativo": "RREO",
        "no_anexo": "RREO-Anexo 02",
        "co_esfera": "E",          # Estadual
        "id_ente": co_ibge,
    }
    
    retries = 3
    delay = 1.0
    for attempt in range(retries):
        try:
            r = requests.get(BASE_URL, params=params, timeout=45)
            if r.status_code == 404:
                print(f"  [404] Não encontrado para IBGE {co_ibge} ano {ano}")
                return []
            r.raise_for_status()
            data = r.json()
            items = data.get("items", [])
            return items
        except Exception as e:
            print(f"  Erro na tentativa {attempt+1} para {co_ibge} {ano}: {e}")
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
            else:
                print(f"  Falha definitiva para {co_ibge} {ano}")
                return []
    return []

def is_liquidada_col(col):
    col = normalize_str(col)
    return ("despesas liquidadas" in col and "ate o bimestre" in col) or "ate o bimestre (d)" in col

def extrair_dados_do_anexo(items: list) -> dict:
    """
    Varre os itens do Anexo 02 e extrai:
    - seg_pub_exceto_liq (Segurança Pública líquida exceto intra-orçamentária)
    - seg_pub_intra_liq (Segurança Pública líquida intra-orçamentária)
    - seg_pub_pct_api (% d/total d para Segurança Pública exceto intra-orçamentária)
    - custodia_exceto_liq (Custódia e Reintegração Social líquida exceto intra-orçamentária)
    - custodia_intra_liq (Custódia e Reintegração Social líquida intra-orçamentária)
    - total_exceto_liq (Total de despesas exceto intra-orçamentárias - I)
    - total_intra_liq (Total de despesas intra-orçamentárias - II)
    - total_geral_liq (Total geral - III)
    """
    res = {
        "seg_pub_exceto_liq": 0.0,
        "seg_pub_intra_liq": 0.0,
        "seg_pub_pct_api": None,
        "custodia_exceto_liq": 0.0,
        "custodia_intra_liq": 0.0,
        "total_exceto_liq": 0.0,
        "total_intra_liq": 0.0,
        "total_geral_liq": 0.0,
    }
    
    for item in items:
        conta = normalize_str(item.get("conta"))
        coluna = normalize_str(item.get("coluna"))
        cod_conta = str(item.get("cod_conta", "")).strip()
        
        try:
            valor = float(str(item.get("valor", 0)).replace(",", "."))
        except (ValueError, TypeError):
            valor = 0.0
            
        # 1. Identificar Segurança Pública
        if conta == "seguranca publica":
            # Verificar se é intra ou exceto
            if cod_conta == "RREO2TotalDespesasIntra":
                if is_liquidada_col(coluna):
                    res["seg_pub_intra_liq"] = valor
            elif cod_conta == "RREO2TotalDespesas" or cod_conta == "":
                if is_liquidada_col(coluna):
                    res["seg_pub_exceto_liq"] = valor
                elif "% (d/total d)" in coluna:
                    res["seg_pub_pct_api"] = valor
                    
        # 2. Identificar Custódia e Reintegração Social (SAP)
        if conta == "custodia e reintegracao social":
            if cod_conta == "RREO2TotalDespesasIntra":
                if is_liquidada_col(coluna):
                    res["custodia_intra_liq"] = valor
            elif cod_conta == "RREO2TotalDespesas" or cod_conta == "":
                if is_liquidada_col(coluna):
                    res["custodia_exceto_liq"] = valor
                    
        # 3. Identificar Totais
        # Total das Despesas Exceto Intra-Orçamentárias (I)
        if conta == "despesas (exceto intra-orcamentarias) (i)" or (
            "exceto" in conta and "intra" in conta and ("despesas" in conta or "total" in conta)
        ):
            if is_liquidada_col(coluna):
                res["total_exceto_liq"] = valor
                
        # Total das Despesas Intra-Orçamentárias (II)
        if conta == "despesas (intra-orcamentarias) (ii)" or (
            "intra" in conta and "exceto" not in conta and ("despesas" in conta or "total" in conta)
        ):
            if is_liquidada_col(coluna):
                res["total_intra_liq"] = max(res["total_intra_liq"], valor)
                
        # TOTAL (III) = (I + II)
        if conta == "total (iii) = (i + ii)" or conta == "total (iii) = (i+ii)" or (
            "total (iii)" in conta or "total geral" in conta
        ):
            if is_liquidada_col(coluna):
                res["total_geral_liq"] = max(res["total_geral_liq"], valor)

    # Lógicas de fallback caso os totais não tenham sido preenchidos diretamente
    if res["total_geral_liq"] == 0.0 and res["total_exceto_liq"] > 0.0:
        res["total_geral_liq"] = res["total_exceto_liq"] + res["total_intra_liq"]
        
    return res

def main():
    cache = load_cache()
    resultados = []
    
    print("Iniciando coleta e consolidação de dados SICONFI (SSP + SAP)...")
    
    total_requisicoes = len(ESTADOS) * len(ANOS)
    contador = 0
    
    for uf, ibge in ESTADOS.items():
        print(f"\n=== {uf} (IBGE: {ibge}) ===")
        for ano in ANOS:
            contador += 1
            cache_key = f"{uf}_{ano}"
            
            print(f"  [{contador}/{total_requisicoes}] {ano}...", end=" ", flush=True)
            
            # Verificar se já está no cache
            if cache_key in cache:
                print("cache hit", end=" ", flush=True)
                items = cache[cache_key]
            else:
                print("buscando...", end=" ", flush=True)
                items = buscar_despesas_por_funcao(ibge, ano)
                cache[cache_key] = items
                save_cache(cache)
                time.sleep(0.4) # respeita rate limit
                
            if not items:
                print("SEM DADOS")
                resultados.append({
                    "UF": uf, "Ano": ano, "Status": "SEM_DADOS",
                    "SSP_Exceto_R$": None, "SSP_Intra_R$": None, "SSP_Total_R$": None,
                    "SAP_Exceto_R$": None, "SAP_Intra_R$": None, "SAP_Total_R$": None,
                    "SSP_SAP_Exceto_R$": None, "SSP_SAP_Intra_R$": None, "SSP_SAP_Total_R$": None,
                    "Total_Exceto_R$": None, "Total_Intra_R$": None, "Total_Geral_R$": None,
                    "Pct_SSP_Exceto_%": None, "Pct_SSP_Total_%": None,
                    "Pct_SAP_Exceto_%": None, "Pct_SAP_Total_%": None,
                    "Pct_SSP_SAP_Exceto_%": None, "Pct_SSP_SAP_Total_%": None,
                    "Pct_API_%": None
                })
                continue
                
            dados = extrair_dados_do_anexo(items)
            
            ssp_exceto = dados["seg_pub_exceto_liq"]
            ssp_intra = dados["seg_pub_intra_liq"]
            ssp_total = ssp_exceto + ssp_intra
            
            sap_exceto = dados["custodia_exceto_liq"]
            sap_intra = dados["custodia_intra_liq"]
            sap_total = sap_exceto + sap_intra
            
            comb_exceto = ssp_exceto + sap_exceto
            comb_intra = ssp_intra + sap_intra
            comb_total = ssp_total + sap_total
            
            tot_exceto = dados["total_exceto_liq"]
            tot_intra = dados["total_intra_liq"]
            tot_geral = dados["total_geral_liq"]
            
            pct_ssp_exceto = None
            pct_ssp_total = None
            pct_sap_exceto = None
            pct_sap_total = None
            pct_comb_exceto = None
            pct_comb_total = None
            
            if tot_exceto > 0:
                pct_ssp_exceto = round((ssp_exceto / tot_exceto) * 100, 2)
                pct_sap_exceto = round((sap_exceto / tot_exceto) * 100, 2)
                pct_comb_exceto = round((comb_exceto / tot_exceto) * 100, 2)
            if tot_geral > 0:
                pct_ssp_total = round((ssp_total / tot_geral) * 100, 2)
                pct_sap_total = round((sap_total / tot_geral) * 100, 2)
                pct_comb_total = round((comb_total / tot_geral) * 100, 2)
                
            pct_api = dados["seg_pub_pct_api"]
            
            print(f"OK (SSP: {pct_ssp_exceto}%, SAP: {pct_sap_exceto}%, Comb: {pct_comb_exceto}%)")
            
            resultados.append({
                "UF": uf,
                "Ano": ano,
                "Status": "OK",
                "SSP_Exceto_R$": ssp_exceto,
                "SSP_Intra_R$": ssp_intra,
                "SSP_Total_R$": ssp_total,
                "SAP_Exceto_R$": sap_exceto,
                "SAP_Intra_R$": sap_intra,
                "SAP_Total_R$": sap_total,
                "SSP_SAP_Exceto_R$": comb_exceto,
                "SSP_SAP_Intra_R$": comb_intra,
                "SSP_SAP_Total_R$": comb_total,
                "Total_Exceto_R$": tot_exceto,
                "Total_Intra_R$": tot_intra,
                "Total_Geral_R$": tot_geral,
                "Pct_SSP_Exceto_%": pct_ssp_exceto,
                "Pct_SSP_Total_%": pct_ssp_total,
                "Pct_SAP_Exceto_%": pct_sap_exceto,
                "Pct_SAP_Total_%": pct_sap_total,
                "Pct_SSP_SAP_Exceto_%": pct_comb_exceto,
                "Pct_SSP_SAP_Total_%": pct_comb_total,
                "Pct_API_%": pct_api
            })

    # Criar DataFrame principal
    df = pd.DataFrame(resultados)
    
    # Salvar CSV Completo
    df.to_csv("segpub_completo.csv", index=False, sep=";", decimal=",", encoding="utf-8-sig")
    print("\nCSV Completo salvo em 'segpub_completo.csv'")
    
    # Filtrar apenas registros com status OK
    df_ok = df[df["Status"] == "OK"].copy()
    
    if not df_ok.empty:
        # Pivots dos percentuais
        pivot_ssp_exceto = df_ok.pivot(index="UF", columns="Ano", values="Pct_SSP_Exceto_%")
        pivot_sap_exceto = df_ok.pivot(index="UF", columns="Ano", values="Pct_SAP_Exceto_%")
        pivot_comb_exceto = df_ok.pivot(index="UF", columns="Ano", values="Pct_SSP_SAP_Exceto_%")
        
        pivot_ssp_total = df_ok.pivot(index="UF", columns="Ano", values="Pct_SSP_Total_%")
        pivot_comb_total = df_ok.pivot(index="UF", columns="Ano", values="Pct_SSP_SAP_Total_%")
        
        pivot_api = df_ok.pivot(index="UF", columns="Ano", values="Pct_API_%")
        
        # Salvar Pivots em CSV
        pivot_ssp_exceto.to_csv("segpub_pivot_ssp_exceto.csv", sep=";", decimal=",", encoding="utf-8-sig")
        pivot_sap_exceto.to_csv("segpub_pivot_sap_exceto.csv", sep=";", decimal=",", encoding="utf-8-sig")
        pivot_comb_exceto.to_csv("segpub_pivot_comb_exceto.csv", sep=";", decimal=",", encoding="utf-8-sig")
        pivot_ssp_total.to_csv("segpub_pivot_ssp_total.csv", sep=";", decimal=",", encoding="utf-8-sig")
        pivot_comb_total.to_csv("segpub_pivot_comb_total.csv", sep=";", decimal=",", encoding="utf-8-sig")
        print("CSVs de Pivots salvos.")
        
        # Salvar tudo em um único Excel formatado
        excel_path = "segpub_estados_2015_2024.xlsx"
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Dados Completos", index=False)
            pivot_ssp_exceto.to_excel(writer, sheet_name="Pct_SSP_Exceto")
            pivot_sap_exceto.to_excel(writer, sheet_name="Pct_SAP_Exceto")
            pivot_comb_exceto.to_excel(writer, sheet_name="Pct_SSP_SAP_Exceto")
            pivot_ssp_total.to_excel(writer, sheet_name="Pct_SSP_Total")
            pivot_comb_total.to_excel(writer, sheet_name="Pct_SSP_SAP_Total")
            pivot_api.to_excel(writer, sheet_name="Pct_API_RREO")
        print(f"Planilha Excel consolidada salva em '{excel_path}'")
        
        print("\n--- PRÉVIA PERCENTUAL COMBINADO SSP+SAP (EXCETO INTRA) ---")
        print(pivot_comb_exceto.to_string())
    else:
        print("\nErro: Nenhum dado pôde ser processado com sucesso.")

if __name__ == "__main__":
    main()
