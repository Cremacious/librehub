"""LibreHub background daemon: focus-watch + engine + live config reload + IPC."""
from __future__ import annotations

import argparse
import asyncio
import contextlib
import os
import sys
from pathlib import Path

from . import config as C
from . import engine as E
from . import focus, ipc, ratbag, selection


class Daemon:
    def __init__(self, cfg_path: Path, engine, appid_fn, model: str):
        self.cfg_path = Path(cfg_path)
        self.engine = engine
        self.appid_fn = appid_fn
        self.model = model
        self.config = C.default_config()
        self.active_appid: str | None = None
        self._detect_future: asyncio.Future | None = None

    def reload_config(self) -> None:
        try:
            self.config = C.load(self.cfg_path)
        except C.ConfigError as e:
            print(f"librehub: keeping last-good config ({e})", file=sys.stderr)
            return
        self.apply_appid(self.active_appid)

    def apply_appid(self, appid: str | None) -> None:
        self.active_appid = appid
        self.engine.set_bindings(selection.active_bindings(self.config, appid))

    # --- detect mode (for GUI "press a button to identify") ---
    def _on_detect(self, code_name: str) -> bool:
        if self._detect_future is not None and not self._detect_future.done():
            if code_name.startswith("KEY_F"):
                self._detect_future.set_result(code_name)
                self._detect_future = None
                return True
        return False

    async def poll_focus(self, interval: float = 0.5) -> None:
        last = object()
        while True:
            appid = self.appid_fn()
            if appid != last:
                self.apply_appid(appid)
                last = appid
            await asyncio.sleep(interval)

    async def watch_config(self, interval: float = 1.0) -> None:
        last_mtime = None
        while True:
            try:
                mtime = self.cfg_path.stat().st_mtime
            except OSError:
                mtime = None
            if mtime != last_mtime:
                self.reload_config()
                last_mtime = mtime
            await asyncio.sleep(interval)

    async def _handle_client(self, reader, writer):
        try:
            line = await reader.readline()
            if not line:
                return
            msg = ipc.decode(line)
            cmd = msg.get("cmd")
            if cmd == "status":
                resp = {"daemon": True, "device": self.model,
                        "active_appid": self.active_appid}
            elif cmd == "current_appid":
                resp = {"appid": self.appid_fn()}
            elif cmd == "detect":
                self._detect_future = asyncio.get_running_loop().create_future()
                try:
                    fcode = await asyncio.wait_for(self._detect_future, timeout=10)
                except asyncio.TimeoutError:
                    fcode = None
                resp = {"fcode": fcode}
            else:
                resp = {"error": "unknown command"}
            writer.write(ipc.encode(resp))
            await writer.drain()
        except (ValueError, ConnectionError):
            pass
        finally:
            with contextlib.suppress(Exception):
                writer.close()

    async def serve_ipc(self) -> None:
        path = ipc.socket_path()
        with contextlib.suppress(FileNotFoundError):
            os.unlink(path)
        server = await asyncio.start_unix_server(self._handle_client, path)
        async with server:
            await server.serve_forever()

    def _resolve_signal_device(self):
        model = self.model
        if not model:
            try:
                dev = ratbag.resolve_device(None)
                model = ratbag.device_name(dev) if dev else None
            except ratbag.RatbagError as e:
                print(f"librehub: mouse auto-detect failed ({e}); "
                      "remapping disabled until restart", file=sys.stderr)
                return None
        if model:
            self.model = model
        try:
            return E.find_signal_device(model) if model else None
        except OSError:
            return None

    async def run(self) -> None:
        self.reload_config()
        dev_path = self._resolve_signal_device()
        tasks = [self.poll_focus(), self.watch_config(), self.serve_ipc()]
        if dev_path:
            tasks.append(self.engine.run(dev_path, on_detect=self._on_detect))
        else:
            print(f"librehub: no signal device for '{self.model}' found; "
                  "remapping disabled until mouse is present", file=sys.stderr)
        await asyncio.gather(*tasks, return_exceptions=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="librehub-daemon")
    ap.add_argument("--model", default=None,
                    help="device model substring to match; default: auto-detect")
    args = ap.parse_args(argv)
    engine = E.Engine()
    d = Daemon(cfg_path=C.config_path(), engine=engine,
               appid_fn=focus.current_appid, model=args.model)
    try:
        asyncio.run(d.run())
    except KeyboardInterrupt:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
