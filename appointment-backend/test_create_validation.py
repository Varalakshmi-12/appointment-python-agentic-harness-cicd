"""Tests for input validation on POST /appointments.

All DB, SMS and email calls are mocked; no database or network is used.
"""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

import app as app_module

SECRET = "SECRET-marker-123"

GOOD = {
    "patient_name": "Jane Doe",
    "patient_phone": "+15551234567",
    "provider_name": "Dr. Smith",
    "patient_email": "jane@example.com",
    "appointment_time": "2026-10-01T10:00:00Z",
}


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as test_client:
        yield test_client


def _post(client, **kwargs):
    """POST /appointments with mocks. Returns (response, get_conn, cursor, sms, email)."""
    cursor = MagicMock()
    cursor.lastrowid = 7
    conn = MagicMock()
    conn.cursor.return_value = cursor
    with patch.object(app_module, "get_db_connection", return_value=conn) as get_conn, \
         patch.object(app_module, "send_sms", return_value=True) as sms, \
         patch.object(app_module, "send_email", return_value=None) as email:
        response = client.post("/appointments", **kwargs)
    return response, get_conn, cursor, sms, email


def _assert_rejected(result, expected_json):
    r, get_conn, cursor, sms, email = result
    assert r.status_code == 400
    assert r.get_json() == expected_json
    get_conn.assert_not_called()
    cursor.execute.assert_not_called()
    sms.assert_not_called()
    email.assert_not_called()


def _values(result):
    return result[2].execute.call_args.args[1]


# ---------- happy path ----------

def test_happy_path_trims_values(client):
    body = {
        **GOOD,
        "patient_name": "  Jane Doe  ",
        "patient_phone": " +15551234567 ",
        "provider_name": "  Dr. Smith ",
        "patient_email": "  jane@example.com ",
    }
    result = _post(client, json=body)
    r, _, _, sms, email = result
    assert r.status_code == 201
    assert r.get_json() == {"id": 7, "message": "Appointment created"}
    assert _values(result) == (
        "Jane Doe", "+15551234567", "Dr. Smith", "jane@example.com",
        datetime(2026, 10, 1, 10, 0), "scheduled",
    )
    assert sms.call_args.args[0] == "+15551234567"
    assert "Jane Doe" in sms.call_args.args[1]
    assert email.call_args.args[0] == "jane@example.com"
    assert "Dr. Smith" in email.call_args.args[2]


def test_status_defaults_to_scheduled(client):
    result = _post(client, json=GOOD)
    assert result[0].status_code == 201
    assert _values(result)[5] == "scheduled"


def test_valid_status_accepted(client):
    result = _post(client, json={**GOOD, "status": "confirmed"})
    assert result[0].status_code == 201
    assert _values(result)[5] == "confirmed"


# ---------- required fields ----------

@pytest.mark.parametrize("field", ["patient_name", "patient_email"])
@pytest.mark.parametrize("mode", ["missing", "empty", "blank", "none", "int", "list"])
def test_required_field_rejected(client, field, mode):
    body = dict(GOOD)
    if mode == "missing":
        del body[field]
    else:
        body[field] = {"empty": "", "blank": "   ", "none": None, "int": 5, "list": [SECRET]}[mode]
    result = _post(client, json=body)
    _assert_rejected(result, {"error": f"{field} is required"})
    assert SECRET not in result[0].get_data(as_text=True)


# ---------- optional phone and provider ----------

@pytest.mark.parametrize("field", ["patient_phone", "provider_name"])
@pytest.mark.parametrize("mode", ["absent", "none", "empty", "blank"])
def test_optional_field_becomes_none(client, field, mode):
    body = dict(GOOD)
    if mode == "absent":
        del body[field]
    else:
        body[field] = {"none": None, "empty": "", "blank": "   "}[mode]
    result = _post(client, json=body)
    assert result[0].status_code == 201
    idx = 1 if field == "patient_phone" else 2
    assert _values(result)[idx] is None


def test_no_phone_skips_sms_but_sends_email(client):
    result = _post(client, json={**GOOD, "patient_phone": ""})
    r, _, _, sms, email = result
    assert r.status_code == 201
    sms.assert_not_called()
    email.assert_called_once()


# ---------- lengths ----------

@pytest.mark.parametrize("field,make", [
    ("patient_name", lambda n: "a" * n),
    ("provider_name", lambda n: "a" * n),
    ("patient_email", lambda n: "a" * (n - len("@example.com")) + "@example.com"),
])
def test_length_limits(client, field, make):
    result = _post(client, json={**GOOD, field: make(256)})
    _assert_rejected(result, {"error": f"{field} is too long"})

    result = _post(client, json={**GOOD, field: make(255)})
    assert result[0].status_code == 201


def test_phone_20_chars_ok(client):
    phone = "+" + "1" * 19
    assert len(phone) == 20
    result = _post(client, json={**GOOD, "patient_phone": phone})
    assert result[0].status_code == 201
    assert _values(result)[1] == phone


