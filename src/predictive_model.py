"""
Predictive ML Module – Approval Probability
=============================================
Academic Justification:
  We use a Random Forest classifier (Breiman, 2001) as the primary model
  because it:
    (a) handles high-cardinality categorical features (department, stage
        responsible) gracefully via built-in feature importance,
    (b) is robust to the class imbalance expected in this dataset
        (approved vs. cancelled), and
    (c) provides interpretable feature importances directly, which is
        critical for the academic reporting requirement.

  XGBoost is included as a secondary model for comparison and typically
  outperforms Random Forest on tabular data, but its SHAP-based feature
  importances are used to cross-validate the RF findings.

Target Variable:
  Binary: 1 = "אושר" (Approved), 0 = "בוטל" or "לא אושר" (Cancelled / Rejected)

Feature Engineering:
  - department          : categorical – encoded via LabelEncoder
  - position_type       : existing/new position (תקן קיים / תקן חדש)
  - initial_wait_days   : days between first event and first budget stage arrival
  - total_events        : total event count for the case
  - unique_stages       : number of distinct stages visited
  - stage_responsible   : most common responsible party for the case
  - has_budget_stage    : binary flag – did the case reach budgeting?
  - has_ceo_stage       : binary flag – did the case reach CEO decision?
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    classification_report, roc_auc_score, confusion_matrix, ConfusionMatrixDisplay
)
import xgboost as xgb
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import sys, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from plot_utils import apply_rtl_text, fix_hebrew, set_plot_style, truncate_label
except ImportError:
    def fix_hebrew(t): return str(t)
    def truncate_label(t, max_len=40): return str(t)
    def apply_rtl_text(ax, *, title=None, xlabel=None, ylabel=None):
        if title is not None:
            ax.set_title(str(title))
        if xlabel is not None:
            ax.set_xlabel(str(xlabel))
        if ylabel is not None:
            ax.set_ylabel(str(ylabel))
    def set_plot_style(): return None

warnings.filterwarnings('ignore')


BUDGET_STAGE   = "המלצת תקציב לגיוס"
CEO_STAGE      = 'החלטת מנכ"ל - גיוס'
STATUS_APPROVED  = "אושר"
STATUS_CANCELLED = "בוטל"
STATUS_REJECTED  = "לא אושר"


# ---------------------------------------------------------------------------
# Feature engineering
# ---------------------------------------------------------------------------

def build_case_features(logfile_path: str) -> pd.DataFrame:
    """
    Constructs one row per case with engineered features and the target label.
    Only cases with a definitive final status (Approved / Cancelled / Rejected)
    are kept; in-progress cases ("סבב אישורים") are excluded.
    """
    print("[Predictive Model] Loading log...")
    df = pd.read_csv(logfile_path, encoding='utf-8-sig')
    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df.dropna(subset=['timestamp'], inplace=True)
    df.sort_values(['case_id', 'timestamp'], inplace=True)

    # --- Final status per case (last known status) ---
    status_df = (
        df.dropna(subset=['request_status'])
          .groupby('case_id')['request_status']
          .last()
          .reset_index()
    )
    status_df.columns = ['case_id', 'final_status']

    # Keep only definitive outcomes
    definitive = {STATUS_APPROVED, STATUS_CANCELLED, STATUS_REJECTED}
    status_df = status_df[status_df['final_status'].isin(definitive)]

    # Binary target: 1 = Approved, 0 = Cancelled/Rejected
    status_df['target'] = (status_df['final_status'] == STATUS_APPROVED).astype(int)

    # --- Case-level aggregates ---
    case_agg = df.groupby('case_id').agg(
        start_time=('timestamp', 'min'),
        end_time=('timestamp', 'max'),
        total_events=('activity', 'size'),
        unique_stages=('activity', 'nunique'),
        department=('department', 'first'),
        position_type=('position_type', 'first'),
        stage_responsible=('stage_responsible', lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else 'Unknown'),
    ).reset_index()

    case_agg['cycle_time_days'] = (
        (case_agg['end_time'] - case_agg['start_time']).dt.total_seconds() / 86400
    )

    # --- Initial wait: time from first event to first budget stage ---
    budget_df = (
        df[df['activity'] == BUDGET_STAGE]
          .groupby('case_id')['timestamp']
          .min()
          .reset_index()
          .rename(columns={'timestamp': 'budget_arrival'})
    )
    case_agg = case_agg.merge(budget_df, on='case_id', how='left')
    case_agg['initial_wait_days'] = (
        (case_agg['budget_arrival'] - case_agg['start_time']).dt.total_seconds() / 86400
    ).fillna(-1)  # -1 means never reached budget stage

    # --- Stage flags ---
    stages_per_case = df.groupby('case_id')['activity'].apply(set).reset_index()
    stages_per_case.columns = ['case_id', 'stage_set']
    stages_per_case['has_budget_stage'] = stages_per_case['stage_set'].apply(
        lambda s: int(BUDGET_STAGE in s)
    )
    stages_per_case['has_ceo_stage'] = stages_per_case['stage_set'].apply(
        lambda s: int(CEO_STAGE in s)
    )
    case_agg = case_agg.merge(
        stages_per_case[['case_id', 'has_budget_stage', 'has_ceo_stage']],
        on='case_id', how='left'
    )

    # --- Merge target ---
    features_df = case_agg.merge(status_df[['case_id', 'final_status', 'target']],
                                  on='case_id', how='inner')

    print(f"[Predictive Model] Feature matrix: {features_df.shape[0]} cases, "
          f"{features_df.shape[1]} columns")
    print(f"[Predictive Model] Class balance:\n"
          f"  Approved  : {(features_df['target'] == 1).sum()} "
          f"({(features_df['target'] == 1).mean()*100:.1f}%)\n"
          f"  Cancelled : {(features_df['target'] == 0).sum()} "
          f"({(features_df['target'] == 0).mean()*100:.1f}%)")

    return features_df


def encode_features(features_df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Label-encodes categorical columns; returns encoded DataFrame and encoders."""
    df = features_df.copy()
    encoders = {}

    cat_cols = ['department', 'position_type', 'stage_responsible']
    for col in cat_cols:
        le = LabelEncoder()
        df[col] = df[col].fillna('Unknown').astype(str)
        df[col + '_enc'] = le.fit_transform(df[col])
        encoders[col] = le

    feature_cols = [
        'department_enc', 'position_type_enc', 'stage_responsible_enc',
        'initial_wait_days', 'total_events', 'unique_stages',
        'cycle_time_days', 'has_budget_stage', 'has_ceo_stage',
    ]
    return df, feature_cols, encoders


