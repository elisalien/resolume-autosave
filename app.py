"""Resolume Autosave — lightweight tray companion for Arena composition saves."""

from __future__ import annotations

import logging
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
from datetime import datetime
from pathlib import Path
from typing import Any

from arena_client import ArenaClient
from backup import backup_composition, find_composition_file, prune_backups
from config import APP_DIR, CONFIG_PATH, load_config, save_config

try:
    import pystray
    from PIL import Image
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "Missing dependencies. Run: pip install -r requirements.txt\n"
        f"({exc})"
    ) from exc


LOG_PATH = APP_DIR / "autosave.log"


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("resolume_autosave")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
        fh.setFormatter(fmt)
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        logger.addHandler(fh)
        logger.addHandler(sh)
    return logger


log = setup_logging()

_TRAY_CACHE: dict[bool, Image.Image] = {}


def make_icon(active: bool) -> Image.Image:
    """Tray icon: little gold stars (gray when paused)."""
    if active in _TRAY_CACHE:
        return _TRAY_CACHE[active].copy()

    from icons import ASSETS, make_stars_icon

    path = ASSETS / ("tray_on.png" if active else "tray_off.png")
    if path.is_file():
        img = Image.open(path).convert("RGBA")
    else:
        img = make_stars_icon(64, active=active)
    _TRAY_CACHE[active] = img
    return img.copy()


def _pythonw() -> str:
    """Prefer pythonw so Settings has no console flash."""
    exe = Path(sys.executable)
    if exe.name.lower() == "python.exe":
        candidate = exe.with_name("pythonw.exe")
        if candidate.is_file():
            return str(candidate)
    return str(exe)


def parse_overrides(argv: list[str]) -> dict[str, Any]:
    """Settings given on the command line (Tamagosc options form). They win over config.json."""
    import argparse

    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--headless", action="store_true")
    p.add_argument("--once", action="store_true")
    p.add_argument("--host")
    p.add_argument("--port", type=int)
    p.add_argument("--interval", dest="interval_seconds", type=int)
    p.add_argument("--keep", dest="keep_backups", type=int)
    p.add_argument("--backup-dir", dest="backup_dir")
    p.add_argument("--compositions-dir", dest="compositions_dir")
    args, _ = p.parse_known_args(argv)
    out = {k: v for k, v in vars(args).items() if v is not None and k not in ("headless", "once")}
    if "interval_seconds" in out:
        out["interval_seconds"] = max(30, out["interval_seconds"])
    if "keep_backups" in out:
        out["keep_backups"] = max(1, out["keep_backups"])
    return out


class AutosaveEngine:
    def __init__(self, overrides: dict[str, Any] | None = None) -> None:
        # Headless runs (Tamagosc) pass their settings here; they stay applied over
        # config.json reloads, and the loop is always on (stop the tool to pause).
        self.overrides = dict(overrides or {})
        self.cfg = self._load()
        self._cfg_mtime = self._read_mtime()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._lock = threading.Lock()
        self.last_status = "Starting..."
        self.last_ok_at: datetime | None = None
        self.last_error = ""
        self.saves = 0
        self.thread = threading.Thread(target=self._loop, name="autosave", daemon=True)
        self.on_config_changed: Any = None

    def _load(self) -> dict[str, Any]:
        cfg = load_config()
        if self.overrides:
            cfg.update(self.overrides)
            cfg["enabled"] = True
        return cfg

    def _read_mtime(self) -> float:
        try:
            return CONFIG_PATH.stat().st_mtime
        except OSError:
            return 0.0

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._wake.set()
        self.thread.join(timeout=3)

    def reload(self, cfg: dict[str, Any] | None = None) -> None:
        with self._lock:
            self.cfg = cfg or self._load()
            self._cfg_mtime = self._read_mtime()
        self._wake.set()
        if self.on_config_changed:
            try:
                self.on_config_changed()
            except Exception:  # noqa: BLE001
                log.exception("on_config_changed failed")

    def _maybe_reload_from_disk(self) -> None:
        mtime = self._read_mtime()
        if mtime and mtime != self._cfg_mtime:
            log.info("Config changed on disk — reloading")
            self.reload()

    def toggle_enabled(self) -> bool:
        with self._lock:
            self.cfg["enabled"] = not bool(self.cfg.get("enabled", True))
            save_config(self.cfg)
            self._cfg_mtime = self._read_mtime()
            enabled = bool(self.cfg["enabled"])
        self._wake.set()
        return enabled

    def run_once(self) -> str:
        with self._lock:
            cfg = dict(self.cfg)
        return self._tick(cfg)

    def _loop(self) -> None:
        while not self._stop.is_set():
            self._maybe_reload_from_disk()
            with self._lock:
                cfg = dict(self.cfg)
            if cfg.get("enabled", True):
                try:
                    msg = self._tick(cfg)
                    self.last_status = msg
                    self.last_error = ""
                    log.info(msg)
                except Exception as exc:  # noqa: BLE001
                    self.last_error = str(exc)
                    self.last_status = f"Error: {exc}"
                    log.error("%s\n%s", exc, traceback.format_exc())
            else:
                self.last_status = "Paused"

            interval = max(30, int(cfg.get("interval_seconds") or 300))
            self._wake.wait(timeout=interval)
            self._wake.clear()

    def _tick(self, cfg: dict[str, Any]) -> str:
        client = ArenaClient(cfg["host"], int(cfg["port"]))
        status = client.status()
        if not status.ok:
            raise RuntimeError(status.message or "Arena not reachable")

        name = status.composition_name or client.composition_name()
        if not name:
            raise RuntimeError("Composition has no name - Save As once in Arena first")

        client.save()
        self.saves += 1
        self.last_ok_at = datetime.now()
        msg = f'Saved "{name}"'

        if cfg.get("also_copy_after_save", True):
            compositions_dir = Path(cfg["compositions_dir"])
            backup_dir = Path(cfg["backup_dir"])
            source = find_composition_file(compositions_dir, name)
            if source is None:
                msg += " (no .avc copy - file not found in compositions folder)"
            else:
                # Brief settle so Arena finishes writing
                time.sleep(0.35)
                dest = backup_composition(source, backup_dir, name)
                removed = prune_backups(backup_dir, name, int(cfg["keep_backups"]))
                msg += f" -> {dest.name}"
                if removed:
                    msg += f" (pruned {removed})"
        return msg


