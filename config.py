"""Load / save autosave settings."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"
DEFAULT_PATH = APP_DIR / "config.default.json"

DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "host": "127.0.0.1",
    "port": 8080,
    "interval_seconds": 300,
    "backup_dir": "",
    "keep_backups": 30,
    "also_copy_after_save": True,
    "compositions_dir": "",
    "start_with_windows": False,
}


def default_compositions_dir() -> Path:
    return Path.home() / "Documents" / "Resolume Arena" / "compositions"


def default_backup_dir() -> Path:
    return Path.home() / "Documents" / "Resolume Arena" / "Autosaves"


def load_config() -> dict[str, Any]:
    cfg = deepcopy(DEFAULTS)
    if DEFAULT_PATH.exists():
        try:
            cfg.update(json.loads(DEFAULT_PATH.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            pass
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            pass

    if not str(cfg.get("compositions_dir") or "").strip():
        cfg["compositions_dir"] = str(default_compositions_dir())
    if not str(cfg.get("backup_dir") or "").strip():
        cfg["backup_dir"] = str(default_backup_dir())

    cfg["port"] = int(cfg.get("port") or 8080)
    cfg["interval_seconds"] = max(30, int(cfg.get("interval_seconds") or 300))
    cfg["keep_backups"] = max(1, int(cfg.get("keep_backups") or 30))
    cfg["enabled"] = bool(cfg.get("enabled", True))
    cfg["also_copy_after_save"] = bool(cfg.get("also_copy_after_save", True))
    cfg["start_with_windows"] = bool(cfg.get("start_with_windows", False))
    return cfg


def save_config(cfg: dict[str, Any]) -> None:
    CONFIG_PATH.write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def set_start_with_windows(enable: bool) -> None:
    """Register / unregister a Run key entry for the tray app."""
    try:
        import winreg
    except ImportError:
        return

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    name = "ResolumeAutosave"
    script = str(APP_DIR / "start.bat")
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
        if enable:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, f'"{script}"')
        else:
            try:
                winreg.DeleteValue(key, name)
            except FileNotFoundError:
                pass
