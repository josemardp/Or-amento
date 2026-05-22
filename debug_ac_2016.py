import requests
import json
import unicodedata

BASE_URL = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo"

params = {
    "an_exercicio": 2016,
    "in_periodicidade": "A",
    "nr_periodo": 6,
    "co_tipo_demonstrativo": "RREO",
    "no_anexo": "RREO-Anexo 02",
    "co_esfera": "E",
    "id_ente": 12, # AC
}

def normalize_str(s):
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s

try:
    r = requests.get(BASE_URL, params=params, timeout=30)
    r.raise_for_status()
    items = r.json().get("items", [])
    
    total_keys = ["despesas (exceto intra", "despesas (intra-orcamentarias) (ii)", "total (iii)"]
    for k in total_keys:
        matching = [it for it in items if k in normalize_str(it.get("conta")) and "despesas liquidadas ate o bimestre" in normalize_str(it.get("coluna"))]
        print(f"\n=== Resultados para '{k}': ===")
        for it in matching:
            print(json.dumps(it, indent=2, ensure_ascii=False))
            
except Exception as e:
    print(f"Erro: {e}")
