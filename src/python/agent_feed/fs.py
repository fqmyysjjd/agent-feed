"""Filesystem helpers."""

from __future__ import annotations

import filecmp
from pathlib import Path


IGNORED_TREE_NAMES = {".DS_Store", "__pycache__"}


def same_tree(left: Path, right: Path) -> bool:
    if not left.is_dir() or not right.is_dir():
        return False
    comparison = filecmp.dircmp(left, right)
    left_only = set(comparison.left_only) - IGNORED_TREE_NAMES
    right_only = set(comparison.right_only) - IGNORED_TREE_NAMES
    diff_files = set(comparison.diff_files) - IGNORED_TREE_NAMES
    if left_only or right_only or diff_files:
        return False
    common_dirs = set(comparison.common_dirs) - IGNORED_TREE_NAMES
    return all(same_tree(left / name, right / name) for name in common_dirs)


def has_existing_content(path: Path) -> bool:
    return path.exists() and (not path.is_dir() or any(path.iterdir()))
