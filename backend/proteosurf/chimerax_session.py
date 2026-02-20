"""
ChimeraX subprocess management.

Launches ChimeraX in REST-API mode and provides methods to send commands,
capture snapshots, and manage the process lifecycle.
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_PORT = int(os.environ.get("CHIMERAX_PORT", "9999"))
CHIMERAX_BIN = os.environ.get(
    "CHIMERAX_BIN",
    shutil.which("chimerax") or shutil.which("ChimeraX") or "/usr/bin/chimerax",
)


class ChimeraXError(Exception):
    pass


class ChimeraXSession:
    """Manages a headless ChimeraX subprocess communicating via its REST API."""

    def __init__(self, port: int = DEFAULT_PORT, timeout: float = 10.0):
        self.port = port
        self.timeout = timeout
        self.base_url = f"http://127.0.0.1:{port}"
        self._process: subprocess.Popen | None = None

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.poll() is None

    async def start(self) -> None:
        if self.is_running:
            logger.info("ChimeraX already running on port %d", self.port)
            return

        cmd = [
            CHIMERAX_BIN,
            "--nogui",
            "--cmd", f"remotecontrol rest start port {self.port}",
        ]
        logger.info("Launching ChimeraX: %s", " ".join(cmd))

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            raise ChimeraXError(
                f"ChimeraX binary not found at '{CHIMERAX_BIN}'. "
                "Set CHIMERAX_BIN env var to the correct path."
            )

        await self._wait_for_ready()

    async def _wait_for_ready(self, retries: int = 20, delay: float = 0.5) -> None:
        """Poll the REST endpoint until ChimeraX is responsive."""
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    resp = await client.get(f"{self.base_url}/cmdline")
                    if resp.status_code == 200:
                        logger.info("ChimeraX ready after %d attempts", attempt + 1)
                        return
            except (httpx.ConnectError, httpx.ReadError):
                pass
            await asyncio.sleep(delay)

        raise ChimeraXError(
            f"ChimeraX did not become ready on port {self.port} "
            f"after {retries * delay:.0f}s"
        )

    async def run_command(self, command: str) -> str:
        """Send a ChimeraX command via the REST API and return the text reply."""
        if not self.is_running:
            await self.start()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(
                    f"{self.base_url}/run",
                    params={"command": command},
                )
                resp.raise_for_status()
                return resp.text
            except httpx.HTTPStatusError as exc:
                raise ChimeraXError(
                    f"ChimeraX command failed ({exc.response.status_code}): {command}"
                )
            except httpx.ConnectError:
                raise ChimeraXError("Lost connection to ChimeraX")

    async def snapshot(
        self,
        width: int = 1024,
        height: int = 768,
        transparent: bool = False,
    ) -> str:
        """Capture the current ChimeraX view and return it as a base64-encoded PNG."""
        tmp = Path(tempfile.mktemp(suffix=".png"))
        bg = "transparent" if transparent else "white"
        await self.run_command(
            f"save {tmp} width {width} height {height} transparentBackground {bg}"
        )

        if not tmp.exists():
            raise ChimeraXError("Snapshot file was not created")

        data = tmp.read_bytes()
        tmp.unlink(missing_ok=True)
        return base64.b64encode(data).decode("ascii")

    async def stop(self) -> None:
        if self._process and self._process.poll() is None:
            try:
                await self.run_command("exit")
                self._process.wait(timeout=5)
            except Exception:
                self._process.send_signal(signal.SIGTERM)
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._process.kill()
            logger.info("ChimeraX stopped")
        self._process = None


# ---------------------------------------------------------------------------
# Singleton session for the MCP server
# ---------------------------------------------------------------------------

_session: ChimeraXSession | None = None


def get_session(port: int = DEFAULT_PORT) -> ChimeraXSession:
    global _session
    if _session is None or not _session.is_running:
        _session = ChimeraXSession(port=port)
    return _session
