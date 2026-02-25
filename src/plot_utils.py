from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt


def set_plot_style() -> None:
    """Apply a consistent style across all generated charts."""
    plt.style.use('seaborn-v0_8-whitegrid')


def finalize_and_save(fig: plt.Figure, output_path: Path, dpi: int = 150) -> None:
    """Tighten layout, save figure, and close to free memory."""
    fig.tight_layout()
    fig.savefig(output_path, dpi=dpi)
    plt.close(fig)
