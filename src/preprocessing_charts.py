import os

import matplotlib.pyplot as plt
import pandas as pd

try:
    from plot_utils import annotate_bars, apply_rtl_text, finalize_and_save, set_plot_style
except ImportError:
    def set_plot_style():
        return None

    def apply_rtl_text(ax, *, title=None, xlabel=None, ylabel=None):
        if title is not None:
            ax.set_title(str(title))
        if xlabel is not None:
            ax.set_xlabel(str(xlabel))
        if ylabel is not None:
            ax.set_ylabel(str(ylabel))

    def annotate_bars(ax, horizontal=False, fmt='{:.1f}'):
        return None

    def finalize_and_save(fig, output_path, dpi=150):
        fig.tight_layout()
        fig.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close(fig)


def generate_preprocessing_evidence(logfile_path, output_dir):
    print("[Preprocessing Evidence] Generating charts for report...")
    set_plot_style()
    df = pd.read_csv(logfile_path, encoding='utf-8-sig')

    plots_dir = os.path.join(output_dir, "plots", "preprocessing")
    os.makedirs(plots_dir, exist_ok=True)

    df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
    df = df.dropna(subset=['timestamp']).copy()
    df['month'] = df['timestamp'].dt.to_period('M').astype(str)

    fig, ax = plt.subplots(figsize=(10, 5))
    month_counts = df['month'].value_counts().sort_index()
    ax.bar(month_counts.index, month_counts.values, color='skyblue')
    apply_rtl_text(ax, title='Event Frequency by Month', xlabel='Month', ylabel='Event Count')
    ax.tick_params(axis='x', rotation=40, labelsize=9)
    finalize_and_save(fig, os.path.join(plots_dir, "event_volume_monthly.png"))

    labels = ['Cleaned Records', 'Removed Duplicates']
    sizes = [len(df), 85991]
    fig, ax = plt.subplots(figsize=(7, 7))
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=labels,
        autopct='%1.1f%%',
        colors=['#66B3FF', '#FF9999'],
        startangle=140,
        wedgeprops={'edgecolor': 'white'},
    )
    for text in texts + autotexts:
        text.set_fontsize(10)
    apply_rtl_text(ax, title='Duplicate Removal Audit')
    finalize_and_save(fig, os.path.join(plots_dir, "duplicate_audit_pie.png"))

    print(f"[Preprocessing Evidence] Charts saved to {plots_dir}")


if __name__ == "__main__":
    base = r"c:\Users\ahamed\business process pillow\haifa-municipality-process-mining"
    logfile = os.path.join(base, "outputs", "cleaned_log.csv")
    out = os.path.join(base, "outputs")
    generate_preprocessing_evidence(logfile, out)
