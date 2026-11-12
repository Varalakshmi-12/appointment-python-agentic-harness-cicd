from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector
from twilio.rest import Client
from dotenv import load_dotenv
import os
import re
from datetime import datetime, timezone
from werkzeug.exceptions import HTTPException

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(to, subject, body):
    """Send a plain-text email via Gmail's SMTP server.

    Args:
        to (str): Recipient email address.
        subject (str): Email subject line.
        body (str): Plain-text email body.

    Returns:
        None. Prints a confirmation message on success; raises whatever
        exception smtplib/socket raises on failure (e.g. auth or connection
        errors), which callers are expected to catch if they need to
        continue on failure.

    Note:
        Reads sender credentials from the EMAIL_USER and EMAIL_PASS
        environment variables.
    """
    msg = MIMEMultipart()
    msg['From'] = os.getenv("EMAIL_USER")
    msg['To'] = to
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
    server.sendmail(msg['From'], msg['To'], msg.as_string())
    server.quit()

    print("Email sent to:", to)


load_dotenv()

app = Flask(__name__)
CORS(app)


@app.errorhandler(404)
def handle_not_found(e):
    """Return JSON 400 for a malformed id on the status route only.

    A 404 on a path shaped like /appointments/<x>/status means <x> did not
    match <int:id> (non-integer or negative). Every other 404 is returned
    unchanged so other routes keep Flask's default behaviour.
    """
    parts = request.path.strip("/").split("/")
    if (request.method == "PATCH" and len(parts) == 3
            and parts[0] == "appointments" and parts[2] == "status"):
        return jsonify({"error": "Invalid appointment id"}), 400
    return e

VALID_STATUSES = {"scheduled", "confirmed", "completed", "cancelled", "no-show"}
MAX_CANCELLATION_REASON_LEN = 500

