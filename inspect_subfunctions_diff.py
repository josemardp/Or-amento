import pandas as pd

try:
    df = pd.read_csv("all_states_safety_subfunctions.csv", sep=";")
    cols = df.columns.tolist()
    
    subfunc_col = cols[3]
    valor_col = cols[4]
    
    # Convert Valor to float by replacing comma and cleaning
    df[valor_col] = df[valor_col].astype(str).str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    df[valor_col] = pd.to_numeric(df[valor_col], errors="coerce").fillna(0.0)
    
    # Filter for 2023
    df_2023 = df[df["Ano"] == 2023]
    
    target_states = ["SP", "MG", "RJ", "RS", "BA"]
    df_targets = df_2023[df_2023["UF"].isin(target_states)]
    
    pivot = df_targets.pivot_table(
        index="UF",
        columns=subfunc_col,
        values=valor_col,
        aggfunc="sum",
        fill_value=0
    )
    
    # Convert to Millions for better reading
    pivot_mi = pivot / 1e6
    pivot_pct = pivot.div(pivot.sum(axis=1), axis=0) * 100
    
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    
    print("\nValores em R$ Milhões por Subfunção (2023):")
    print(pivot_mi.round(2))
    
    print("\nDistribuição Percentual (%) interna da Função 06 (2023):")
    print(pivot_pct.round(2))
    
except Exception as e:
    import traceback
    print(f"Erro: {e}")
    traceback.print_exc()
