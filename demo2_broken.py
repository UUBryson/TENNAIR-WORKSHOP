import pandas as pd

df = pd.read_csv("enrollment.csv")

# Convert Yes/No to 1/0 (blank stays NaN)
df["RetainedFlag"] = df["Retained"].map({"Yes": 1, "No": 0})

# Student-level retained flag
df["RetentionRate"] = df["RetainedFlag"]

# BUG 1: Wrong column name (case sensitive)
# BUG 2: Dividing string column by numeric column
# df["RetentionRate"] = df["retained"] / df["Cohort"]

# Optional: cohort-level retention rate
cohort_rate = df["RetainedFlag"].mean(skipna=True)
print(f"\nCohort retention rate: {cohort_rate:.1%}")

print(f"\n{df}")
