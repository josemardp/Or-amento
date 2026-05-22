import json

with open("siconfi_anexo4_cache.json", "r", encoding="utf-8") as f:
    cache = json.load(f)

for uf in ["SP", "MG", "RJ", "CE"]:
    print(f"\n=== {uf} 2020 ===")
    key = f"{uf}_2020"
    items = cache.get(key, [])
    seen = {}
    for it in items:
        cod = it.get("cod_conta", "")
        conta = it.get("conta", "")
        col = it.get("coluna", "")
        val = it.get("valor", 0)
        if "militar" in cod.lower() or "militar" in conta.lower() or "milirares" in cod.lower() or "milirares" in conta.lower():
            if val > 0 and "liquidada" in col.lower():
                seen[(cod, conta, col)] = val
    for k, v in seen.items():
        print(f"  Cod: {k[0]} | Conta: {k[1]} | Col: {k[2]} | Val: {v:,.2f}")
