"""Regression test: importing appointment-backend/test_sms.py must be side-effect free.

The module previously printed Twilio credentials and sent an SMS at import time.
"""
import ast
import importlib
import os
import socket
import sys
import types
from unittest import mock

import pytest

BACKEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "appointment-backend")
)
SMS_PATH = os.path.join(BACKEND_DIR, "test_sms.py")
SENTINEL = "SENTINEL_SECRET_VALUE_9f3a"


@pytest.fixture
def twilio_spy(monkeypatch):
    """Inject a stub twilio.rest.Client (always, so the real one is never used)."""
    client_cls = mock.MagicMock(name="Client")
    twilio_mod = types.ModuleType("twilio")
    rest_mod = types.ModuleType("twilio.rest")
    rest_mod.Client = client_cls
    twilio_mod.rest = rest_mod
    monkeypatch.setitem(sys.modules, "twilio", twilio_mod)
    monkeypatch.setitem(sys.modules, "twilio.rest", rest_mod)
    return client_cls


@pytest.fixture
def fresh_import(monkeypatch):
    monkeypatch.syspath_prepend(BACKEND_DIR)
    sys.modules.pop("test_sms", None)
    yield lambda: importlib.import_module("test_sms")
    sys.modules.pop("test_sms", None)


def _forbid_network(monkeypatch):
    def boom(*args, **kwargs):
        raise AssertionError("network access attempted during import")

    monkeypatch.setattr(socket, "socket", boom)
    monkeypatch.setattr(socket, "create_connection", boom)


def test_import_has_no_side_effects(monkeypatch, capfd, twilio_spy, fresh_import):
    for name in ("TWILIO_SID", "TWILIO_AUTH", "TWILIO_NUMBER"):
        monkeypatch.setenv(name, SENTINEL)
    _forbid_network(monkeypatch)

    module = fresh_import()

    out, err = capfd.readouterr()
    assert out == ""
    assert err == ""
    assert SENTINEL not in out + err
    twilio_spy.assert_not_called()
    assert twilio_spy.return_value.messages.create.call_count == 0
    assert callable(module.main)


def test_import_prints_nothing_capsys(monkeypatch, capsys, twilio_spy, fresh_import):
    monkeypatch.setenv("TWILIO_SID", SENTINEL)
    monkeypatch.setenv("TWILIO_AUTH", SENTINEL)
    monkeypatch.setenv("TWILIO_NUMBER", SENTINEL)
    _forbid_network(monkeypatch)

    fresh_import()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert SENTINEL not in captured.out + captured.err


def test_source_has_only_imports_and_defs():
    with open(SMS_PATH, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef)):
            continue
        is_main_guard = (
            isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "__name__"
        )
        assert is_main_guard, f"unexpected top-level statement: {ast.dump(node)[:80]}"

    func_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    assert not [n for n in func_names if n.startswith("test_")]
    assert "main" in func_names
