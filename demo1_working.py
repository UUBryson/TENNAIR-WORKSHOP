import pandas as pd

df = pd.read_csv("enrollment.csv")

# Clean the Retained column
df["Retained"] = df["Retained"].map({"Yes": 1, "No": 0})

# Calculate retention rate (ignoring blanks)
retention_rate = df["Retained"].mean()

print(df)
print(f"\nOverall retention rate: {retention_rate:.1%}")
