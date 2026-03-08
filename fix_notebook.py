import json

def fix_notebook():
    file_path = r'notebooks\חיזוימעבדה.ipynb'
    with open(file_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    # Dictionary of cell index to new source code
    # We use lists of strings for 'source' to match standard ipynb format
    replacements = {
        3: """# Read the event log
df = pd.read_csv("patients-log.csv")

# Clean column names
df.columns = df.columns.str.strip()

# Convert DateTime column to datetime type
df["DateTime"] = pd.to_datetime(df["DateTime"])

# Show basic info
df.head()""",

        6: """important_columns = ["patient", "action", "org:resource"]

for col in important_columns:
    print(f"\\n Column: {col}")
    print(f"Number of unique values: {df[col].nunique()}")
    print("Unique values:")
    print(df[col].unique())""",

        9: """plt.figure(figsize=(10, 5))

action_counts = df["action"].value_counts()

sns.barplot(
    x=action_counts.values,
    y=action_counts.index,
)

plt.title("Frequency of Medical Actions in the Event Log")
plt.xlabel("Number of Occurrences")
plt.ylabel("Action")
plt.tight_layout()
plt.show()""",

        11: """# Sort events by patient and time
df_sorted = df.sort_values(["patient", "DateTime"])

# Create next action per patient
df_sorted["next_action"] = df_sorted.groupby("patient")["action"].shift(-1)

# Remove last events (no next action)
transitions = df_sorted.dropna(subset=["next_action"])""",

        12: """transition_counts = (
    transitions
    .groupby(["action", "next_action"])
    .size()
    .reset_index(name="count")
)

pivot_table = transition_counts.pivot(
    index="action",
    columns="next_action",
    values="count"
).fillna(0)

plt.figure(figsize=(12, 8))

sns.heatmap(
    pivot_table,
    annot=True,
    fmt=".0f",
    cmap="Blues"
)

plt.title("Action-to-Next-Action Transition Frequencies")
plt.xlabel("Next Action")
plt.ylabel("Current Action")
plt.tight_layout()
plt.show()""",

        16: """# Use only rows with a next action
data = df_sorted.dropna(subset=["next_action"])

# Build X and y
# y must be a 1D Series
y = data["next_action"]

# X must only contain features, NOT the target
X = data[["patient", "action", "org:resource"]]

# One-hot encode categorical features
X_encoded = pd.get_dummies(X, columns=["patient", "action", "org:resource"])

# 80% train, 20% temp
try:
    X_train, X_temp, y_train, y_temp = train_test_split(
        X_encoded, y, test_size=0.2, random_state=42, stratify=y
    )
    # Split temp into 10% validation, 10% test
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
    )
except ValueError:
    print("Warning: Stratifcation failed (likely due to rare classes). Falling back to random split.")
    X_train, X_temp, y_train, y_temp = train_test_split(
        X_encoded, y, test_size=0.2, random_state=42
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42
    )""",

        19: """# Base fallback model
best_model = RandomForestClassifier(n_estimators=50, random_state=42)
if len(X_train) > 0: best_model.fit(X_train, y_train)

best_score = -1
best_params = {'n_estimators': 50, 'max_depth': None}

for n_estimators in [50, 100, 200]:
    for max_depth in [5, 10, 15, None]:
        model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42
        )
        if len(X_train) > 0: model.fit(X_train, y_train)
        score = model.score(X_val, y_val) if len(X_val) > 0 else 0

        # Fix condition to accept even nan or zero if it's the first
        if score >= best_score:
            best_score = score
            best_model = model
            best_params = {'n_estimators': n_estimators, 'max_depth': max_depth}

print("Best validation accuracy:", best_score)
print("Best hyperparameters:", best_params)""",

        23: """# Read the event log
df = pd.read_csv("patients-log.csv")

# ---------- CLEAN & SORT ----------
df.columns = df.columns.str.strip()

# Convert DateTime column to datetime type
df["DateTime"] = pd.to_datetime(df["DateTime"])

df = df.sort_values(["patient", "DateTime"])

# ---------- PATIENT SPLIT (80 / 10 / 10) ----------
patients = df["patient"].unique()

train_p, temp_p = train_test_split(
    patients, test_size=0.2, random_state=42
)
val_p, test_p = train_test_split(
    temp_p, test_size=0.5, random_state=42
)

df_train = df[df["patient"].isin(train_p)].copy()
df_val   = df[df["patient"].isin(val_p)].copy()
df_test  = df[df["patient"].isin(test_p)].copy()""",

        24: """# ---------- LABEL ----------
def build_labels(d):
    return (
        d.groupby("patient")["action"]
        .apply(lambda x: int("Surgery" in x.values))
        .reset_index(name="has_surgery")
    )

y_train_df = build_labels(df_train)
y_val_df   = build_labels(df_val)
y_test_df  = build_labels(df_test)

# ---------- PREFIX ----------
MAX_EVENTS = 5

def fixed_prefix(trace):
    return trace.sort_values("DateTime").head(MAX_EVENTS)

def apply_prefix(df_part):
    # Since df is already sorted by DateTime in Cell 23, we can just use head()
    return df_part.groupby("patient").head(MAX_EVENTS)

df_train_prefix = apply_prefix(df_train)
df_val_prefix   = apply_prefix(df_val)
df_test_prefix  = apply_prefix(df_test)

# ---------- SEQUENCE ENCODING ----------
activities = sorted(df["action"].unique())

def encode(df_prefix):
    rows = []
    for patient, trace in df_prefix.groupby("patient"):
        row = {"patient": patient}
        trace = trace.sort_values("DateTime")

        for i in range(MAX_EVENTS):
            if i < len(trace):
                event = trace.iloc[i]
                row[f"time_{i}"] = event["DateTime"].timestamp()
                for act in activities:
                    row[f"{act}_{i}"] = int(event["action"] == act)
            else:
                row[f"time_{i}"] = 0
                for act in activities:
                    row[f"{act}_{i}"] = 0

        rows.append(row)
    return pd.DataFrame(rows)

# ---------- FINAL DATASETS ----------
X_train = encode(df_train_prefix).merge(y_train_df, on="patient")
X_val   = encode(df_val_prefix).merge(y_val_df, on="patient")
X_test  = encode(df_test_prefix).merge(y_test_df, on="patient")

y_train = X_train.pop("has_surgery")
y_val   = X_val.pop("has_surgery")
y_test  = X_test.pop("has_surgery")

X_train = X_train.drop(columns=["patient"])
X_val   = X_val.drop(columns=["patient"])
X_test  = X_test.drop(columns=["patient"])""",

        27: """# Base fallback model
best_model = RandomForestClassifier(n_estimators=50, random_state=42, class_weight="balanced")
if len(X_train) > 0: best_model.fit(X_train, y_train)

best_score = -1
best_params = {'n_estimators': 50, 'max_depth': None}

for n_estimators in [50, 100, 200]:
    for max_depth in [5, 10, 15, None]:
        model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            random_state=42,
            class_weight="balanced"
        )
        if len(X_train) > 0: model.fit(X_train, y_train)
        score = model.score(X_val, y_val) if len(X_val) > 0 else 0

        # Fix condition to accept even nan or zero if it's the first
        if score >= best_score:
            best_score = score
            best_model = model
            best_params = {'n_estimators': n_estimators, 'max_depth': max_depth}

print("Best validation accuracy:", best_score)
print("Best hyperparameters:", best_params)"""
    }

    # Find the indices of code cells only to match my dumped indices
    code_cells_only = [c for c in nb['cells'] if c['cell_type'] == 'code']
    
    for idx, new_code in replacements.items():
        # Split into list of strings with newlines like jupyter expects
        lines = [line + '\\n' for line in new_code.split('\\n')]
        if lines:
            lines[-1] = lines[-1].replace('\\n', '') # Last line shouldn't have trailing newline unless explicit
        
        # We mapped idx based on the enumerate mapping for code boundaries, wait, no, the enumerate was over ALL cells!
        # Let's check how I dumped it. 
        # `[f.write(f'# --- CELL {i} ---\\n' + ''.join(c['source']) + '\\n\\n') for i, c in enumerate(nb['cells']) if c['cell_type'] == 'code']`
        # This means `i` is the absolute index in nb['cells']!
        
        nb['cells'][idx]['source'] = lines

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        
    print("Notebook successfully updated.")

if __name__ == "__main__":
    fix_notebook()
