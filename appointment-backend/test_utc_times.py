"""Tests for UTC-at-rest appointment times.

All DB, SMS and email calls are mocked; no database or network is used.
"""
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

import app as app_module
from app import parse_utc, to_iso_utc

BODY = {
    "patient_name": "Jane Doe",
    "patient_phone": "+15551234567",
    "provider_name": "Dr. Smith",
    "patient_email": "jane@example.com",
}


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as test_client:
        yield test_client


def _mock_conn(rows=None, row=None, rowcount=1):
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    cursor.fetchone.return_value = row
    cursor.rowcount = rowcount
    cursor.lastrowid = 7
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


def _call(client, method, path, conn, **kwargs):
    with patch.object(app_module, "get_db_connection", return_value=conn), \
         patch.object(app_module, "send_sms", return_value=True) as sms, \
         patch.object(app_module, "send_email", return_value=None) as email:
        response = getattr(client, method)(path, **kwargs)
    return response, sms, email


# ---------- parse_utc ----------

def test_parse_utc_converts_offset_to_utc():
    assert parse_utc("2026-10-01T10:00:00-05:00") == datetime(2026, 10, 1, 15, 0)


def test_parse_utc_z_unchanged():
    assert parse_utc("2026-10-01T10:00:00Z") == datetime(2026, 10, 1, 10, 0)


def test_parse_utc_dst_boundary():
    # US DST ends 2026-11-01 at 02:00 local. 01:30-05:00 (CDT) and 01:30-06:00
    # (CST) are the same wall time but different instants, one hour apart.
    assert parse_utc("2026-11-01T01:30:00-05:00") == datetime(2026, 11, 1, 6, 30)
    assert parse_utc("2026-11-01T01:30:00-06:00") == datetime(2026, 11, 1, 7, 30)


@pytest.mark.parametrize("bad", [
    "2026-10-01T10:00:00",  # naive
    "not-a-date",
    "",
    None,
    12345,
    ["2026-10-01T10:00:00Z"],
    "2026-10-01T10:00:00Z" + " " * 64,  # over-long
])
def test_parse_utc_rejects(bad):
    with pytest.raises(ValueError):
        parse_utc(bad)


def test_parse_utc_result_is_naive():
    assert parse_utc("2026-10-01T10:00:00+02:00").tzinfo is None
    assert parse_utc("2026-10-01T10:00:00Z").tzinfo is None


def test_to_iso_utc():
    assert to_iso_utc(None) is None
    assert to_iso_utc(datetime(2026, 10, 1, 15, 0)) == "2026-10-01T15:00:00Z"


# ---------- routes ----------

def test_post_stores_naive_utc(client):
    conn, cursor = _mock_conn()
    r, sms, email = _call(client, "post", "/appointments", conn,
                          json={**BODY, "appointment_time": "2026-10-01T10:00:00-05:00"})
    assert r.status_code == 201
    values = cursor.execute.call_args.args[1]
    stored = values[4]
    assert stored == datetime(2026, 10, 1, 15, 0)
    assert stored.tzinfo is None
    assert "2026-10-01T15:00:00Z UTC" in sms.call_args.args[1]
    assert "2026-10-01T15:00:00Z UTC" in email.call_args.args[2]


def test_put_stores_naive_utc(client):
    conn, cursor = _mock_conn()
    r, sms, email = _call(client, "put", "/appointments/3", conn,
                          json={**BODY, "appointment_time": "2026-10-01T10:00:00-05:00"})
    assert r.status_code == 200
    values = cursor.execute.call_args.args[1]
    assert values[4] == datetime(2026, 10, 1, 15, 0)
    assert values[4].tzinfo is None
    assert values[5] == 3
    assert "2026-10-01T15:00:00Z UTC" in sms.call_args.args[1]


@pytest.mark.parametrize("method,path", [("post", "/appointments"), ("put", "/appointments/3")])
@pytest.mark.parametrize("bad", ["SECRET-garbage-input", "2026-10-01T10:00:00", "", None, 5])
def test_bad_time_returns_400(client, method, path, bad):
    conn, cursor = _mock_conn()
    r, sms, email = _call(client, method, path, conn, json={**BODY, "appointment_time": bad})
    assert r.status_code == 400
    assert r.get_json() == {"error": "Invalid appointment_time"}
    assert "SECRET-garbage-input" not in r.get_data(as_text=True)
    cursor.execute.assert_not_called()
    sms.assert_not_called()
    email.assert_not_called()


def test_get_list_serializes_z(client):
    rows = [{"id": 1, "appointment_time": datetime(2026, 10, 1, 15, 0)},
            {"id": 2, "appointment_time": None}]
    conn, _ = _mock_conn(rows=rows)
    r, _, _ = _call(client, "get", "/appointments", conn)
    body = r.get_json()
    assert r.status_code == 200
    assert body[0]["appointment_time"] == "2026-10-01T15:00:00Z"
    assert body[0]["appointment_time"].endswith("Z")
    assert body[1]["appointment_time"] is None


def test_get_single_serializes_z(client):
    conn, _ = _mock_conn(row={"id": 1, "appointment_time": datetime(2026, 10, 1, 15, 0)})
    r, _, _ = _call(client, "get", "/appointments/1", conn)
    assert r.status_code == 200
    assert r.get_json()["appointment_time"].endswith("Z")


def test_round_trip_same_instant(client):
    original = "2026-10-01T10:00:00-05:00"
    conn, cursor = _mock_conn()
    r, _, _ = _call(client, "post", "/appointments", conn,
                    json={**BODY, "appointment_time": original})
    assert r.status_code == 201
    stored = cursor.execute.call_args.args[1][4]

    conn2, _ = _mock_conn(row={"id": 7, "appointment_time": stored})
    r2, _, _ = _call(client, "get", "/appointments/7", conn2)
    served = r2.get_json()["appointment_time"]

    expected = datetime.fromisoformat(original).astimezone(timezone.utc)
    assert datetime.fromisoformat(served.replace("Z", "+00:00")) == expected
