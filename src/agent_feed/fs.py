"""Filesystem helpers."""

from __future__ import annotations

import filecmp
from pathlib import Path


def same_tree(left: Path, right: Path) -> bool:
    if not left.is_dir() or not right.is_dir():
        return False
    comparison = filecmp.dircmp(left, right)
    if comparison.left_only or comparison.right_only or comparison.diff_files:
        return False
    return all(same_tree(left / name, right / name) for name in comparison.common_dirs)


def has_existing_content(path: Path) -> bool:
    return path.exists() and (not path.is_dir() or any(path.iterdir()))