# Create-route (POST /appointments) validation limits.
MAX_NAME_LEN = 255
MAX_PHONE_LEN = 20
MAX_EMAIL_LEN = 255
MAX_PROVIDER_LEN = 255
_PHONE_RE = re.compile(r"^\+?[0-9]{7,19}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_CREATE_FORBIDDEN = {"id", "cancellation_reason"}
_INVALID_STATUS_MSG = "Invalid status"


def validate_appointment_create(data):
    """Validate and normalise the body of POST /appointments.

    Args:
        data (dict): Parsed JSON body.

    Returns:
        (clean, None) on success, where clean has exactly the keys
        patient_name, patient_phone, provider_name, patient_email, status
        (unknown input keys are dropped). (None, msg) on failure, where msg is
        a fixed string that never includes input values. When msg equals
        _INVALID_STATUS_MSG the route adds the "allowed" list.
    """
    if _CREATE_FORBIDDEN & set(data):
        return None, "Field not allowed on create"

    name = data.get("patient_name")
    if not isinstance(name, str):
        return None, "patient_name is required"
    name = name.strip()
    if not name:
        return None, "patient_name is required"
    if len(name) > MAX_NAME_LEN:
        return None, "patient_name is too long"

    phone = data.get("patient_phone")
    if phone is not None:
        if not isinstance(phone, str):
            return None, "patient_phone must be a string"
        phone = phone.strip() or None
        if phone is not None and not _PHONE_RE.match(phone):
            return None, "patient_phone is invalid"

    provider = data.get("provider_name")
    if provider is not None:
        if not isinstance(provider, str):
            return None, "provider_name must be a string"
        provider = provider.strip() or None
        if provider is not None and len(provider) > MAX_PROVIDER_LEN:
            return None, "provider_name is too long"

    email = data.get("patient_email")
    if not isinstance(email, str):
        return None, "patient_email is required"
    email = email.strip()
    if not email:
        return None, "patient_email is required"
    if len(email) > MAX_EMAIL_LEN:
        return None, "patient_email is too long"
    if not _EMAIL_RE.match(email):
        return None, "patient_email is invalid"

    status = data.get("status", "scheduled")
    if not isinstance(status, str) or status not in VALID_STATUSES:
        return None, _INVALID_STATUS_MSG

    return {
        "patient_name": name,
        "patient_phone": phone,
        "provider_name": provider,
        "patient_email": email,
        "status": status,
    }, None

# Legal status transitions for PATCH /appointments/<id>/status (decision-007).
# Resubmitting the current status is handled separately as an idempotent no-op.
# The empty sets below for "completed", "cancelled", and "no-show" are the
# terminal-state guard called for by decision-007: since none of these keys
# map to any reachable target, `status not in STATUS_TRANSITIONS.get(row["status"], set())`
# in update_appointment_status is true for any attempted transition out of a
# terminal state, so it is rejected with 409 before the UPDATE statement runs.
STATUS_TRANSITIONS = {
    "scheduled": {"confirmed", "cancelled", "no-show"},
    "confirmed": {"completed", "cancelled", "no-show"},
    "completed": set(),
    "cancelled": set(),
    "no-show":   set(),
}

# -----------------------------
# UTC time helpers
# -----------------------------
def parse_utc(value):
    """Parse an ISO 8601 timestamp with an offset into a naive UTC datetime.

    Args:
        value (str): ISO 8601 string with an explicit offset or a trailing
            "Z" (1 to 64 characters).

    Returns:
        datetime: Naive datetime (tzinfo None) in UTC, suitable for MySQL.

    Raises:
        ValueError: If value is not a str of length 1..64, cannot be parsed,
        or has no UTC offset.
    """
    if not isinstance(value, str) or not 1 <= len(value) <= 64:
        raise ValueError("appointment_time must be a string of 1 to 64 characters")
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("appointment_time must include a UTC offset")
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def to_iso_utc(dt):
    """Format a naive UTC datetime as an ISO 8601 string ending in "Z".

    Returns None if dt is None; any non-datetime value is returned unchanged.
    """
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    return dt

# -----------------------------
# Database Connection
# -----------------------------
def get_db_connection():
    """Open a new MySQL connection using credentials from the environment.

    Reads DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, and DB_NAME environment
    variables (typically loaded from a .env file via load_dotenv()).

    Returns:
        mysql.connector.connection.MySQLConnection: A new, open connection.
        Callers are responsible for closing it (and any cursors) when done.
    """
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

# -----------------------------
# SMS Function
# -----------------------------
def send_sms(to, message):
    """Send an SMS message via Twilio.

    Args:
        to (str): Recipient phone number in E.164 format (e.g. "+15551234567").
        message (str): SMS body text.

    Returns:
        bool: True if the message was submitted to Twilio successfully,
        False if an exception occurred (the exception is caught internally
        and logged rather than raised, so this call never breaks the caller).

    Note:
        Reads Twilio credentials/sender number from the TWILIO_SID,
        TWILIO_AUTH, and TWILIO_NUMBER environment variables.
    """
    try:
        client = Client(os.getenv("TWILIO_SID"), os.getenv("TWILIO_AUTH"))
        client.messages.create(
            body=message,
            from_=os.getenv("TWILIO_NUMBER"),
            to=to
        )
        print("SMS sent successfully")

        return True
    except Exception as e:
        print("SMS Error:", e)
        return False

# -----------------------------
# ROUTES
# -----------------------------
@app.route("/")
def home():
    """Root health-check route.

    Method: GET /
    Input: None.
    Returns: Plain-text string confirming the backend is running (200).
    """
    return "Appointment backend is running"

@app.route("/test")
def test():
    """Simple liveness check route.

    Method: GET /test
    Input: None.
    Returns: Plain-text "Test OK" (200).
    """
    return "Test OK"

@app.route('/test-sms')
def test_sms():
    """Manually trigger a test SMS to a hardcoded phone number.

    Method: GET /test-sms
    Input: None.
    Returns: Plain-text "SMS sent!" (200). Used only to verify Twilio
    configuration; not part of the appointment workflow.
    """
    send_sms("+15551234567", "Test message from you system!")
    return "SMS sent!"

@app.route('/test-email')
def test_email():
    """Manually trigger a test email to a hardcoded address.

    Method: GET /test-email
    Input: None.
    Returns: Plain-text "Email sent!" (200). Used only to verify SMTP
    configuration; not part of the appointment workflow.
    """
    send_email(
        "test@example.com",
        "Test Email",
        "This is a test email from your appointment backend."
    )
    return "Email sent!"


# -----------------------------
# CREATE Appointment
# -----------------------------
@app.route("/appointments", methods=["POST"])
def create_appointment():
    """Create a new appointment and notify the patient.

    Method: POST /appointments
    Input (JSON body): {
        "patient_name": str (required, trimmed, 1..255),
        "patient_phone": str (optional; absent, null or blank is stored as
            null; otherwise trimmed and must match an optional "+" followed
            by 7..19 digits),
        "provider_name": str (optional; absent, null or blank is stored as
            null; otherwise trimmed, max 255),
        "patient_email": str (required, trimmed, max 255, must look like
            local@domain.tld),
        "appointment_time": str (ISO 8601 with offset or "Z"),
        "status": str (optional, one of VALID_STATUSES, case-sensitive, no
            trimming; defaults to "scheduled")
    }
    Unknown keys are silently ignored and never reach SQL.
    Returns:
        201 with JSON {"id": <new appointment id>, "message": "Appointment created"}
        on success.
        400 with JSON {"error": <str>} for: a body that is not a JSON object;
        "id" or "cancellation_reason" present ("Field not allowed on create");
        a missing, non-string, blank or over-long patient_name or
        patient_email; a non-string or invalid patient_phone; a non-string or
        over-long provider_name; an invalid patient_email format; an unknown
        status (also includes "allowed": <sorted list>); or a missing or bad
        appointment_time ("Invalid appointment_time"). Raw input is never
        echoed. All validation runs before any DB access.
        500 with JSON {"error": <str>} if any step (DB insert, etc.) raises.

    Side effects: Inserts a row into the appointments table, then sends a
    confirmation SMS (only if a phone number was given) and a confirmation
    email to the patient. Email failures are caught and logged so they don't
    fail the request; SMS failures are handled inside send_sms itself.
    """
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Request body must be a JSON object"}), 400

        clean, error = validate_appointment_create(data)
        if error is not None:
            if error == _INVALID_STATUS_MSG:
                return jsonify({"error": error, "allowed": sorted(VALID_STATUSES)}), 400
            return jsonify({"error": error}), 400

        # Raises ValueError (handled below) on a missing or bad time.
        appointment_dt = parse_utc(data.get("appointment_time"))

        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            INSERT INTO appointments (patient_name, patient_phone, provider_name, patient_email, appointment_time, status)
            VALUES (%s, %s, %s, %s, %s, %s)
        """

        values = (
            clean["patient_name"],
            clean["patient_phone"],
            clean["provider_name"],
            clean["patient_email"],
            appointment_dt,
            clean["status"]
        )

        cursor.execute(sql, values)
        conn.commit()

        appointment_id = cursor.lastrowid

        # Send SMS AFTER DB commit (only when a phone number was given)
        if clean["patient_phone"] is not None:
            send_sms(
                clean["patient_phone"],
                f"Hello {clean['patient_name']}, your appointment is confirmed for {to_iso_utc(appointment_dt)} UTC."
            )

        # Send email AFTER DB commit (wrapped so a failure can't break the request)
        try:
            send_email(
                clean['patient_email'],
                "Appointment Confirmation",
                f"Hello {clean['patient_name']}, your appointment with {clean['provider_name']} is confirmed for {to_iso_utc(appointment_dt)} UTC."
            )
        except Exception as e:
            print("Email error:", e)

        cursor.close()
        conn.close()

        return jsonify({"id": appointment_id, "message": "Appointment created"}), 201

    except (KeyError, TypeError, AttributeError) as e:
        print("Create appointment error - invalid input:", e)
        return jsonify({"error": "Invalid request data"}), 400
    except ValueError:
        return jsonify({"error": "Invalid appointment_time"}), 400
    except Exception as e:
        print("Create appointment error:", e)
        return jsonify({"error": "An unexpected error occurred"}), 500

# -----------------------------
# READ All Appointments
# -----------------------------
@app.route("/appointments", methods=["GET"])
def get_appointments():
    """List all appointments, ordered by appointment time ascending.

    Method: GET /appointments
    Input: None.
    Returns:
        200 with a JSON array of appointment rows (each a dict of columns,
        including cancellation_reason, which is null unless one was given).
        500 with JSON {"error": <str>} if the query fails.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM appointments ORDER BY appointment_time ASC")
        rows = cursor.fetchall()

        cursor.close()
        conn.close()

        for row in rows:
            row["appointment_time"] = to_iso_utc(row["appointment_time"])

        return jsonify(rows), 200

    except Exception as e:
        print("Get appointments error:", e)
        return jsonify({"error": "An unexpected error occurred"}), 500

# -----------------------------
# READ Single Appointment
# -----------------------------
@app.route("/appointments/<int:id>", methods=["GET"])
def get_appointment(id):
    """Fetch a single appointment by its id.

    Method: GET /appointments/<id>
    Input: `id` (int) in the URL path.
    Returns:
        200 with a JSON object for the matching appointment row, if found
        (includes cancellation_reason, null unless one was given).
        404 with JSON {"message": "Appointment not found"} if no row matches.
        500 with JSON {"error": <str>} if the query fails.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT * FROM appointments WHERE id = %s", (id,))
        row = cursor.fetchone()

        cursor.close()
        conn.close()

        if row:
            row["appointment_time"] = to_iso_utc(row["appointment_time"])
            return jsonify(row), 200
        else:
            return jsonify({"message": "Appointment not found"}), 404

    except Exception as e:
        print("Get appointment error:", e)
        return jsonify({"error": "An unexpected error occurred"}), 500

# -----------------------------
# UPDATE Appointment
# -----------------------------
@app.route("/appointments/<int:id>", methods=["PUT"])
def update_appointment(id):
    """Update an existing appointment's fields and notify the patient.

    Method: PUT /appointments/<id>
    Input:
        `id` (int) in the URL path.
        JSON body: {
            "patient_name": str,
            "patient_phone": str,
            "provider_name": str,
            "patient_email": str,
            "appointment_time": str
        }
    Returns:
        200 with JSON {"message": "Appointment updated"} on success.
        404 with JSON {"message": "Appointment not found"} if `id` doesn't
        match any row (checked via the UPDATE's affected row count).
        500 with JSON {"error": <str>} if any step raises.

    Side effects: Updates the matching row, sends a confirmation email
    (failure is caught and logged, not raised), and if the row existed,
    sends an SMS confirming the updated time.
    """
    try:
        data = request.json

        appointment_dt = parse_utc(data["appointment_time"])

        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            UPDATE appointments
            SET patient_name=%s, patient_phone=%s, provider_name=%s, patient_email=%s, appointment_time=%s
            WHERE id=%s
        """

        values = (
            data["patient_name"],
            data["patient_phone"],
            data["provider_name"],
            data["patient_email"],
            appointment_dt,
            id
        )

        cursor.execute(sql, values)
        conn.commit()

        # Send email (wrapped so a failure can't break the request)
        try:
            send_email(
                data['patient_email'],
                "Appointment updated Confirmation",
                f"Hello {data['patient_name']}, your appointment with {data['provider_name']} is confirmed for {to_iso_utc(appointment_dt)} UTC."
            )
        except Exception as e:
            print("Email error:", e)

        updated = cursor.rowcount  # check BEFORE closing cursor

        cursor.close()
        conn.close()

        if updated == 0:
            return jsonify({"message": "Appointment not found"}), 404

        # Send SMS
        send_sms(
            data["patient_phone"],
            f"Hello {data['patient_name']}, your appointment has been updated to {to_iso_utc(appointment_dt)} UTC."
        )

        return jsonify({"message": "Appointment updated"}), 200

    except (KeyError, TypeError, AttributeError) as e:
        print("Update appointment error - invalid input:", e)
        return jsonify({"error": "Invalid request data"}), 400
    except ValueError:
        return jsonify({"error": "Invalid appointment_time"}), 400
    except Exception as e:
        print("Update appointment error:", e)
        return jsonify({"error": "An unexpected error occurred"}), 500

# -----------------------------
# UPDATE Appointment Status
# -----------------------------
@app.route("/appointments/<int:id>/status", methods=["PATCH"])
def update_appointment_status(id):
    """Change an appointment's status and notify the patient.

    Method: PATCH /appointments/<id>/status
    Input:
        `id` (int) in the URL path; must be >= 1. Non-integer or negative
        ids never match the route and get a JSON 400 from the 404 handler.
        JSON body: {"status": str}; status must exactly match one of
        VALID_STATUSES (case-sensitive, no trimming). Optional
        "cancellation_reason": str or null; trimmed, and empty or
        whitespace-only becomes None. Max 500 characters after trimming. A
        non-empty reason is only allowed when status is "cancelled"; a null
        or empty reason on any other status is accepted and ignored.
    Returns:
        200 with JSON {"message": "Status updated", "status": <str>} on success,
        including when the requested status equals the appointment's current
        status (treated as an idempotent no-op).
        400 with JSON {"error": <str>} for an invalid id, a body that is not
        a JSON object, a missing or non-string "status", or an unknown
        status. An unknown status also includes "allowed": <sorted list>.
        400 also covers a non-string "cancellation_reason", one over 500
        characters (includes "max_length": 500), or a reason given with a
        status other than "cancelled".
        The raw input is never echoed. Validation runs before any DB access.
        404 with JSON {"error": "Appointment not found", "message":
        "Appointment not found"} if `id` doesn't match any row ("message" is
        kept for backward compatibility).
        409 with JSON {"error": <str>, "current_status": <str>, "allowed":
        <sorted list>} if the requested status is not a legal transition from
        the appointment's current status (see STATUS_TRANSITIONS /
        decision-007).
        500 with JSON {"error": "An unexpected error occurred"} for unexpected
        errors (details are logged, not returned). werkzeug HTTPExceptions
        keep their own status code.

    Side effects: Updates only the status column (patient/time details are
    left untouched); on a real transition to "cancelled" it also stores
    cancellation_reason (re-cancelling is a no-op and never overwrites an
    existing reason). The reason is not included in the SMS or email. Then sends a status-specific SMS and email. Email
    failures are caught and logged rather than raised; SMS failures are
    handled inside send_sms itself. No notifications are sent for a
    same-status no-op, since nothing changed. The DB cursor and connection
    are closed on every path.
    """
    # Validate the request before any DB access.
    if id < 1:
        return jsonify({"error": "Invalid appointment id"}), 400

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object"}), 400
    if "status" not in data:
        return jsonify({"error": "Missing required field: status"}), 400
    status = data["status"]
    if not isinstance(status, str):
        return jsonify({"error": "status must be a string"}), 400
    if status not in VALID_STATUSES:
        return jsonify({"error": "Invalid status", "allowed": sorted(VALID_STATUSES)}), 400

    reason = data.get("cancellation_reason")
    if reason is not None:
        if not isinstance(reason, str):
            return jsonify({"error": "cancellation_reason must be a string"}), 400
        reason = reason.strip() or None
    if reason is not None:
        if len(reason) > MAX_CANCELLATION_REASON_LEN:
            return jsonify({
                "error": "cancellation_reason is too long",
                "max_length": MAX_CANCELLATION_REASON_LEN,
            }), 400
        if status != "cancelled":
            return jsonify({"error": "cancellation_reason is only allowed when status is cancelled"}), 400

    conn = None
    cursor = None
    try:
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute(
                "SELECT status, patient_name, patient_phone, patient_email, appointment_time FROM appointments WHERE id = %s",
                (id,)
            )
            row = cursor.fetchone()

            if not row:
                return jsonify({"error": "Appointment not found", "message": "Appointment not found"}), 404

            if status == row["status"]:
                return jsonify({"message": "Status updated", "status": status}), 200

            allowed = STATUS_TRANSITIONS.get(row["status"], set())
            if status not in allowed:
                return jsonify({
                    "error": f"Cannot transition from {row['status']} to {status}",
                    "current_status": row["status"],
                    "allowed": sorted(allowed),
                }), 409

            if status == "cancelled":
                cursor.execute(
                    "UPDATE appointments SET status=%s, cancellation_reason=%s WHERE id=%s",
                    (status, reason, id)
                )
            else:
                cursor.execute("UPDATE appointments SET status=%s WHERE id=%s", (status, id))
            conn.commit()
        finally:
            if cursor is not None:
                try:
                    cursor.close()
                except Exception as close_err:
                    print("Cursor close error:", close_err)
            if conn is not None:
                try:
                    conn.close()
                except Exception as close_err:
                    print("Connection close error:", close_err)

        time_text = f"{to_iso_utc(row['appointment_time'])} UTC"
        messages = {
            "scheduled": f"Hello {row['patient_name']}, your appointment has been scheduled for {time_text}.",
            "confirmed": f"Hello {row['patient_name']}, your appointment has been confirmed for {time_text}.",
            "cancelled": f"Hello {row['patient_name']}, your appointment has been cancelled.",
            "completed": f"Hello {row['patient_name']}, your appointment has been marked as completed.",
            "no-show": f"Hello {row['patient_name']}, you were marked as a no-show for your appointment on {time_text}.",
        }
        message = messages[status]

        send_sms(row["patient_phone"], message)

        try:
            send_email(row["patient_email"], "Appointment Status Update", message)
        except Exception as e:
            print("Email error:", e)

        return jsonify({"message": "Status updated", "status": status}), 200

    except HTTPException:
        raise
    except Exception as e:
        print("Update appointment status error:", e)
        return jsonify({"error": "An unexpected error occurred"}), 500

# -----------------------------
# DELETE Appointment
# -----------------------------
@app.route("/appointments/<int:id>", methods=["DELETE"])
def delete_appointment(id):
    """Delete an appointment by id and notify the patient of cancellation.

    Method: DELETE /appointments/<id>
    Input: `id` (int) in the URL path.
    Returns:
        200 with JSON {"message": "Appointment deleted"} on success.
        404 with JSON {"message": "Appointment not found"} if no row matches.
        500 with JSON {"error": <str>} if any step raises.

    Side effects: Looks up the patient's name/phone before deleting the row
    (needed for the notification), deletes the row, then sends a
    cancellation SMS.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Get patient info BEFORE deleting
        cursor.execute("SELECT patient_name, patient_phone FROM appointments WHERE id = %s", (id,))
        row = cursor.fetchone()

        if not row:
            return jsonify({"message": "Appointment not found"}), 404

        patient_name = row["patient_name"]
        patient_phone = row["patient_phone"]

        cursor.execute("DELETE FROM appointments WHERE id = %s", (id,))
        conn.commit()

        cursor.close()
        conn.close()

        # Send SMS
        send_sms(
            patient_phone,
            f"Hello {patient_name}, your appointment has been cancelled."
        )

        return jsonify({"message": "Appointment deleted"}), 200

    except Exception as e:
        print("Delete appointment error:", e)
        return jsonify({"error": "An unexpected error occurred"}), 500

# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
