import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

try:
    from cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from plot_utils import finalize_and_save, set_plot_style
except ModuleNotFoundError:  # package-import fallback for tests
    from .cli_utils import ensure_exists, ensure_output_dir, load_clean_log
    from .plot_utils import finalize_and_save, set_plot_style


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


def _save_segmentation_plots(wait_by_owner: pd.DataFrame, wait_by_performer: pd.DataFrame, outcome_cycle: pd.DataFrame, keyword_wait: pd.DataFrame, output_dir: Path) -> None:
    set_plot_style()

    if not wait_by_owner.empty:
        top = wait_by_owner.head(10)
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.barh(top['stage_owner'].astype(str), top['mean_wait_days'], color='#4C72B0')
        ax.invert_yaxis()
        ax.set_title('Top Stage Owners by Mean Wait')
        ax.set_xlabel('Mean Wait (Days)')
        finalize_and_save(fig, output_dir / 'bottleneck_by_stage_owner_top10.png')

    if not wait_by_performer.empty:
        top = wait_by_performer.head(10)
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.barh(top['performer'].astype(str), top['mean_wait_days'], color='#55A868')
        ax.invert_yaxis()
        ax.set_title('Top Performers by Mean Wait')
        ax.set_xlabel('Mean Wait (Days)')
        finalize_and_save(fig, output_dir / 'bottleneck_by_performer_top10.png')

    if not outcome_cycle.empty:
        fig, ax = plt.subplots(figsize=(8, 4.8))
        ax.bar(outcome_cycle['request_status'].astype(str), outcome_cycle['mean_cycle_time_days'], color='#C44E52')
        ax.set_title('Cycle Time by Request Outcome/Status')
        ax.set_ylabel('Mean Cycle Time (Days)')
        ax.tick_params(axis='x', rotation=20)
        finalize_and_save(fig, output_dir / 'cycle_time_by_request_status.png')

    if not keyword_wait.empty:
        fig, ax = plt.subplots(figsize=(8, 4.8))
        ax.bar(keyword_wait['keyword'], keyword_wait['mean_wait_days'], color='#8172B2')
        ax.set_title('Mean Wait in Known Bottleneck Keywords')
        ax.set_ylabel('Mean Wait (Days)')
        finalize_and_save(fig, output_dir / 'keyword_bottleneck_waits.png')


def analyze_bottleneck_segmentation(logfile_path, output_dir):
    output_dir = Path(output_dir)
    df = load_clean_log(logfile_path, REQUIRED_COLUMNS, context='bottleneck segmentation analysis')
    df = _ensure_optional_columns(df)

    case_cycle = _case_cycle(df)
    event_wait = _event_wait(df)

    wait_by_stage = (
        event_wait.groupby('activity', dropna=False)['wait_time_days']
        .mean().reset_index(name='mean_wait_days')
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

    _save_segmentation_plots(wait_by_owner, wait_by_performer, outcome_cycle, keyword_wait.dropna(subset=['mean_wait_days']), output_dir)
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
