from __future__ import annotations

import re
from pathlib import Path

import matplotlib.pyplot as plt

try:
    from bidi.algorithm import get_display as _bidi_get_display
    _HAS_BIDI = True
except ImportError:
    _HAS_BIDI = False

_HEBREW_RE = re.compile(r'[\u0590-\u05FF]')


def fix_hebrew(text: str) -> str:
    """Apply BiDi algorithm so Hebrew renders correctly (RTL) in matplotlib.

    Matplotlib renders all text LTR. The BiDi algorithm reorders the
    *logical* character sequence so that when matplotlib renders it LTR
    the *visual* result is correct RTL Hebrew.
    """
    text = str(text)
    if not _HAS_BIDI:
        return text
    # Only apply if the string actually contains Hebrew characters
    if _HEBREW_RE.search(text):
        return _bidi_get_display(text)
    return text


def has_hebrew(text: str) -> bool:
    return bool(_HEBREW_RE.search(str(text)))


def fix_hebrew_list(values) -> list[str]:
    return [fix_hebrew(value) for value in values]


def set_plot_style() -> None:
    """Apply a consistent, readable style across all generated charts."""
    plt.style.use('seaborn-v0_8-whitegrid')
    plt.rcParams.update(
        {
            'font.family': ['DejaVu Sans', 'Arial', 'sans-serif'],
            'font.size': 11,
            'axes.titlesize': 14,
            'axes.titleweight': 'semibold',
            'axes.labelsize': 12,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10,
            'legend.fontsize': 10,
            'axes.unicode_minus': False,
            'legend.frameon': False,
            'figure.dpi': 150,
            'savefig.dpi': 150,
        }
    )


def finalize_and_save(fig: plt.Figure, output_path: Path, dpi: int = 150) -> None:
    """Tighten layout, save figure, and close to free memory."""
    fig.tight_layout(pad=1.1)
    fig.savefig(output_path, dpi=dpi, bbox_inches='tight')
    plt.close(fig)


def truncate_label(label: str, max_len: int = 40) -> str:
    text = str(label)
    truncated = text if len(text) <= max_len else text[: max_len - 1] + '\u2026'
    return fix_hebrew(truncated)


def apply_rtl_text(ax, *, title: str | None = None, xlabel: str | None = None,
                   ylabel: str | None = None) -> None:
    """Apply RTL-safe strings to common axis text fields."""
    if title is not None:
        ax.set_title(fix_hebrew(title))
    if xlabel is not None:
        ax.set_xlabel(fix_hebrew(xlabel))
    if ylabel is not None:
        ax.set_ylabel(fix_hebrew(ylabel))


def set_rtl_ticklabels(ax, axis: str, labels, rotation: int = 0,
                       ha: str | None = None, fontsize: int | None = None) -> None:
    rendered = fix_hebrew_list(labels)
    if axis == 'x':
        ax.set_xticklabels(rendered, rotation=rotation, ha=ha, fontsize=fontsize)
        return
    ax.set_yticklabels(rendered, rotation=rotation, ha=ha, fontsize=fontsize)


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
