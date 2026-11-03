"""Tests for PATCH /appointments/<id>/status input validation and behaviour.

Separate from test_mysql.py on purpose: that module connects to the DB at
import time. All DB, SMS and email calls are mocked here.
"""
from unittest.mock import MagicMock, patch

import pytest

import app as app_module


def _make_mock_conn(current_status, patient_name="Jane Doe", patient_phone="+15551234567",
                    patient_email="jane@example.com", appointment_time="2026-10-01 10:00:00",
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


def _send(client, body_kwargs, appointment_id=1, current_status="scheduled", row_exists=True,
          conn=None):
    """PATCH with the given client.patch kwargs; return (response, mocks)."""
    mock_conn = conn or _make_mock_conn(current_status, row_exists=row_exists)
    with patch.object(app_module, "get_db_connection", return_value=mock_conn) as get_conn, \
         patch.object(app_module, "send_sms", return_value=True) as sms, \
         patch.object(app_module, "send_email", return_value=None) as email:
        response = client.patch(f"/appointments/{appointment_id}/status", **body_kwargs)
    return response, {"conn": mock_conn, "get_conn": get_conn, "sms": sms, "email": email}


# ---------- validation failures (400, no DB access) ----------

def test_missing_status_key(client):
    r, m = _send(client, {"json": {"other": "x"}})
    assert r.status_code == 400
    assert r.get_json() == {"error": "Missing required field: status"}
    m["get_conn"].assert_not_called()


def test_empty_body(client):
    r, m = _send(client, {})
    assert r.status_code == 400
    assert r.get_json() == {"error": "Request body must be a JSON object"}
    m["get_conn"].assert_not_called()


def test_non_json_content_type(client):
    r, m = _send(client, {"data": "status=confirmed", "content_type": "text/plain"})
    assert r.status_code == 400
    m["get_conn"].assert_not_called()


def test_json_list_body(client):
    r, m = _send(client, {"json": ["confirmed"]})
    assert r.status_code == 400
    assert r.get_json() == {"error": "Request body must be a JSON object"}
    m["get_conn"].assert_not_called()


def test_null_body(client):
    r, m = _send(client, {"data": "null", "content_type": "application/json"})
    assert r.status_code == 400
    assert r.get_json() == {"error": "Request body must be a JSON object"}
    m["get_conn"].assert_not_called()


@pytest.mark.parametrize("bad", [5, ["confirmed"], {"a": 1}])
def test_status_wrong_type(client, bad):
    r, m = _send(client, {"json": {"status": bad}})
    assert r.status_code == 400
    assert r.get_json() == {"error": "status must be a string"}
    m["get_conn"].assert_not_called()


def test_unknown_status_string(client):
    r, m = _send(client, {"json": {"status": "bogus-value"}})
    body = r.get_json()
    assert r.status_code == 400
    assert body["error"] == "Invalid status"
    assert body["allowed"] == sorted(app_module.VALID_STATUSES)
    assert "bogus-value" not in r.get_data(as_text=True)
    m["get_conn"].assert_not_called()


def test_wrong_case_status_rejected(client):
    r, m = _send(client, {"json": {"status": "Confirmed"}})
    assert r.status_code == 400
    assert r.get_json()["error"] == "Invalid status"
    m["get_conn"].assert_not_called()


def test_non_integer_id(client):
    r, m = _send(client, {"json": {"status": "confirmed"}}, appointment_id="abc")
    assert r.status_code == 400
    assert r.get_json() == {"error": "Invalid appointment id"}
    m["get_conn"].assert_not_called()


def test_negative_id(client):
    r, m = _send(client, {"json": {"status": "confirmed"}}, appointment_id=-1)
    assert r.status_code == 400
    assert r.get_json() == {"error": "Invalid appointment id"}
    m["get_conn"].assert_not_called()


def test_zero_id(client):
    r, m = _send(client, {"json": {"status": "confirmed"}}, appointment_id=0)
    assert r.status_code == 400
    assert r.get_json() == {"error": "Invalid appointment id"}
    m["get_conn"].assert_not_called()


# ---------- DB-backed paths ----------

def test_appointment_not_found(client):
    r, m = _send(client, {"json": {"status": "confirmed"}}, row_exists=False)
    assert r.status_code == 404
    body = r.get_json()
    assert body["error"] == "Appointment not found"
    assert body["message"] == "Appointment not found"
    m["conn"].close.assert_called_once()
    m["conn"].cursor.return_value.close.assert_called_once()


@pytest.mark.parametrize("current,new", [
    (cur, new)
    for cur, targets in app_module.STATUS_TRANSITIONS.items()
    for new in sorted(targets)
])
def test_all_valid_transitions(client, current, new):
    r, m = _send(client, {"json": {"status": new}}, current_status=current)
    assert r.status_code == 200
    assert r.get_json() == {"message": "Status updated", "status": new}
    cursor = m["conn"].cursor.return_value
    update_calls = [c for c in cursor.execute.call_args_list if "UPDATE" in c.args[0]]
    assert len(update_calls) == 1
    assert update_calls[0].args[1] == (new, 1)
    m["conn"].commit.assert_called_once()
    m["sms"].assert_called_once()
    m["email"].assert_called_once()
    m["conn"].close.assert_called_once()


def test_illegal_non_terminal_transition_is_409(client):
    r, m = _send(client, {"json": {"status": "completed"}}, current_status="scheduled")
    assert r.status_code == 409
    body = r.get_json()
    assert body["error"] == "Cannot transition from scheduled to completed"
    assert body["current_status"] == "scheduled"
    assert body["allowed"] == sorted(app_module.STATUS_TRANSITIONS["scheduled"])
    cursor = m["conn"].cursor.return_value
    assert not [c for c in cursor.execute.call_args_list if "UPDATE" in c.args[0]]
    m["sms"].assert_not_called()
    m["conn"].close.assert_called_once()
    cursor.close.assert_called_once()


def test_same_status_is_200_without_notifications(client):
    r, m = _send(client, {"json": {"status": "scheduled"}}, current_status="scheduled")
    assert r.status_code == 200
    assert r.get_json() == {"message": "Status updated", "status": "scheduled"}
    m["sms"].assert_not_called()
    m["email"].assert_not_called()
    m["conn"].close.assert_called_once()


def test_exception_returns_500_and_closes_connection(client):
    conn = _make_mock_conn("scheduled")
    conn.cursor.return_value.execute.side_effect = RuntimeError("secret db detail")
    r, m = _send(client, {"json": {"status": "confirmed"}}, conn=conn)
    assert r.status_code == 500
    assert r.get_json() == {"error": "An unexpected error occurred"}
    assert "secret db detail" not in r.get_data(as_text=True)
    conn.close.assert_called_once()
    conn.cursor.return_value.close.assert_called_once()
