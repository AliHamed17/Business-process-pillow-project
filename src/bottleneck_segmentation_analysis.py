import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

try:
    from cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from plot_utils import annotate_bars, apply_rtl_text, finalize_and_save, fix_hebrew, set_plot_style, truncate_label
except ModuleNotFoundError:  # package-import fallback for tests
    from .cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from .plot_utils import annotate_bars, apply_rtl_text, finalize_and_save, fix_hebrew, set_plot_style, truncate_label


REQUIRED_COLUMNS = ['case_id', 'activity', 'timestamp']


def _ensure_optional_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {
        'stage_responsible': 'stage_owner',
        'resource': 'performer',
        'department': 'department',
        'request_status': 'request_status',
    }
    out = df.copy()
    for src, dst in mapping.items():
        if src in out.columns:
            out[dst] = out[src].fillna('Unknown')
        elif dst not in out.columns:
            out[dst] = 'Unknown'
    return out


def _case_cycle(df: pd.DataFrame) -> pd.DataFrame:
    case_cycle = df.groupby('case_id').agg(
        case_start=('timestamp', 'min'),
        case_end=('timestamp', 'max'),
        request_status=('request_status', 'last'),
        department=('department', 'last'),
    ).reset_index()
    case_cycle['cycle_time_days'] = (
        case_cycle['case_end'] - case_cycle['case_start']
    ).dt.total_seconds() / (24 * 3600)
    return case_cycle


def _event_wait(df: pd.DataFrame) -> pd.DataFrame:
    e = df.sort_values(['case_id', 'timestamp']).copy()
    e['next_timestamp'] = e.groupby('case_id')['timestamp'].shift(-1)
    e['wait_time_days'] = (e['next_timestamp'] - e['timestamp']).dt.total_seconds() / (24 * 3600)
    return e


def _save_segmentation_plots(wait_by_stage: pd.DataFrame, wait_by_owner: pd.DataFrame, wait_by_performer: pd.DataFrame, outcome_cycle: pd.DataFrame, keyword_wait: pd.DataFrame, output_dir: Path) -> None:
    set_plot_style()
    import numpy as np

    if not wait_by_stage.empty:
        top_stages = wait_by_stage.head(10).copy()
        fig, ax1 = plt.subplots(figsize=(10, 6))
        labels = [truncate_label(x, 25) for x in top_stages['activity'].astype(str)]
        y_pos = np.arange(len(labels))
        height = 0.35
        
        ax1.barh(y_pos - height/2, top_stages['mean_wait_days'], height, label='Mean Wait Time (Days)', color='#C44E52')
        ax2 = ax1.twiny()
        ax2.barh(y_pos + height/2, top_stages['event_count'], height, label='Execution Frequency', color='#4C72B0')
        
        ax1.set_yticks(y_pos)
        ax1.set_yticklabels(labels)
        ax1.invert_yaxis()
        
        apply_rtl_text(ax1, title='Bottleneck Frequency vs. Duration (Top 10 Stages)', xlabel='Wait Time (Days)', ylabel='Stage')
        ax2.set_xlabel('Event Frequency')
        
        lines_1, labels_1 = ax1.get_legend_handles_labels()
        lines_2, labels_2 = ax2.get_legend_handles_labels()
        ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='lower right', bbox_to_anchor=(0.95, 0.05))
        finalize_and_save(fig, output_dir / 'bottleneck_frequency_vs_duration.png')

    if not wait_by_owner.empty:
        top = wait_by_owner.head(10)
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.barh([truncate_label(x, 32) for x in top['stage_owner'].astype(str)], top['mean_wait_days'], color='#4C72B0')
        ax.invert_yaxis()
        apply_rtl_text(ax, title='Top Stage Owners by Mean Wait', xlabel='Mean Wait (Days)')
        annotate_bars(ax, horizontal=True)
        finalize_and_save(fig, output_dir / 'bottleneck_by_stage_owner_top10.png')

    if not wait_by_performer.empty:
        top = wait_by_performer.head(10)
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.barh([truncate_label(x, 32) for x in top['performer'].astype(str)], top['mean_wait_days'], color='#55A868')
        ax.invert_yaxis()
        apply_rtl_text(ax, title='Top Performers by Mean Wait', xlabel='Mean Wait (Days)')
        annotate_bars(ax, horizontal=True)
        finalize_and_save(fig, output_dir / 'bottleneck_by_performer_top10.png')

    if not outcome_cycle.empty:
        fig, ax = plt.subplots(figsize=(8, 4.8))
        ax.bar([fix_hebrew(x) for x in outcome_cycle['request_status'].astype(str)], outcome_cycle['mean_cycle_time_days'], color='#C44E52')
        apply_rtl_text(ax, title='Cycle Time by Request Outcome/Status', ylabel='Mean Cycle Time (Days)')
        ax.tick_params(axis='x', rotation=20)
        finalize_and_save(fig, output_dir / 'cycle_time_by_request_status.png')

    if not keyword_wait.empty:
        fig, ax = plt.subplots(figsize=(8, 4.8))
        ax.bar(keyword_wait['keyword'], keyword_wait['mean_wait_days'], color='#8172B2')
        apply_rtl_text(ax, title='Mean Wait in Known Bottleneck Keywords', ylabel='Mean Wait (Days)')
        annotate_bars(ax, horizontal=False)
        finalize_and_save(fig, output_dir / 'keyword_bottleneck_waits.png')