def test_phone_21_chars_rejected(client):
    phone = "+" + "1" * 20
    assert len(phone) == 21
    _assert_rejected(_post(client, json={**GOOD, "patient_phone": phone}),
                     {"error": "patient_phone is invalid"})


# ---------- formats and types ----------

@pytest.mark.parametrize("phone", ["12345", "abc1234567", "+1555-123-4567", "1+5551234567", SECRET])
def test_bad_phone_format(client, phone):
    result = _post(client, json={**GOOD, "patient_phone": phone})
    _assert_rejected(result, {"error": "patient_phone is invalid"})
    assert SECRET not in result[0].get_data(as_text=True)


@pytest.mark.parametrize("email", ["plain", "a@b", "a@@b.com", "a b@c.com", "@c.com", f"{SECRET}"])
def test_bad_email_format(client, email):
    result = _post(client, json={**GOOD, "patient_email": email})
    _assert_rejected(result, {"error": "patient_email is invalid"})
    assert SECRET not in result[0].get_data(as_text=True)


@pytest.mark.parametrize("field", ["patient_phone", "provider_name"])
@pytest.mark.parametrize("value", [5, True, [SECRET], {"k": SECRET}])
def test_non_str_optional_rejected(client, field, value):
    result = _post(client, json={**GOOD, field: value})
    _assert_rejected(result, {"error": f"{field} must be a string"})
    assert SECRET not in result[0].get_data(as_text=True)


@pytest.mark.parametrize("status", [SECRET, "Scheduled", " scheduled", "", None, 5, [SECRET]])
def test_invalid_status(client, status):
    result = _post(client, json={**GOOD, "status": status})
    _assert_rejected(result, {"error": "Invalid status",
                              "allowed": sorted(app_module.VALID_STATUSES)})
    assert SECRET not in result[0].get_data(as_text=True)


# ---------- forbidden and unknown keys ----------

@pytest.mark.parametrize("key", ["id", "cancellation_reason"])
def test_forbidden_keys(client, key):
    result = _post(client, json={**GOOD, key: SECRET})
    _assert_rejected(result, {"error": "Field not allowed on create"})
    assert SECRET not in result[0].get_data(as_text=True)


def test_unknown_key_ignored_and_not_in_sql(client):
    baseline = _post(client, json=GOOD)
    result = _post(client, json={**GOOD, "evil": SECRET, "is_admin": True})
    assert result[0].status_code == 201
    values = _values(result)
    assert len(values) == len(_values(baseline)) == 6
    assert SECRET not in repr(result[2].execute.call_args)
    assert SECRET not in result[0].get_data(as_text=True)


# ---------- body shape ----------

@pytest.mark.parametrize("kwargs", [
    {"json": [GOOD]},
    {"json": "text"},
    {"json": None},
    {"data": "not json at all", "content_type": "text/plain"},
    {"data": "{broken", "content_type": "application/json"},
    {},
])
def test_non_object_body_rejected(client, kwargs):
    _assert_rejected(_post(client, **kwargs),
                     {"error": "Request body must be a JSON object"})


# ---------- appointment_time ----------

@pytest.mark.parametrize("bad", [SECRET, "2026-10-01T10:00:00", "", None, 5])
def test_bad_time_still_invalid_appointment_time(client, bad):
    result = _post(client, json={**GOOD, "appointment_time": bad})
    _assert_rejected(result, {"error": "Invalid appointment_time"})
    assert SECRET not in result[0].get_data(as_text=True)


def test_missing_time_rejected(client):
    body = dict(GOOD)
    del body["appointment_time"]
    _assert_rejected(_post(client, json=body), {"error": "Invalid appointment_time"})


def test_field_errors_checked_before_time(client):
    result = _post(client, json={**GOOD, "patient_name": "", "appointment_time": "bad"})
    _assert_rejected(result, {"error": "patient_name is required"})


# ---------- frontend payload ----------

def test_frontend_payload_shape(client):
    body = {
        "patient_name": "Jane Doe",
        "patient_phone": "",
        "provider_name": "",
        "patient_email": "jane@example.com",
        "appointment_time": "2026-10-01T15:00:00.000Z",
    }
    result = _post(client, json=body)
    assert result[0].status_code == 201
    values = _values(result)
    assert values[1] is None and values[2] is None
    assert values[4] == datetime(2026, 10, 1, 15, 0)
    assert values[5] == "scheduled"
    result[3].assert_not_called()
    result[4].assert_called_once()


# ---------- SECRET never echoed ----------

@pytest.mark.parametrize("field", [
    "patient_name", "patient_phone", "provider_name", "patient_email",
    "status", "appointment_time", "id", "cancellation_reason",
])
def test_secret_never_in_response(client, field):
    value = SECRET * 30 if field in ("patient_name", "provider_name") else SECRET
    result = _post(client, json={**GOOD, field: value})
    r = result[0]
    assert r.status_code == 400
    assert SECRET not in r.get_data(as_text=True)
    result[1].assert_not_called()
