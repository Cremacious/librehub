import os
import pytest
from librehub import ipc


def test_encode_decode_roundtrip():
    msg = {"cmd": "status"}
    assert ipc.decode(ipc.encode(msg)) == msg


def test_encode_ends_with_newline():
    assert ipc.encode({"a": 1}).endswith(b"\n")


def test_decode_bad_json_raises():
    with pytest.raises(ValueError):
        ipc.decode(b"not json\n")


def test_socket_path_uses_runtime_dir(monkeypatch):
    monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")
    assert ipc.socket_path() == "/run/user/1000/librehub.sock"


def test_socket_path_fallback(monkeypatch):
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    assert ipc.socket_path() == f"/tmp/librehub-{os.getuid()}.sock"
