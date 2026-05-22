import pandas as pd
import numpy as np

def to_markdown_custom(df, title):
    headers = ["UF"] + [str(col) for col in df.columns]
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join(["---"] * len(headers)) + " |"
    lines = [header_line, separator_line]
    
    for idx, row in df.iterrows():
        cells = [str(idx)]
        for val in row:
            if pd.isnull(val):
                cells.append("[NL]")
            else:
                cells.append(f"{val:.2f}%")
        lines.append("| " + " | ".join(cells) + " |")
        
    md = f"### {title}\n\n"
    md += "\n".join(lines)
    md += "\n\n"
    return md

try:
    df_exceto = pd.read_csv("segpub_pivot_exceto.csv", sep=";", decimal=",", index_col=0)
    df_total = pd.read_csv("segpub_pivot_total.csv", sep=";", decimal=",", index_col=0)
    df_api = pd.read_csv("segpub_pivot_api.csv", sep=";", decimal=",", index_col=0)
    
    md_exceto = to_markdown_custom(df_exceto, "Tabela 1: Segurança Pública (função 06) como % das Despesas Liquidadas Exceto Intra-Orçamentárias (I)")
    md_total = to_markdown_custom(df_total, "Tabela 2: Segurança Pública Total (Exceto + Intra) como % das Despesas Liquidadas Totais (III = I + II)")
    md_api = to_markdown_custom(df_api, "Tabela 3: Percentual % (d/total d) extraído diretamente da API do SICONFI")
    
    output_path = "tabelas_markdown.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# Tabelas de Segurança Pública nos Estados (2015-2024)\n\n")
        f.write(md_exceto)
        f.write(md_total)
        f.write(md_api)
        
    print(f"Tabelas formatadas e salvas em '{output_path}'")
except Exception as e:
    print(f"Erro ao formatar tabelas: {e}")
