import json
import os

CACHE_FILE = "siconfi_raw_cache.json"

if not os.path.exists(CACHE_FILE):
    print("Cache não encontrado!")
    exit(1)

with open(CACHE_FILE, "r", encoding="utf-8") as f:
    cache = json.load(f)

for ano in [2015, 2018, 2021, 2023]:
    key = f"MG_{ano}"
    items = cache.get(key, [])
    print(f"\n==================== MG {ano} ====================")
    
    seen = set()
    for it in items:
        conta = it.get("conta", "")
        coluna = it.get("coluna", "")
        cod_conta = str(it.get("cod_conta", "")).strip()
        
        try:
            valor = float(str(it.get("valor", 0)).replace(",", "."))
        except (ValueError, TypeError):
            valor = 0.0
            
        if "despesas liquidadas" in coluna.lower() and "ate o bimestre" in coluna.lower() and valor > 0:
            # We want to print accounts containing "seguranca" or related or subfunctions
            # Let's print unique accounts that look like subfunctions or are safety-related
            conta_norm = conta.strip().lower()
            if conta_norm not in seen:
                if any(x in conta_norm for x in ["seguranca", "policiamento", "defesa civil", "inteligencia", "fu06", "demais"]):
                    print(f"Conta: {conta} | Cod: {cod_conta} | Valor: R$ {valor:,.2f}")
                    seen.add(conta_norm)
