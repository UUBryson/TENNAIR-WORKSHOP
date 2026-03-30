import pandas as pd

df = pd.read_csv("enrollment.csv")

# BUG 1: Wrong column name (case sensitive)
# BUG 2: Dividing string column by numeric column
df["RetentionRate"] = df["retained"] / df["Cohort"]

print(df)
