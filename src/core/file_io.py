"""Crash-safe helpers for replacing user-selected output files."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
from typing import Callable


def atomic_save(output_path: str | Path, writer: Callable[[Path], object]) -> None:
    """Write beside the destination and replace it only after a complete save."""
    destination = Path(output_path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.stem}.",
        suffix=destination.suffix,
        dir=destination.parent,
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        writer(temporary)
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
