"""Tests for the optional cancellation_reason on PATCH /appointments/<id>/status.

All DB, SMS and email calls are mocked; no network and no database.
"""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

import app as app_module

SENTINEL = "ZQX-SENTINEL-7731"


def _make_mock_conn(current_status, patient_name="Jane Doe", patient_phone="+15551234567",
                    patient_email="jane@example.com", appointment_time=datetime(2026, 10, 1, 10, 0, 0),
                    row_exists=True):
    """Mock DB connection whose cursor returns one appointment row (or None)."""
    mock_cursor = MagicMock()
    if row_exists:
        mock_cursor.fetchone.return_value = {
            "status": current_status,
            "patient_name": patient_name,
            "patient_phone": patient_phone,
            "patient_email": patient_email,
            "appointment_time": appointment_time,
        }
    else:
        mock_cursor.fetchone.return_value = None
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    return mock_conn


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as test_client:
        yield test_client


def _send(client, body, appointment_id=1, current_status="scheduled"):
    """PATCH the status route with a JSON body; return (response, mocks)."""
    mock_conn = _make_mock_conn(current_status)
    with patch.object(app_module, "get_db_connection", return_value=mock_conn) as get_conn, \
         patch.object(app_module, "send_sms", return_value=True) as sms, \
         patch.object(app_module, "send_email", return_value=None) as email:
        response = client.patch(f"/appointments/{appointment_id}/status", json=body)
    return response, {"conn": mock_conn, "get_conn": get_conn, "sms": sms, "email": email}


def _updates(mocks):
    cursor = mocks["conn"].cursor.return_value
    return [c for c in cursor.execute.call_args_list if "UPDATE" in c.args[0]]


# ---------- persistence on cancel ----------

def test_cancel_with_reason(client):
    r, m = _send(client, {"status": "cancelled", "cancellation_reason": "Patient moved"})
    assert r.status_code == 200
    updates = _updates(m)
    assert len(updates) == 1
    assert updates[0].args[1] == ("cancelled", "Patient moved", 1)
    assert "cancellation_reason" in updates[0].args[0]


def test_cancel_without_reason_stores_none(client):
    r, m = _send(client, {"status": "cancelled"})
    assert r.status_code == 200
    assert _updates(m)[0].args[1] == ("cancelled", None, 1)


def test_whitespace_only_reason_stored_as_none(client):
    r, m = _send(client, {"status": "cancelled", "cancellation_reason": "   \t\n "})
    assert r.status_code == 200
    assert _updates(m)[0].args[1] == ("cancelled", None, 1)


def test_reason_is_trimmed(client):
    r, m = _send(client, {"status": "cancelled", "cancellation_reason": "  Too far  "})
    assert r.status_code == 200
    assert _updates(m)[0].args[1] == ("cancelled", "Too far", 1)


def test_exactly_500_chars_ok(client):
    reason = "a" * 500
    r, m = _send(client, {"status": "cancelled", "cancellation_reason": reason})
    assert r.status_code == 200
    assert _updates(m)[0].args[1] == ("cancelled", reason, 1)


# ---------- validation failures (400, no DB access) ----------

def test_501_chars_rejected(client):
    r, m = _send(client, {"status": "cancelled", "cancellation_reason": "a" * 501})
    assert r.status_code == 400
    assert r.get_json() == {"error": "cancellation_reason is too long", "max_length": 500}
    m["get_conn"].assert_not_called()


@pytest.mark.parametrize("bad", [123, [SENTINEL], {"k": SENTINEL}])
def test_non_string_reason_rejected(client, bad):
    r, m = _send(client, {"status": "cancelled", "cancellation_reason": bad})
    assert r.status_code == 400
    assert r.get_json() == {"error": "cancellation_reason must be a string"}
    assert SENTINEL not in r.get_data(as_text=True)
    m["get_conn"].assert_not_called()


