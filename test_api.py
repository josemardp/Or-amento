import requests

BASE_URL = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo"

params = {
    "an_exercicio": 2015,
    "in_periodicidade": "A",
    "nr_periodo": 6,
    "co_tipo_demonstrativo": "RREO",
    "no_anexo": "RREO-Anexo 02",
    "co_esfera": "E",
    "id_ente": 35, # SP
}
try:
    r = requests.get(BASE_URL, params=params, timeout=30)
    r.raise_for_status()
    items = r.json().get("items", [])
    
    seg_items = [it for it in items if "seguran" in str(it.get("conta", "")).lower()]
    print("=== SP 2015 SEGURANÇA ITEMS ===")
    for it in seg_items:
        print(f"rotulo: {it.get('rotulo')} | conta: {it.get('conta')} | coluna: {it.get('coluna')} | valor: {it.get('valor')}")
        
except Exception as e:
    print(f"Erro: {e}")
