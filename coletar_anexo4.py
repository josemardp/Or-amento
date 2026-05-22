import requests
import json
import os
import time

ESTADOS = {
    "AC": 12, "AL": 27, "AM": 13, "AP": 16, "BA": 29,
    "CE": 23, "DF": 53, "ES": 32, "GO": 52, "MA": 21,
    "MG": 31, "MS": 50, "MT": 51, "PA": 15, "PB": 25,
    "PE": 26, "PI": 22, "PR": 41, "RJ": 33, "RN": 24,
    "RO": 11, "RR": 14, "RS": 43, "SC": 42, "SE": 28,
    "SP": 35, "TO": 17,
}

ANOS = [2020, 2021, 2022, 2023, 2024]
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

def main():
    cache = load_cache()
    total = len(ESTADOS) * len(ANOS)
    count = 0
    
    print("Iniciando a extração do RREO Anexo 04 para todas as UFs (2020-2024)...")
    
    for uf, ibge in ESTADOS.items():
        for ano in ANOS:
            count += 1
            key = f"{uf}_{ano}"
            
            if key in cache:
                print(f"[{count}/{total}] {key}: cache hit")
                continue
                
            print(f"[{count}/{total}] {key}: buscando no SICONFI...", end="", flush=True)
            
            params = {
                "an_exercicio": ano,
                "in_periodicidade": "A",
                "nr_periodo": 6,
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
                    r = requests.get(BASE_URL, params=params, timeout=40)
                    if r.status_code == 404:
                        print(" [404 Não encontrado]")
                        break
                    r.raise_for_status()
                    data = r.json()
                    items = data.get("items", [])
                    print(f" OK (encontrados {len(items)} registros)")
                    break
                except Exception as e:
                    print(f" [Erro tentativa {attempt+1}: {e}]", end="", flush=True)
                    if attempt < retries - 1:
                        time.sleep(delay)
                        delay *= 2
                    else:
                        print(" FALHA")
            
            cache[key] = items
            save_cache(cache)
            time.sleep(0.3) # rate limiting

    print("\nExtração finalizada!")

if __name__ == "__main__":
    main()