def analyze_bottleneck_segmentation(logfile_path, output_dir):
    output_dir = Path(output_dir)
    df = load_clean_log(logfile_path, REQUIRED_COLUMNS, context='bottleneck segmentation analysis')
    df = _ensure_optional_columns(df)

    case_cycle = _case_cycle(df)
    event_wait = _event_wait(df)

    wait_by_stage = (
        event_wait.groupby('activity', dropna=False)['wait_time_days']
        .agg(['mean', 'count'])
        .reset_index()
        .rename(columns={'mean': 'mean_wait_days', 'count': 'event_count'})
        .sort_values('mean_wait_days', ascending=False)
    )
    wait_by_stage.to_csv(output_dir / 'bottleneck_by_stage.csv', index=False)

    wait_by_owner = (
        event_wait.groupby('stage_owner', dropna=False)['wait_time_days']
        .mean().reset_index(name='mean_wait_days')
        .sort_values('mean_wait_days', ascending=False)
    )
    wait_by_owner.to_csv(output_dir / 'bottleneck_by_stage_owner.csv', index=False)

    wait_by_performer = (
        event_wait.groupby('performer', dropna=False)['wait_time_days']
        .mean().reset_index(name='mean_wait_days')
        .sort_values('mean_wait_days', ascending=False)
    )
    wait_by_performer.to_csv(output_dir / 'bottleneck_by_performer.csv', index=False)

    dept_cycle = (
        case_cycle.groupby('department', dropna=False)['cycle_time_days']
        .agg(['count', 'mean', 'median', 'max'])
        .reset_index()
        .rename(columns={'mean': 'mean_cycle_time_days', 'median': 'median_cycle_time_days', 'max': 'max_cycle_time_days'})
        .sort_values('mean_cycle_time_days', ascending=False)
    )
    dept_cycle.to_csv(output_dir / 'cycle_time_by_department.csv', index=False)

    outcome_cycle = (
        case_cycle.groupby('request_status', dropna=False)['cycle_time_days']
        .agg(['count', 'mean', 'median', 'max'])
        .reset_index()
        .rename(columns={'mean': 'mean_cycle_time_days', 'median': 'median_cycle_time_days', 'max': 'max_cycle_time_days'})
        .sort_values('mean_cycle_time_days', ascending=False)
    )
    outcome_cycle.to_csv(output_dir / 'cycle_time_by_request_status.csv', index=False)

    keywords = {
        'screening_sorting': ['מיון', 'סינון', 'screen', 'sort'],
        'committee': ['ועדה', 'committee'],
    }
    rows = []
    for k, terms in keywords.items():
        mask = event_wait['activity'].astype(str).str.lower().apply(lambda a: any(t.lower() in a for t in terms))
        subset = event_wait.loc[mask, 'wait_time_days'].dropna()
        rows.append({'keyword': k, 'mean_wait_days': float(subset.mean()) if not subset.empty else None, 'event_count': int(mask.sum())})
    keyword_wait = pd.DataFrame(rows)
    keyword_wait.to_csv(output_dir / 'keyword_bottleneck_analysis.csv', index=False)

    _save_segmentation_plots(wait_by_stage, wait_by_owner, wait_by_performer, outcome_cycle, keyword_wait.dropna(subset=['mean_wait_days']), output_dir)
    print('Bottleneck segmentation analysis complete.')


def parse_args():
    parser = argparse.ArgumentParser(description='Analyze bottlenecks by stage/owner/user/department/outcome and keyword hotspots')
    parser.add_argument('logfile', help='Path to cleaned_log.csv')
    parser.add_argument('--output-dir', default='outputs', help='Directory for generated outputs')
    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    logfile = ensure_exists(args.logfile, 'Cleaned log')
    output_dir = ensure_output_dir(args.output_dir)
    analyze_bottleneck_segmentation(logfile, output_dir)