class TrayApp:
    def __init__(self) -> None:
        self.engine = AutosaveEngine()
        self.engine.on_config_changed = self.refresh_icon
        self._settings_proc: subprocess.Popen[Any] | None = None
        self.icon = pystray.Icon(
            "resolume_autosave",
            make_icon(True),
            "Resolume Autosave",
            menu=self._menu(),
        )

    def _menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem("Settings...", self.open_settings, default=True),
            pystray.MenuItem(
                lambda item: "Pause autosave" if self.engine.cfg.get("enabled", True) else "Resume autosave",
                self.toggle,
            ),
            pystray.MenuItem("Save now", self.save_now),
            pystray.MenuItem("Open Autosaves folder", self.open_backups),
            pystray.MenuItem("Open log", self.open_log),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", self.quit),
        )

    def refresh_icon(self) -> None:
        active = bool(self.engine.cfg.get("enabled", True))
        self.icon.icon = make_icon(active)
        self.icon.title = (
            "Resolume Autosave - ON"
            if active
            else "Resolume Autosave - PAUSED"
        )

    def notify(self, title: str, message: str) -> None:
        try:
            self.icon.notify(message, title)
        except Exception:  # noqa: BLE001
            pass

    def open_settings(self, _icon=None, _item=None) -> None:
        """Launch Settings in a separate process (avoids Tk + tray thread issues)."""
        log.info("Settings menu clicked")
        if self._settings_proc is not None and self._settings_proc.poll() is None:
            try:
                self._settings_proc.terminate()
            except Exception:  # noqa: BLE001
                pass
            time.sleep(0.15)

        script = APP_DIR / "settings_ui.py"
        try:
            self._settings_proc = subprocess.Popen(
                [_pythonw(), str(script)],
                cwd=str(APP_DIR),
                close_fds=True,
            )
            log.info("Settings process started pid=%s", self._settings_proc.pid)
        except Exception:  # noqa: BLE001
            log.exception("Failed to launch Settings")
            self.notify("Resolume Autosave", "Could not open Settings")

    def toggle(self, _icon=None, _item=None) -> None:
        enabled = self.engine.toggle_enabled()
        self.refresh_icon()
        self.notify("Resolume Autosave", "Enabled" if enabled else "Paused")

    def save_now(self, _icon=None, _item=None) -> None:
        def work() -> None:
            try:
                msg = self.engine.run_once()
                self.notify("Autosave", msg)
            except Exception as exc:  # noqa: BLE001
                self.notify("Autosave failed", str(exc))

        threading.Thread(target=work, daemon=True).start()

    def open_backups(self, _icon=None, _item=None) -> None:
        path = Path(self.engine.cfg["backup_dir"])
        path.mkdir(parents=True, exist_ok=True)
        webbrowser.open(path.as_uri())

    def open_log(self, _icon=None, _item=None) -> None:
        LOG_PATH.touch(exist_ok=True)
        webbrowser.open(LOG_PATH.as_uri())

    def quit(self, _icon=None, _item=None) -> None:
        self.engine.stop()
        if self._settings_proc is not None and self._settings_proc.poll() is None:
            try:
                self._settings_proc.terminate()
            except Exception:  # noqa: BLE001
                pass
        self.icon.stop()

    def run(self) -> None:
        self.engine.start()
        self.refresh_icon()
        log.info("Resolume Autosave started")
        self.icon.run()


def run_headless(argv: list[str]) -> None:
    """No tray icon: started and set up from Tamagosc (LOG on stdout)."""
    engine = AutosaveEngine(parse_overrides(argv))
    cfg = engine.cfg
    if "--once" in argv:
        try:
            print(engine.run_once(), flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"Save failed: {exc}", flush=True)
            sys.exit(1)
        return
    log.info(
        "Resolume Autosave started (headless): every %ss, Arena %s:%s, keep %s in %s",
        cfg["interval_seconds"], cfg["host"], cfg["port"], cfg["keep_backups"], cfg["backup_dir"],
    )
    engine.start()
    try:
        engine.thread.join()
    except KeyboardInterrupt:
        engine.stop()


def main() -> None:
    if "--settings" in sys.argv:
        from settings_ui import main as settings_main

        settings_main()
        return
    if "--headless" in sys.argv or "--once" in sys.argv:
        run_headless(sys.argv[1:])
        return
    TrayApp().run()


if __name__ == "__main__":
    main()
