import json

with open("siconfi_anexo4_cache.json", "r", encoding="utf-8") as f:
    cache = json.load(f)

print(f"Total keys in cache: {len(cache)}")

distinct_codes = {}
for key, items in cache.items():
    if not items:
        continue
    uf = key.split("_")[0]
    for it in items:
        cod = it.get("cod_conta", "")
        conta = it.get("conta", "")
        coluna = it.get("coluna", "")
        valor = it.get("valor", 0)
        
        # We are looking for military pensions
        cod_lower = str(cod).lower()
        conta_lower = str(conta).lower()
        if "militar" in cod_lower or "militar" in conta_lower:
            if cod not in distinct_codes:
                distinct_codes[cod] = {
                    "conta": conta,
                    "ufs": set(),
                    "colunas": set()
                }
            distinct_codes[cod]["ufs"].add(uf)
            if valor > 0:
                distinct_codes[cod]["colunas"].add(coluna)

print("\nContas contendo 'militar':")
for cod, info in distinct_codes.items():
    print(f"Cod: {cod}")
    print(f"  Conta: {info['conta']}")
    print(f"  UFs: {sorted(list(info['ufs']))}")
    print(f"  Colunas com valor > 0: {sorted(list(info['colunas']))}")
