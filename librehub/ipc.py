"""Minimal newline-delimited JSON protocol for GUI<->daemon IPC."""
from __future__ import annotations

import json
import os


def socket_path() -> str:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        return os.path.join(runtime, "librehub.sock")
    return f"/tmp/librehub-{os.getuid()}.sock"


def encode(msg: dict) -> bytes:
    return (json.dumps(msg) + "\n").encode("utf-8")


def decode(line: bytes) -> dict:
    try:
        return json.loads(line.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"bad IPC message: {e}") from e
