import json

with open("siconfi_anexo4_cache.json", "r", encoding="utf-8") as f:
    cache = json.load(f)

for ano in [2020, 2021, 2022, 2023, 2024]:
    print(f"\n=== DF {ano} ===")
    items = cache.get(f"DF_{ano}", [])
    seen = {}
    for it in items:
        cod = it.get("cod_conta", "")
        conta = it.get("conta", "")
        col = it.get("coluna", "")
        val = it.get("valor", 0)
        if any(term in str(cod).lower() or term in str(conta).lower() for term in ["militar", "milirares", "policia", "bombeiro"]):
            if val > 0:
                seen[(cod, conta, col)] = val
    for k, v in sorted(seen.items()):
        print(f"  Cod: {k[0]} | Conta: {k[1]} | Col: {k[2]} | Val: {v:,.2f}")
