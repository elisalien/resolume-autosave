"""Standalone Settings window — launched in its own process from the tray app."""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path
from typing import Any

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from arena_client import ArenaClient
from backup import backup_composition, find_composition_file, prune_backups
from config import load_config, save_config, set_start_with_windows


class SettingsApp:
    def __init__(self) -> None:
        self.cfg = load_config()
        self.root = tk.Tk()
        self.root.title("Resolume Autosave")
        self.root.geometry("460x420")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

        frm = ttk.Frame(self.root, padding=14)
        frm.pack(fill="both", expand=True)

        self.enabled_var = tk.BooleanVar()
        self.host_var = tk.StringVar()
        self.port_var = tk.StringVar()
        self.interval_var = tk.StringVar()
        self.keep_var = tk.StringVar()
        self.copy_var = tk.BooleanVar()
        self.startup_var = tk.BooleanVar()
        self.comp_dir_var = tk.StringVar()
        self.backup_dir_var = tk.StringVar()
        self.status_var = tk.StringVar(value="")

        row = 0
        ttk.Checkbutton(frm, text="Autosave enabled", variable=self.enabled_var).grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(0, 8)
        )
        row += 1

        ttk.Label(frm, text="Arena host").grid(row=row, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.host_var, width=18).grid(row=row, column=1, sticky="w")
        ttk.Label(frm, text="Port").grid(row=row, column=2, sticky="e")
        ttk.Entry(frm, textvariable=self.port_var, width=8).grid(
            row=row, column=2, sticky="e", padx=(40, 0)
        )
        row += 1

        ttk.Label(frm, text="Interval (seconds)").grid(row=row, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(frm, textvariable=self.interval_var, width=10).grid(
            row=row, column=1, sticky="w", pady=(8, 0)
        )
        row += 1

        ttk.Label(frm, text="Keep backups").grid(row=row, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(frm, textvariable=self.keep_var, width=10).grid(
            row=row, column=1, sticky="w", pady=(8, 0)
        )
        row += 1

        ttk.Checkbutton(
            frm,
            text="Also copy timestamped .avc into Autosaves folder",
            variable=self.copy_var,
        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(10, 4))
        row += 1

        ttk.Checkbutton(
            frm,
            text="Start with Windows",
            variable=self.startup_var,
        ).grid(row=row, column=0, columnspan=3, sticky="w", pady=(0, 8))
        row += 1

        ttk.Label(frm, text="Compositions folder").grid(row=row, column=0, columnspan=3, sticky="w")
        row += 1
        ttk.Entry(frm, textvariable=self.comp_dir_var, width=48).grid(
            row=row, column=0, columnspan=2, sticky="we"
        )
        ttk.Button(frm, text="…", width=3, command=self._browse_comp).grid(
            row=row, column=2, sticky="e"
        )
        row += 1

        ttk.Label(frm, text="Autosaves folder").grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )
        row += 1
        ttk.Entry(frm, textvariable=self.backup_dir_var, width=48).grid(
            row=row, column=0, columnspan=2, sticky="we"
        )
        ttk.Button(frm, text="…", width=3, command=self._browse_backup).grid(
            row=row, column=2, sticky="e"
        )
        row += 1

        btns = ttk.Frame(frm)
        btns.grid(row=row, column=0, columnspan=3, sticky="we", pady=(14, 6))
        ttk.Button(btns, text="Save now", command=self._save_now).pack(side="left")
        ttk.Button(btns, text="Test connection", command=self._test).pack(side="left", padx=6)
        ttk.Button(btns, text="Open Autosaves", command=self._open_backups).pack(side="left")
        ttk.Button(btns, text="Apply", command=self.apply).pack(side="right")
        row += 1

        ttk.Label(frm, textvariable=self.status_var, wraplength=420, foreground="#333").grid(
            row=row, column=0, columnspan=3, sticky="w", pady=(8, 0)
        )

        self._load_from_cfg()
        self.root.lift()
        try:
            self.root.attributes("-topmost", True)
            self.root.after(150, lambda: self.root.attributes("-topmost", False))
        except tk.TclError:
            pass
        self.root.focus_force()

    def _load_from_cfg(self) -> None:
        cfg = self.cfg
        self.enabled_var.set(bool(cfg.get("enabled", True)))
        self.host_var.set(str(cfg.get("host", "127.0.0.1")))
        self.port_var.set(str(cfg.get("port", 8080)))
        self.interval_var.set(str(cfg.get("interval_seconds", 300)))
        self.keep_var.set(str(cfg.get("keep_backups", 30)))
        self.copy_var.set(bool(cfg.get("also_copy_after_save", True)))
        self.startup_var.set(bool(cfg.get("start_with_windows", False)))
        self.comp_dir_var.set(str(cfg.get("compositions_dir", "")))
        self.backup_dir_var.set(str(cfg.get("backup_dir", "")))

    def apply(self) -> bool:
        try:
            cfg: dict[str, Any] = dict(self.cfg)
            cfg["enabled"] = bool(self.enabled_var.get())
            cfg["host"] = self.host_var.get().strip() or "127.0.0.1"
            cfg["port"] = int(self.port_var.get().strip())
            cfg["interval_seconds"] = max(30, int(self.interval_var.get().strip()))
            cfg["keep_backups"] = max(1, int(self.keep_var.get().strip()))
            cfg["also_copy_after_save"] = bool(self.copy_var.get())
            cfg["start_with_windows"] = bool(self.startup_var.get())
            cfg["compositions_dir"] = self.comp_dir_var.get().strip()
            cfg["backup_dir"] = self.backup_dir_var.get().strip()
            save_config(cfg)
            set_start_with_windows(bool(cfg["start_with_windows"]))
            self.cfg = cfg
            self.status_var.set("Settings saved.")
            return True
        except ValueError:
            messagebox.showerror(
                "Invalid value",
                "Check port / interval / keep backups (numbers only).",
            )
            return False

    def _browse_comp(self) -> None:
        path = filedialog.askdirectory(initialdir=self.comp_dir_var.get() or None)
        if path:
            self.comp_dir_var.set(path)

    def _browse_backup(self) -> None:
        path = filedialog.askdirectory(initialdir=self.backup_dir_var.get() or None)
        if path:
            self.backup_dir_var.set(path)

    def _run_once(self) -> str:
        """One-shot save using current on-disk settings (after Apply)."""
        import time

        cfg = self.cfg
        client = ArenaClient(cfg["host"], int(cfg["port"]))
        status = client.status()
        if not status.ok:
            raise RuntimeError(status.message or "Arena not reachable")

        name = status.composition_name or client.composition_name()
        if not name:
            raise RuntimeError("Composition has no name - Save As once in Arena first")

        client.save()
        msg = f'Saved "{name}"'

        if cfg.get("also_copy_after_save", True):
            compositions_dir = Path(cfg["compositions_dir"])
            backup_dir = Path(cfg["backup_dir"])
            source = find_composition_file(compositions_dir, name)
            if source is None:
                msg += " (no .avc copy - file not found in compositions folder)"
            else:
                time.sleep(0.35)
                dest = backup_composition(source, backup_dir, name)
                removed = prune_backups(backup_dir, name, int(cfg["keep_backups"]))
                msg += f" -> {dest.name}"
                if removed:
                    msg += f" (pruned {removed})"
        return msg

    def _save_now(self) -> None:
        if not self.apply():
            return
        try:
            msg = self._run_once()
            self.status_var.set(msg)
        except Exception as exc:  # noqa: BLE001
            self.status_var.set(str(exc))
            messagebox.showerror("Save failed", str(exc))

    def _test(self) -> None:
        if not self.apply():
            return
        cfg = self.cfg
        status = ArenaClient(cfg["host"], int(cfg["port"])).status()
        if status.ok:
            self.status_var.set(
                f"OK - {status.product}"
                + (f' / "{status.composition_name}"' if status.composition_name else "")
            )
        else:
            self.status_var.set(status.message)
            messagebox.showwarning("Connection", status.message)

    def _open_backups(self) -> None:
        path = Path(self.backup_dir_var.get() or self.cfg["backup_dir"])
        path.mkdir(parents=True, exist_ok=True)
        webbrowser.open(path.as_uri())

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    SettingsApp().run()


if __name__ == "__main__":
    main()
