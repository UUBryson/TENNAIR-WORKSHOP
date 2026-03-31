import pandas as pd

df = pd.read_csv("enrollment.csv")

# Normalize Retained into numeric flag: Yes=1, No=0, blank stays missing
df["retained_flag"] = (df["Retained"].str.strip().str.lower().map({"yes": 1, "no": 0}))

# Cohort-level retention rate (ignores missing retained values)
retention_by_cohort = (
    df.groupby("Cohort", dropna=False)["retained_flag"]
    .mean()
    .reset_index(name="RetentionRate")
)

print(df)
print("\nRetention by cohort:")
print(retention_by_cohort)
