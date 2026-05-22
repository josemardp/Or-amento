import json
import os
import unicodedata

CACHE_FILE = "siconfi_raw_cache.json"

def normalize_str(s):
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = "".join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return s

if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        cache = json.load(f)
    
    # Vamos inspecionar as contas de São Paulo em 2023
    sp_2023 = cache.get("SP_2023", [])
    print(f"Total de itens em SP 2023: {len(sp_2023)}")
    
    # Procurar contas que mencionem palavras-chave do sistema prisional
    keywords = ["custodia", "reintegracao", "penitenciaria", "prisional", "sap", "justica"]
    matching_accounts = set()
    for it in sp_2023:
        conta = it.get("conta", "")
        norm_conta = normalize_str(conta)
        if any(kw in norm_conta for kw in keywords):
            matching_accounts.add(conta)
            
    print("\nContas correspondentes encontradas:")
    for acc in sorted(matching_accounts):
        print(f"- {acc}")
        
    # Mostrar alguns exemplos de valores liquidados destas contas em SP 2023
    print("\nExemplos de valores para estas contas em SP 2023:")
    for it in sp_2023:
        conta = it.get("conta", "")
        coluna = it.get("coluna", "")
        val = it.get("valor", 0)
        rot = it.get("rotulo", "")
        cod = it.get("cod_conta", "")
        if conta in matching_accounts and "despesas liquidadas" in normalize_str(coluna) and "ate o bimestre" in normalize_str(coluna):
            print(f"rotulo: {rot} | conta: {conta} | cod_conta: {cod} | valor: {val:,.2f}")
else:
    print("Cache não encontrado.")
