import pandas as pd

df = pd.read_csv("enrollment.csv")

print("Raw data:")
print(df)
print(f"\nMissing values:\n{df.isnull().sum()}")

# Option 1: Treat missing as Not Retained
df_option1 = df.copy()
df_option1["Retained"] = df_option1["Retained"].fillna("No")
df_option1["Retained"] = df_option1["Retained"].map({"Yes": 1, "No": 0})
print(f"\nOption 1 (missing = No): {df_option1['Retained'].mean():.1%}")

# Option 2: Exclude missing from calculation
df_option2 = df.dropna(subset=["Retained"]).copy()
df_option2["Retained"] = df_option2["Retained"].map({"Yes": 1, "No": 0})
print(f"Option 2 (exclude missing): {df_option2['Retained'].mean():.1%}")