def test_reason_with_non_cancel_status_rejected(client):
    r, m = _send(client, {"status": "confirmed", "cancellation_reason": "nope"})
    assert r.status_code == 400
    assert r.get_json() == {"error": "cancellation_reason is only allowed when status is cancelled"}
    m["get_conn"].assert_not_called()


def test_null_reason_with_non_cancel_status_uses_original_update(client):
    r, m = _send(client, {"status": "confirmed", "cancellation_reason": None})
    assert r.status_code == 200
    updates = _updates(m)
    assert len(updates) == 1
    assert updates[0].args[0] == "UPDATE appointments SET status=%s WHERE id=%s"
    assert updates[0].args[1] == ("confirmed", 1)


def test_error_responses_do_not_echo_input(client):
    bodies = [
        {"status": "cancelled", "cancellation_reason": SENTINEL + "a" * 600},
        {"status": "confirmed", "cancellation_reason": SENTINEL},
        {"status": "cancelled", "cancellation_reason": [SENTINEL]},
        {"status": "cancelled", "cancellation_reason": {"k": SENTINEL}},
    ]
    for body in bodies:
        r, m = _send(client, body)
        assert r.status_code == 400
        assert SENTINEL not in r.get_data(as_text=True)
        m["get_conn"].assert_not_called()


# ---------- transition guard and idempotency ----------

def test_completed_to_cancelled_is_409_without_update(client):
    r, m = _send(client, {"status": "cancelled", "cancellation_reason": "late"},
                 current_status="completed")
    assert r.status_code == 409
    assert _updates(m) == []
    m["sms"].assert_not_called()


def test_recancel_is_noop_and_keeps_reason(client):
    r, m = _send(client, {"status": "cancelled", "cancellation_reason": "new reason"},
                 current_status="cancelled")
    assert r.status_code == 200
    assert _updates(m) == []
    m["conn"].commit.assert_not_called()
    m["sms"].assert_not_called()
    m["email"].assert_not_called()


# ---------- notifications unchanged ----------

def test_notifications_do_not_include_reason(client):
    r, m = _send(client, {"status": "cancelled", "cancellation_reason": SENTINEL})
    assert r.status_code == 200
    expected = "Hello Jane Doe, your appointment has been cancelled."
    m["sms"].assert_called_once_with("+15551234567", expected)
    m["email"].assert_called_once_with("jane@example.com", "Appointment Status Update", expected)
    assert SENTINEL not in repr(m["sms"].call_args)
    assert SENTINEL not in repr(m["email"].call_args)


# ---------- GET routes return the column ----------

def _get_mock_conn(fetchone=None, fetchall=None):
    cursor = MagicMock()
    cursor.fetchone.return_value = fetchone
    cursor.fetchall.return_value = fetchall
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn


def _row(**overrides):
    row = {
        "id": 1,
        "patient_name": "Jane Doe",
        "patient_phone": "+15551234567",
        "provider_name": "Dr. Who",
        "patient_email": "jane@example.com",
        "appointment_time": datetime(2026, 10, 1, 10, 0, 0),
        "status": "cancelled",
        "cancellation_reason": "Patient moved",
    }
    row.update(overrides)
    return row


def test_get_single_returns_cancellation_reason(client):
    conn = _get_mock_conn(fetchone=_row())
    with patch.object(app_module, "get_db_connection", return_value=conn):
        r = client.get("/appointments/1")
    assert r.status_code == 200
    body = r.get_json()
    assert "cancellation_reason" in body
    assert body["cancellation_reason"] == "Patient moved"


def test_get_list_returns_cancellation_reason(client):
    conn = _get_mock_conn(fetchall=[_row(), _row(id=2, status="scheduled", cancellation_reason=None)])
    with patch.object(app_module, "get_db_connection", return_value=conn):
        r = client.get("/appointments")
    assert r.status_code == 200
    body = r.get_json()
    assert all("cancellation_reason" in row for row in body)
    assert body[0]["cancellation_reason"] == "Patient moved"
    assert body[1]["cancellation_reason"] is None
