from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt


def set_plot_style() -> None:
    """Apply a consistent, readable style across all generated charts."""
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams.update(
        {
            'font.size': 10,
            'axes.titlesize': 13,
            'axes.labelsize': 11,
            'xtick.labelsize': 9,
            'ytick.labelsize': 9,
            'legend.fontsize': 9,
        }
    )


def finalize_and_save(fig: plt.Figure, output_path: Path, dpi: int = 150) -> None:
    """Tighten layout, save figure, and close to free memory."""
    fig.tight_layout()
    fig.savefig(output_path, dpi=dpi)
    plt.close(fig)


def truncate_label(label: str, max_len: int = 40) -> str:
    text = str(label)
    return text if len(text) <= max_len else text[: max_len - 1] + '…'


def annotate_bars(ax, horizontal: bool = False, fmt: str = '{:.1f}') -> None:
    """Add value labels on bar charts for easier reading."""
    for patch in ax.patches:
        if horizontal:
            value = patch.get_width()
            if value is None:
                continue
            ax.text(
                value,
                patch.get_y() + patch.get_height() / 2,
                f' {fmt.format(value)}',
                va='center',
                ha='left',
            )
        else:
            value = patch.get_height()
            if value is None:
                continue
            ax.text(
                patch.get_x() + patch.get_width() / 2,
                value,
                fmt.format(value),
                va='bottom',
                ha='center',
            )
