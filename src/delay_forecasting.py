import pandas as pd
import numpy as np
import os
import json
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import mean_absolute_error, r2_score
import matplotlib.pyplot as plt

def build_forecasting_features(logfile_path):
    """
    Creates a snapshot-base dataset where each event is a training point
    predicting the remaining time until the case ends.
    """
    print("[Delay Forecast] Processing log for regression...")
    df = pd.read_csv(logfile_path, encoding='utf-8-sig')
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df.sort_values(['case_id', 'timestamp'], inplace=True)

    # 1. Get total duration per case
    case_stats = df.groupby('case_id').agg(
        case_start=('timestamp', 'min'),
        case_end=('timestamp', 'max')
    ).reset_index()
    case_stats['total_duration_days'] = (case_stats['case_end'] - case_stats['case_start']).dt.total_seconds() / 86400

    # Merge back to original df
    df = df.merge(case_stats, on='case_id')

    # 2. Calculate elapsed time and target (remaining time)
    df['elapsed_days'] = (df['timestamp'] - df['case_start']).dt.total_seconds() / 86400
    df['remaining_days'] = df['total_duration_days'] - df['elapsed_days']

    # 3. Progressive features
    df['event_index'] = df.groupby('case_id').cumcount() + 1
    
    # We only want to predict for cases that actually finished (have a reasonable duration)
    # and we exclude the very last event (where remaining time is 0) to avoid triviality.
    train_df = df[df['remaining_days'] > 0.1].copy() # At least 0.1 days left

    return train_df

def train_forecaster(logfile_path, output_dir):
    data = build_forecasting_features(logfile_path)
    
    # Encoding
    le_activity = LabelEncoder()
    data['activity_enc'] = le_activity.fit_transform(data['activity'])
    
    le_dept = LabelEncoder()
    data['department'] = data['department'].fillna('Unknown')
    data['dept_enc'] = le_dept.fit_transform(data['department'])

    features = ['activity_enc', 'dept_enc', 'elapsed_days', 'event_index']
    X = data[features]
    y = data['remaining_days']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print(f"[Delay Forecast] Training on {len(X_train)} snapshots...")
    model = RandomForestRegressor(n_estimators=100, max_depth=12, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)

    # Eval
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    r2 = r2_score(y_test, preds)

    print(f"[Delay Forecast] MAE: {mae:.2f} days")
    print(f"[Delay Forecast] R2: {r2:.4f}")

    # Feature Importance
    fi = pd.DataFrame({
        'Feature': features,
        'Importance': model.feature_importances_
    }).sort_values('Importance', ascending=False)
    
    out_fi = os.path.join(output_dir, "delay_feature_importance.csv")
    fi.to_csv(out_fi, index=False)
    
    results = {
        "mae_days": round(mae, 2),
        "r2_score": round(r2, 4),
        "n_samples": len(data)
    }
    
    out_json = os.path.join(output_dir, "delay_forecast_results.json")
    with open(out_json, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"[Delay Forecast] Results saved to {out_json}")
    return results

if __name__ == "__main__":
    base = r"c:\Users\ahamed\business process pillow\haifa-municipality-process-mining"
    logfile = os.path.join(base, "outputs", "cleaned_log.csv")
    outdir = os.path.join(base, "outputs")
    
    train_forecaster(logfile, outdir)
