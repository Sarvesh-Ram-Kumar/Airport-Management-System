from flask import Blueprint, request, jsonify, session
import bcrypt
from db import get_connection

bank = Blueprint("bank", __name__)

# balance given to a newly opened bank account
OPENING_BALANCE = 50000.00

# wrong PINs allowed before the account is locked, and for how long
MAX_PIN_ATTEMPTS = 3
LOCK_MINUTES     = 15


def check_pin(pin, pin_hash):
    """True if the entered PIN matches the hash stored in bank_accounts."""
    return bool(pin_hash) and bcrypt.checkpw(
        str(pin or "").encode("utf-8"),
        pin_hash.encode("utf-8")
    )


def verify_pin(conn, cursor, account, pin):
    """
    Check the PIN against this account's row (needs pin_hash, failed_attempts
    and is_locked selected). Returns None if OK, otherwise an error response.
    """
    if account["is_locked"]:
        conn.rollback()
        return jsonify({
            "error": f"Account locked after {MAX_PIN_ATTEMPTS} wrong PINs. "
                     f"Try again in {LOCK_MINUTES} minutes"
        }), 423

    if check_pin(pin, account["pin_hash"]):
        if account["failed_attempts"]:
            cursor.execute(
                "UPDATE bank_accounts SET failed_attempts = 0 WHERE bank_id = %s",
                (account["bank_id"],)
            )
        return None

    # wrong PIN: undo anything done in this transaction, then record the
    # failed attempt in its own transaction so it isn't rolled back with it
    conn.rollback()
    attempts = account["failed_attempts"] + 1

    if attempts >= MAX_PIN_ATTEMPTS:
        cursor.execute("""
            UPDATE bank_accounts
            SET failed_attempts = 0,
                locked_until    = NOW() + INTERVAL %s MINUTE
            WHERE bank_id = %s
        """, (LOCK_MINUTES, account["bank_id"]))
        error = (f"Incorrect PIN. Account locked for {LOCK_MINUTES} minutes")
    else:
        cursor.execute(
            "UPDATE bank_accounts SET failed_attempts = %s WHERE bank_id = %s",
            (attempts, account["bank_id"])
        )
        error = f"Incorrect PIN. {MAX_PIN_ATTEMPTS - attempts} attempt(s) left"

    conn.commit()
    return jsonify({"error": error}), 401


# ─── PASSENGER: CREATE A BANK ACCOUNT ─────────────────────

@bank.route("/api/bank/create", methods=["POST"])
def create_account():
    if session.get("role") != "passenger":
        return jsonify({"error": "Unauthorized"}), 403

    pin = str(request.get_json().get("pin") or "").strip()
    if not (pin.isdigit() and 4 <= len(pin) <= 6):
        return jsonify({"error": "PIN must be 4-6 digits"}), 400

    pin_hash = bcrypt.hashpw(pin.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO bank_accounts (holder_name, pin_hash, balance)
            VALUES (%s, %s, %s)
        """, (session["name"], pin_hash, OPENING_BALANCE))
        conn.commit()
        bank_id = cursor.lastrowid
        return jsonify({
            "message": f"Bank account {bank_id} created with balance {OPENING_BALANCE:.2f}",
            "bank_id": bank_id
        }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()


# ─── PASSENGER: VIEW A BANK ACCOUNT (ID + PIN) ────────────

@bank.route("/api/bank/check", methods=["POST"])
def check_account():
    if session.get("role") != "passenger":
        return jsonify({"error": "Unauthorized"}), 403

    data    = request.get_json()
    bank_id = data.get("bank_id")

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT bank_id, holder_name, balance, pin_hash, failed_attempts,
               COALESCE(locked_until > NOW(), 0) AS is_locked
        FROM bank_accounts WHERE bank_id = %s
        FOR UPDATE
    """, (bank_id,))
    account = cursor.fetchone()

    if not account:
        conn.rollback()
        cursor.close()
        conn.close()
        return jsonify({"error": "Bank ID not found", "bank_not_found": True}), 404

    error = verify_pin(conn, cursor, account, data.get("pin"))
    if error:
        cursor.close()
        conn.close()
        return error
    conn.commit()

    for key in ("pin_hash", "failed_attempts", "is_locked"):
        account.pop(key)

    cursor.execute("""
        SELECT t.txn_id, t.booking_id, t.amount, t.txn_type, t.created_at,
               f.flight_no, b.seat_no
        FROM bank_transactions t
        JOIN bookings b ON t.booking_id = b.booking_id
        JOIN flights f  ON b.flight_id  = f.flight_id
        WHERE t.bank_id = %s
        ORDER BY t.created_at DESC, t.txn_id DESC
    """, (bank_id,))
    transactions = cursor.fetchall()
    cursor.close()
    conn.close()

    account["balance"] = float(account["balance"])
    for t in transactions:
        t["amount"]     = float(t["amount"])
        t["created_at"] = str(t["created_at"])
    account["transactions"] = transactions

    return jsonify(account), 200
