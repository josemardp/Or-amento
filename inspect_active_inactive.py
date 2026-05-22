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

def is_liquidada_col(col):
    col = normalize_str(col)
    return ("despesas liquidadas" in col and "ate o bimestre" in col) or "ate o bimestre (d)" in col

if not os.path.exists(CACHE_FILE):
    print("Cache não encontrado!")
    exit(1)

with open(CACHE_FILE, "r", encoding="utf-8") as f:
    cache = json.load(f)

# Subfunções da Função 06
# As subfunções padrão da Função 06 são:
# 181: Policiamento
# 182: Defesa Civil
# 183: Informação e Inteligência
# 122: Administração Geral (por vezes associada à função 06)
# 421: Custódia e Reintegração Social (por vezes na Função 14 ou 06)
# Demais subfunções

for uf in ["MG", "SP"]:
    key = f"{uf}_2023"
    items = cache.get(key, [])
    print(f"\n==================== {uf} 2023: Subfunções de Segurança Pública ====================")
    
    rows = []
    for it in items:
        conta = it.get("conta", "")
        coluna = it.get("coluna", "")
        cod_conta = str(it.get("cod_conta", "")).strip()
        
        try:
            valor = float(str(it.get("valor", 0)).replace(",", "."))
        except (ValueError, TypeError):
            valor = 0.0
            
        if is_liquidada_col(coluna) and valor > 0:
            # We want to identify the subfunctions under Segurança Pública
            # Let's inspect cod_conta and see if we can filter by them
            # Let's print the raw item if it relates to segurança pública
            if "seguranca" in normalize_str(conta) or "policiamento" in normalize_str(conta) or "defesa civil" in normalize_str(conta) or "inteligencia" in normalize_str(conta) or "fu06" in normalize_str(conta) or "custodia" in normalize_str(conta):
                rows.append((conta, cod_conta, valor))
                
    # Remove duplicates by grouping
    grouped = {}
    for conta, cod, val in rows:
        key_group = (conta, cod)
        grouped[key_group] = max(grouped.get(key_group, 0.0), val)
        
    for (conta, cod), val in sorted(grouped.items(), key=lambda x: x[0][0]):
        print(f"Conta: {conta:40s} | Cod: {cod:20s} | Valor: R$ {val:,.2f}")
