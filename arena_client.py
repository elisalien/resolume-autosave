"""Minimal Resolume Arena REST client for composition save / status."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class ArenaStatus:
    ok: bool
    product: str = ""
    composition_name: str = ""
    message: str = ""


class ArenaClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 8080, timeout: float = 5.0):
        self.host = host.strip() or "127.0.0.1"
        self.port = int(port)
        self.timeout = timeout

    @property
    def base(self) -> str:
        return f"http://{self.host}:{self.port}/api/v1"

    def _request(self, method: str, path: str) -> Any:
        url = f"{self.base}{path}"
        req = urllib.request.Request(url, method=method)
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            raw = resp.read()
            if not raw:
                return None
            ctype = resp.headers.get("Content-Type", "")
            if "json" in ctype or raw[:1] in (b"{", b"["):
                return json.loads(raw.decode("utf-8"))
            return raw.decode("utf-8", errors="replace")

    def ping(self) -> ArenaStatus:
        try:
            data = self._request("GET", "/product")
            product = ""
            if isinstance(data, dict):
                product = str(
                    data.get("name")
                    or data.get("product")
                    or data.get("displayname")
                    or "Resolume"
                )
            return ArenaStatus(ok=True, product=product or "Resolume")
        except urllib.error.URLError as exc:
            return ArenaStatus(
                ok=False,
                message=(
                    "Arena webserver unreachable. Enable it in "
                    f"Preferences > Webserver (port {self.port}). "
                    f"({exc.reason})"
                ),
            )
        except Exception as exc:  # noqa: BLE001
            return ArenaStatus(ok=False, message=str(exc))

    def composition_name(self) -> str:
        data = self._request("GET", "/composition")
        if not isinstance(data, dict):
            return ""
        name = data.get("name") or data.get("displayname") or ""
        if isinstance(name, dict):
            # Some builds nest value under parameter-like objects
            name = name.get("value") or name.get("name") or ""
        return str(name).strip()

    def status(self) -> ArenaStatus:
        ping = self.ping()
        if not ping.ok:
            return ping
        try:
            name = self.composition_name()
            return ArenaStatus(ok=True, product=ping.product, composition_name=name)
        except Exception as exc:  # noqa: BLE001
            return ArenaStatus(ok=True, product=ping.product, message=str(exc))

    def save(self) -> None:
        self._request("POST", "/composition/save")
