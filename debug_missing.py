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
        
    for key in ["BA_2016", "RN_2015"]:
        if key in cache:
            items = cache[key]
            print(f"\n=== INSPEÇÃO {key} ({len(items)} itens) ===")
            
            # Ver contas que parecem total
            total_items = [it for it in items if "despesas (" in normalize_str(it.get("conta")) or "total (" in normalize_str(it.get("conta"))]
            print(f"\nContas de total em {key}:")
            for it in total_items[:10]:
                print(f"rotulo: {it.get('rotulo')} | conta: {it.get('conta')} | cod_conta: {it.get('cod_conta')} | coluna: {it.get('coluna')} | valor: {it.get('valor')}")
                
            # Ver contas de segurança
            seg_items = [it for it in items if "seguran" in normalize_str(it.get("conta"))]
            print(f"\nContas de segurança em {key}:")
            for it in seg_items[:10]:
                print(f"rotulo: {it.get('rotulo')} | conta: {it.get('conta')} | cod_conta: {it.get('cod_conta')} | coluna: {it.get('coluna')} | valor: {it.get('valor')}")
        else:
            print(f"Chave {key} não encontrada no cache.")
else:
    print("Cache não encontrado.")
