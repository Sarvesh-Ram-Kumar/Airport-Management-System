from flask import Flask, Blueprint, request, jsonify, render_template, session
from flask_cors import CORS
import bcrypt
from db import get_connection
from routes.bank import verify_pin

bookings = Blueprint("bookings", __name__)

# ─── STAFF: VIEW ALL BOOKINGS ─────────────────────────────

@bookings.route("/api/bookings/all", methods=["GET"])
def all_bookings():
    if session.get("role") != "staff":
        return jsonify({"error": "Unauthorized"}), 403

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT b.booking_id, b.seat_no, b.status, b.booked_at, b.amount_paid,
               u.name AS passenger_name, u.username,
               f.flight_no, f.origin, f.destination, 
               f.flight_date, f.flight_time
        FROM bookings b
        JOIN users u ON b.user_id = u.id
        JOIN flights f ON b.flight_id = f.flight_id
        ORDER BY b.booked_at DESC
    """)
    bookings = cursor.fetchall()
    cursor.close()
    conn.close()

    for b in bookings:
        b["flight_date"] = str(b["flight_date"])
        b["flight_time"] = str(b["flight_time"])
        b["booked_at"]   = str(b["booked_at"])
        b["amount_paid"] = float(b["amount_paid"])

    return jsonify(bookings), 200




# ─── PASSENGER: BOOK A SEAT ───────────────────────────────

@bookings.route("/api/bookings/book", methods=["POST"])
def book_seat():
    if session.get("role") != "passenger":
        return jsonify({"error": "Unauthorized"}), 403

    data      = request.get_json()
    flight_id = data["flight_id"]
    seat_no   = data["seat_no"]
    bank_id   = data.get("bank_id")
    bank_pin  = data.get("bank_pin")
    user_id   = session["user_id"]

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        # start transaction
        conn.start_transaction()

        # lock the flight row and check capacity
        cursor.execute("""
            SELECT capacity, price,
                   (SELECT COUNT(*) FROM bookings
                    WHERE flight_id = %s AND status = 'confirmed') AS booked
            FROM flights
            WHERE flight_id = %s AND status = 'approved'
            FOR UPDATE
        """, (flight_id, flight_id))

        flight = cursor.fetchone()

        if not flight:
            conn.rollback()
            return jsonify({"error": "Flight not found or not approved"}), 404

        if flight["booked"] >= flight["capacity"]:
            conn.rollback()
            return jsonify({"error": "Flight is fully booked"}), 400

        cursor.execute("""
            SELECT booking_id FROM bookings
            WHERE flight_id = %s AND seat_no = %s AND status = 'confirmed'
        """, (flight_id, seat_no))
        if cursor.fetchone():
            conn.rollback()
            return jsonify({"error": f"Seat {seat_no} is already taken"}), 400

        # lock the paying bank account and check funds
        cursor.execute("""
            SELECT bank_id, balance, pin_hash, failed_attempts,
                   COALESCE(locked_until > NOW(), 0) AS is_locked
            FROM bank_accounts
            WHERE bank_id = %s
            FOR UPDATE
        """, (bank_id,))
        account = cursor.fetchone()

        if not account:
            conn.rollback()
            # frontend uses this flag to offer creating a new account
            return jsonify({"error": "Bank ID not found", "bank_not_found": True}), 404

        # authorise the payment with this account's PIN (locks after repeated misses)
        error = verify_pin(conn, cursor, account, bank_pin)
        if error:
            return error

        price = flight["price"]
        if account["balance"] < price:
            conn.rollback()
            return jsonify({"error": "Insufficient bank balance"}), 400

        # insert booking, debit account and log payment as one unit
        cursor.execute("""
            INSERT INTO bookings (user_id, flight_id, seat_no, status, amount_paid)
            VALUES (%s, %s, %s, 'confirmed', %s)
        """, (user_id, flight_id, seat_no, price))
        booking_id = cursor.lastrowid

        cursor.execute("""
            UPDATE bank_accounts SET balance = balance - %s
            WHERE bank_id = %s
        """, (price, account["bank_id"]))

        cursor.execute("""
            INSERT INTO bank_transactions (bank_id, booking_id, amount, txn_type)
            VALUES (%s, %s, %s, 'payment')
        """, (account["bank_id"], booking_id, price))

        conn.commit()
        return jsonify({
            "message": f"Seat {seat_no} booked successfully. Paid {price:.2f}"
        }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()


# ─── PASSENGER: VIEW OWN BOOKINGS ─────────────────────────

@bookings.route("/api/bookings/mine", methods=["GET"])
def my_bookings():
    if session.get("role") != "passenger":
        return jsonify({"error": "Unauthorized"}), 403

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT b.booking_id, b.seat_no, b.status, b.booked_at, b.amount_paid,
               f.flight_no, f.origin, f.destination,
               f.flight_date, f.flight_time, f.gate,
               a.airline_name, t.bank_id
        FROM bookings b
        JOIN flights f ON b.flight_id = f.flight_id
        JOIN airliner_details a ON f.airliner_id = a.airliner_id
        LEFT JOIN bank_transactions t ON t.booking_id = b.booking_id
                                     AND t.txn_type = 'payment'
        WHERE b.user_id = %s
        ORDER BY f.flight_date DESC
    """, (session["user_id"],))
    bookings = cursor.fetchall()
    cursor.close()
    conn.close()

    for b in bookings:
        b["flight_date"] = str(b["flight_date"])
        b["flight_time"] = str(b["flight_time"])
        b["booked_at"]   = str(b["booked_at"])
        b["amount_paid"] = float(b["amount_paid"])

    return jsonify(bookings), 200


# ─── PASSENGER: CANCEL A BOOKING ──────────────────────────

@bookings.route("/api/bookings/cancel", methods=["POST"])
def cancel_booking():
    if session.get("role") != "passenger":
        return jsonify({"error": "Unauthorized"}), 403

    data       = request.get_json()
    booking_id = data["booking_id"]

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        conn.start_transaction()

        # lock the booking; must belong to this passenger and still be confirmed
        cursor.execute("""
            SELECT booking_id FROM bookings
            WHERE booking_id = %s AND user_id = %s AND status = 'confirmed'
            FOR UPDATE
        """, (booking_id, session["user_id"]))
        if not cursor.fetchone():
            conn.rollback()
            return jsonify({"error": "Booking not found, not yours, or already cancelled"}), 404

        # find the original payment to refund
        cursor.execute("""
            SELECT bank_id, amount FROM bank_transactions
            WHERE booking_id = %s AND txn_type = 'payment'
        """, (booking_id,))
        payment = cursor.fetchone()

        cursor.execute("""
            UPDATE bookings SET status = 'cancelled'
            WHERE booking_id = %s
        """, (booking_id,))

        refund = 0
        if payment:
            refund = payment["amount"]
            cursor.execute("""
                UPDATE bank_accounts SET balance = balance + %s
                WHERE bank_id = %s
            """, (refund, payment["bank_id"]))
            if cursor.rowcount == 0:
                # bank account missing -> undo the cancellation as well
                conn.rollback()
                return jsonify({"error": "Refund failed, booking not cancelled"}), 500

            cursor.execute("""
                INSERT INTO bank_transactions (bank_id, booking_id, amount, txn_type)
                VALUES (%s, %s, %s, 'refund')
            """, (payment["bank_id"], booking_id, refund))

        conn.commit()
        return jsonify({"message": f"Booking cancelled. Refunded {refund:.2f}"}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

