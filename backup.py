"""Timestamped composition backups and pruning."""

from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path


SAFE_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]+')


def sanitize(name: str) -> str:
    cleaned = SAFE_NAME.sub("_", name).strip(" .")
    return cleaned or "Untitled"


def find_composition_file(compositions_dir: Path, name: str) -> Path | None:
    if not name:
        return None
    direct = compositions_dir / f"{name}.avc"
    if direct.is_file():
        return direct

    # Case-insensitive fallback
    target = f"{name}.avc".lower()
    if compositions_dir.is_dir():
        for path in compositions_dir.glob("*.avc"):
            if path.name.lower() == target:
                return path
    return None


def backup_composition(
    source: Path,
    backup_dir: Path,
    composition_name: str,
) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = backup_dir / f"{sanitize(composition_name)}_{stamp}.avc"
    shutil.copy2(source, dest)
    return dest


def prune_backups(backup_dir: Path, composition_name: str, keep: int) -> int:
    if keep < 1 or not backup_dir.is_dir():
        return 0
    prefix = f"{sanitize(composition_name)}_"
    files = sorted(
        (
            p
            for p in backup_dir.glob("*.avc")
            if p.name.startswith(prefix)
        ),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    removed = 0
    for old in files[keep:]:
        try:
            old.unlink()
            removed += 1
        except OSError:
            pass
    return removed
