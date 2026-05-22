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
        
    mg_2023 = cache.get("MG_2023", [])
    print(f"Total de itens em MG 2023: {len(mg_2023)}")
    
    # Listar todas as contas e seus valores liquidados (exceto intra-orçamentárias)
    # que tenham valor > 0, ordenados pelo valor decrescente
    accounts_val = {}
    for it in mg_2023:
        conta = it.get("conta", "")
        coluna = it.get("coluna", "")
        cod_conta = str(it.get("cod_conta", "")).strip()
        
        try:
            valor = float(str(it.get("valor", 0)).replace(",", "."))
        except (ValueError, TypeError):
            valor = 0.0
            
        if cod_conta == "RREO2TotalDespesas" and "despesas liquidadas" in normalize_str(coluna) and "ate o bimestre" in normalize_str(coluna):
            if valor > 0:
                accounts_val[conta] = valor
                
    print("\nContas com despesas liquidadas > 0 em MG 2023:")
    sorted_accounts = sorted(accounts_val.items(), key=lambda x: x[1], reverse=True)
    for acc, val in sorted_accounts:
        print(f"- {acc}: R$ {val:,.2f}")
else:
    print("Cache não encontrado.")