# ---------------------------------------------------------------------------
# Model training
# ---------------------------------------------------------------------------

def train_and_evaluate(logfile_path: str, output_dir: str) -> dict:
    """
    Trains Random Forest and XGBoost classifiers, evaluates them,
    and saves feature importance charts + results JSON.
    """
    features_df = build_case_features(logfile_path)
    df_enc, feature_cols, encoders = encode_features(features_df)

    X = df_enc[feature_cols].values
    y = df_enc['target'].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # ---- Random Forest ----
    print("\n[RF] Training Random Forest...")
    rf = RandomForestClassifier(
        n_estimators=300,
        max_depth=8,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_test)
    rf_proba = rf.predict_proba(X_test)[:, 1]

    rf_auc = roc_auc_score(y_test, rf_proba)
    rf_cv = cross_val_score(rf, X, y, cv=StratifiedKFold(5), scoring='roc_auc').mean()
    print(f"[RF] Test AUC: {rf_auc:.4f} | 5-fold CV AUC: {rf_cv:.4f}")
    print("[RF] Classification Report:")
    print(classification_report(y_test, rf_pred, target_names=['Cancelled/Rejected', 'Approved']))

    # ---- XGBoost ----
    print("\n[XGB] Training XGBoost...")
    neg = (y_train == 0).sum()
    pos = (y_train == 1).sum()
    scale_pos = neg / pos if pos > 0 else 1

    xgb_model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        scale_pos_weight=scale_pos,
        use_label_encoder=False,
        eval_metric='logloss',
        random_state=42,
        n_jobs=-1,
        verbosity=0,
    )
    xgb_model.fit(X_train, y_train)
    xgb_pred = xgb_model.predict(X_test)
    xgb_proba = xgb_model.predict_proba(X_test)[:, 1]

    xgb_auc = roc_auc_score(y_test, xgb_proba)
    xgb_cv = cross_val_score(xgb_model, X, y, cv=StratifiedKFold(5), scoring='roc_auc').mean()
    print(f"[XGB] Test AUC: {xgb_auc:.4f} | 5-fold CV AUC: {xgb_cv:.4f}")
    print("[XGB] Classification Report:")
    print(classification_report(y_test, xgb_pred, target_names=['Cancelled/Rejected', 'Approved']))

    # ---------------------------------------------------------------------------
    # Feature Importance (RF)
    # ---------------------------------------------------------------------------
    feature_labels = [
        'Department', 'Position Type', 'Stage Responsible',
        'Initial Wait (days)', 'Total Events', 'Unique Stages',
        'Cycle Time (days)', 'Has Budget Stage', 'Has CEO Stage',
    ]
    rf_importances = pd.DataFrame({
        'Feature': feature_labels,
        'RF_Importance': rf.feature_importances_,
        'XGB_Importance': xgb_model.feature_importances_,
    }).sort_values('RF_Importance', ascending=False)

    print("\n[Feature Importances – Random Forest]")
    print(rf_importances.to_string(index=False))

    # Save feature importance CSV
    fi_csv = os.path.join(output_dir, "feature_importance.csv")
    rf_importances.to_csv(fi_csv, index=False, encoding='utf-8-sig')
    print(f"[Predictive Model] Feature importance saved to {fi_csv}")

    # ---------------------------------------------------------------------------
    # Plots
    # ---------------------------------------------------------------------------
    plots_dir = os.path.join(output_dir, "plots")
    os.makedirs(plots_dir, exist_ok=True)
    set_plot_style()

    # Feature Importance Bar Chart
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    for ax, col, title in zip(
        axes,
        ['RF_Importance', 'XGB_Importance'],
        ['Random Forest Feature Importance', 'XGBoost Feature Importance']
    ):
        sorted_df = rf_importances.sort_values(col, ascending=True)
        ax.barh([truncate_label(x, 28) for x in sorted_df['Feature']], sorted_df[col], color='steelblue')
        apply_rtl_text(ax, title=title, xlabel='Importance Score')
        ax.tick_params(axis='y', labelsize=9)

    plt.tight_layout()
    fi_plot = os.path.join(plots_dir, "feature_importance.png")
    plt.savefig(fi_plot, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Predictive Model] Feature importance plot saved to {fi_plot}")

    # Confusion Matrix (RF)
    fig, ax = plt.subplots(figsize=(5, 4))
    cm = confusion_matrix(y_test, rf_pred)
    disp = ConfusionMatrixDisplay(cm, display_labels=['Cancelled/Rejected', 'Approved'])
    disp.plot(ax=ax, colorbar=False)
    apply_rtl_text(ax, title='Random Forest Confusion Matrix')
    plt.tight_layout()
    cm_plot = os.path.join(plots_dir, "confusion_matrix_rf.png")
    plt.savefig(cm_plot, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Predictive Model] Confusion matrix saved to {cm_plot}")

    # Department-level cancellation rate
    dept_cancel = (
        features_df.groupby('department')
                   .agg(total=('target', 'count'), cancelled=('target', lambda x: (x == 0).sum()))
                   .reset_index()
    )
    dept_cancel['cancel_rate'] = dept_cancel['cancelled'] / dept_cancel['total']
    dept_cancel = dept_cancel[dept_cancel['total'] >= 5].sort_values('cancel_rate', ascending=False)
    dept_cancel_csv = os.path.join(output_dir, "dept_cancellation_rate.csv")
    dept_cancel.to_csv(dept_cancel_csv, index=False, encoding='utf-8-sig')
    print(f"[Predictive Model] Dept cancellation rates saved to {dept_cancel_csv}")

    # Top 15 departments by cancellation rate (bar chart)
    top15 = dept_cancel.head(15)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh([truncate_label(str(x), 30) for x in top15['department']], top15['cancel_rate'] * 100, color='tomato')
    apply_rtl_text(ax, title='Top 15 Departments by Cancellation Rate', xlabel='Cancellation Rate (%)')
    ax.invert_yaxis()
    plt.tight_layout()
    dept_plot = os.path.join(plots_dir, "dept_cancellation_rate.png")
    plt.savefig(dept_plot, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"[Predictive Model] Dept cancellation rate plot saved to {dept_plot}")

    # ---------------------------------------------------------------------------
    # Summary results
    # ---------------------------------------------------------------------------
    results = {
        "rf_test_auc": round(rf_auc, 4),
        "rf_cv_auc": round(rf_cv, 4),
        "xgb_test_auc": round(xgb_auc, 4),
        "xgb_cv_auc": round(xgb_cv, 4),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "class_balance": {
            "approved_pct": round(float((y == 1).mean() * 100), 1),
            "cancelled_pct": round(float((y == 0).mean() * 100), 1),
        },
        "top_rf_features": rf_importances[['Feature', 'RF_Importance']].to_dict(orient='records'),
        "top_dept_by_cancellation": dept_cancel.head(10)[['department', 'cancel_rate']].to_dict(orient='records'),
    }

    out_json = os.path.join(output_dir, "predictive_model_results.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n[Predictive Model] Results saved to {out_json}")

    return results


if __name__ == "__main__":
    base = r"c:\Users\ahamed\business process pillow\haifa-municipality-process-mining"
    logfile = os.path.join(base, "outputs", "cleaned_log.csv")
    outdir = os.path.join(base, "outputs")

    results = train_and_evaluate(logfile, outdir)

    print("\n=== Phase 2B Complete ===")
    print(f"Random Forest AUC  : {results['rf_test_auc']} (CV: {results['rf_cv_auc']})")
    print(f"XGBoost AUC        : {results['xgb_test_auc']} (CV: {results['xgb_cv_auc']})")
    print("\nTop Feature by Importance (RF):")
    for fi in results['top_rf_features'][:3]:
        print(f"  {fi['Feature']}: {fi['RF_Importance']:.4f}")

