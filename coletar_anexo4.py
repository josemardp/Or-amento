import requests
import json
import os
import time
import concurrent.futures
from threading import Lock

ESTADOS = {
    "AC": 12, "AL": 27, "AM": 13, "AP": 16, "BA": 29,
    "CE": 23, "DF": 53, "ES": 32, "GO": 52, "MA": 21,
    "MG": 31, "MS": 50, "MT": 51, "PA": 15, "PB": 25,
    "PE": 26, "PI": 22, "PR": 41, "RJ": 33, "RN": 24,
    "RO": 11, "RR": 14, "RS": 43, "SC": 42, "SE": 28,
    "SP": 35, "TO": 17,
}

ANOS = [2025, 2026]
BASE_URL = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo"
CACHE_FILE = "siconfi_anexo4_cache.json"

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

def fetch_uf_ano(uf, ibge, ano):
    key = f"{uf}_{ano}"
    params = {
        "an_exercicio": ano,
        "in_periodicidade": "B" if ano == 2026 else "A",
        "nr_periodo": 2 if ano == 2026 else 6,
        "co_tipo_demonstrativo": "RREO",
        "no_anexo": "RREO-Anexo 04",
        "co_esfera": "E",
        "id_ente": ibge,
    }
    
    retries = 3
    delay = 1.0
    items = []
    for attempt in range(retries):
        try:
            r = requests.get(BASE_URL, params=params, timeout=35)
            if r.status_code == 404:
                print(f"  {key}: [404 Não encontrado]")
                break
            r.raise_for_status()
            data = r.json()
            items = data.get("items", [])
            print(f"  {key}: OK (encontrados {len(items)} registros)")
            break
        except Exception as e:
            print(f"  {key}: [Erro tentativa {attempt+1}: {e}]")
            if attempt < retries - 1:
                time.sleep(delay)
                delay *= 2
            else:
                print(f"  {key}: FALHA")
                
    return key, items

def main():
    cache = load_cache()
    print("Iniciando a extração paralela do RREO Anexo 04 para todas as UFs (2025-2026)...")
    
    tasks = []
    for uf, ibge in ESTADOS.items():
        for ano in ANOS:
            key = f"{uf}_{ano}"
            if key not in cache:
                tasks.append((uf, ibge, ano))
            else:
                print(f"  {key}: cache hit")
                
    if not tasks:
        print("Tudo já está no cache!")
        return
        
    print(f"Baixando {len(tasks)} registros do SICONFI...")
    
    # Executar em paralelo
    cache_lock = Lock()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(fetch_uf_ano, uf, ibge, ano): (uf, ano) for uf, ibge, ano in tasks}
        for future in concurrent.futures.as_completed(futures):
            uf, ano = futures[future]
            try:
                key, items = future.result()
                with cache_lock:
                    cache[key] = items
                    save_cache(cache)
            except Exception as exc:
                print(f"  {uf}_{ano} gerou uma exceção: {exc}")

    print("\nExtração finalizada!")

if __name__ == "__main__":
    main()
