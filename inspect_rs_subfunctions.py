import pandas as pd

df = pd.read_csv("all_states_safety_subfunctions.csv", sep=";")
df_rs = df[df["UF"] == "RS"].copy()
print(df_rs)
