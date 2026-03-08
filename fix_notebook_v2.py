import json

def fix_notebook():
    file_path = r'notebooks\חיזוימעבדה.ipynb'
    with open(file_path, 'r', encoding='utf-8') as f:
        nb = json.load(f)

    replacements = {
        3: """import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report

# Read the event log
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
sns.barplot(x=action_counts.values, y=action_counts.index)
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

        12: """transition_counts = transitions.groupby(["action", "next_action"]).size().reset_index(name="count")
pivot_table = transition_counts.pivot(index="action", columns="next_action", values="count").fillna(0)
plt.figure(figsize=(12, 8))
sns.heatmap(pivot_table, annot=True, fmt=".0f", cmap="Blues")
plt.title("Action-to-Next-Action Transition Frequencies")
plt.xlabel("Next Action")
plt.ylabel("Current Action")
plt.tight_layout()
plt.show()""",

        16: """# Use only rows with a next action
data = df_sorted.dropna(subset=["next_action"])

y = data["next_action"]
X = data[["patient", "action", "org:resource"]]

# One-hot encode categorical features
X_encoded = pd.get_dummies(X, columns=["patient", "action", "org:resource"])

try:
    X_train, X_temp, y_train, y_temp = train_test_split(
        X_encoded, y, test_size=0.2, random_state=42, stratify=y
    )
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
    )

print("Train shape:", X_train.shape, "| Label dist:", y_train.value_counts().to_dict() if len(y_train) < 10 else "...")
print("Val shape:  ", X_val.shape,   "| Label dist:", y_val.value_counts().to_dict() if len(y_val) < 10 else "...")
print("Test shape: ", X_test.shape,  "| Label dist:", y_test.value_counts().to_dict() if len(y_test) < 10 else "...")
""",

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
print("Best hyperparameters:", best_params)

if len(X_test) > 0:
    y_pred = best_model.predict(X_test)
else:
    y_pred = []""",

        21: """print("Test Accuracy:", accuracy_score(y_test, y_pred) if len(y_test) > 0 else 0)
print("\\nClassification Report:\\n")
if len(y_test) > 0:
    print(classification_report(y_test, y_pred, zero_division=0))
    print("Confusion Matrix:\\n", confusion_matrix(y_test, y_pred))""",

        23: """# Read the event log
df = pd.read_csv("patients-log.csv")

# ---------- CLEAN & SORT ----------
df.columns = df.columns.str.strip()
df["DateTime"] = pd.to_datetime(df["DateTime"])
df = df.sort_values(["patient", "DateTime"])

# ---------- PATIENT-LEVEL STRATIFIED SPLIT (80 / 10 / 10) ----------
# Calculate label for EACH PATIENT BEFORE SPLIT to ensure zero leakage and proper stratification
patient_labels = df.groupby("patient")["action"].apply(lambda x: int("Surgery" in x.values)).reset_index(name="has_surgery")

patients = patient_labels["patient"].values
labels = patient_labels["has_surgery"].values

try:
    train_p, temp_p, train_y, temp_y = train_test_split(
        patients, labels, test_size=0.2, random_state=42, stratify=labels
    )
    val_p, test_p, val_y, test_y = train_test_split(
        temp_p, temp_y, test_size=0.5, random_state=42, stratify=temp_y
    )
except ValueError:
    print("Warning: Patient stratifcation failed. Falling back to random split.")
    train_p, temp_p, train_y, temp_y = train_test_split(patients, labels, test_size=0.2, random_state=42)
    val_p, test_p, val_y, test_y = train_test_split(temp_p, temp_y, test_size=0.5, random_state=42)

df_train = df[df["patient"].isin(train_p)].copy()
df_val   = df[df["patient"].isin(val_p)].copy()
df_test  = df[df["patient"].isin(test_p)].copy()

y_train_df = pd.DataFrame({"patient": train_p, "has_surgery": train_y})
y_val_df   = pd.DataFrame({"patient": val_p, "has_surgery": val_y})
y_test_df  = pd.DataFrame({"patient": test_p, "has_surgery": test_y})""",

        24: """# ---------- SEQUENCE ENCODING LOGIC ----------
activities = sorted(df["action"].unique())

def encode(df_prefix, MAX_EVENTS):
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

def evaluate_surgery_prediction(MAX_EVENTS):
    print(f"\\n{'='*60}\\nEvaluating Surgery Prediction with MAX_EVENTS = {MAX_EVENTS}\\n{'='*60}")
    
    def apply_prefix(df_part):
        return df_part.groupby("patient").head(MAX_EVENTS)

    df_train_prefix = apply_prefix(df_train)
    df_val_prefix   = apply_prefix(df_val)
    df_test_prefix  = apply_prefix(df_test)

    # ---------- FINAL DATASETS ----------
    X_train = encode(df_train_prefix, MAX_EVENTS).merge(y_train_df, on="patient")
    X_val   = encode(df_val_prefix, MAX_EVENTS).merge(y_val_df, on="patient")
    X_test  = encode(df_test_prefix, MAX_EVENTS).merge(y_test_df, on="patient")

    y_train_split = X_train.pop("has_surgery")
    y_val_split   = X_val.pop("has_surgery")
    y_test_split  = X_test.pop("has_surgery")

    X_train.drop(columns=["patient"], inplace=True)
    X_val.drop(columns=["patient"], inplace=True)
    X_test.drop(columns=["patient"], inplace=True)
    
    print("Train shape:", X_train.shape, "| Label dist:", y_train_split.value_counts().to_dict())
    print("Val shape:  ", X_val.shape,   "| Label dist:", y_val_split.value_counts().to_dict())
    print("Test shape: ", X_test.shape,  "| Label dist:", y_test_split.value_counts().to_dict())
    
    # Grid Search
    best_model = RandomForestClassifier(n_estimators=50, random_state=42, class_weight="balanced")
    if len(X_train) > 0: best_model.fit(X_train, y_train_split)

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
            if len(X_train) > 0: model.fit(X_train, y_train_split)
            score = model.score(X_val, y_val_split) if len(X_val) > 0 else 0

            if score >= best_score:
                best_score = score
                best_model = model
                best_params = {'n_estimators': n_estimators, 'max_depth': max_depth}

    print("\\nBest validation accuracy:", best_score)
    print("Best hyperparameters:", best_params)
    
    if len(X_test) > 0:
        y_pred = best_model.predict(X_test)
        print("\\nTest Accuracy:", accuracy_score(y_test_split, y_pred))
        print("\\nClassification Report:\\n")
        print(classification_report(y_test_split, y_pred, zero_division=0))
        print("Confusion Matrix:\\n", confusion_matrix(y_test_split, y_pred))""",

        25: """# Run evaluation for MAX_EVENTS = 4
evaluate_surgery_prediction(MAX_EVENTS=4)""",

        27: """# Run evaluation for MAX_EVENTS = 5
evaluate_surgery_prediction(MAX_EVENTS=5)""",

        28: """# Comparison Conclusion:
# Both experiments ensure no leakage since the train/val/test splits are fully patient-stratified.
# Testing 4 vs 5 events allows us to understand if capturing one additional initial event 
# significantly boosts the predictive power for predicting downstream surgery."""
    }

    for idx, new_code in replacements.items():
        lines = [line + '\\n' for line in new_code.split('\\n')]
        if lines:
            lines[-1] = lines[-1].replace('\\n', '')
        
        nb['cells'][idx]['source'] = lines

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, indent=1, ensure_ascii=False)
        
    print("Notebook successfully updated.")

if __name__ == "__main__":
    fix_notebook()
