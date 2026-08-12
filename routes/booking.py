from flask import Flask, Blueprint, request, jsonify, render_template, session
from flask_cors import CORS
import bcrypt
from db import get_connection

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
        SELECT b.booking_id, b.seat_no, b.status, b.booked_at,
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

    return jsonify(bookings), 200




# ─── PASSENGER: BOOK A SEAT ───────────────────────────────

@bookings.route("/api/bookings/book", methods=["POST"])
def book_seat():
    if session.get("role") != "passenger":
        return jsonify({"error": "Unauthorized"}), 403

    data      = request.get_json()
    flight_id = data["flight_id"]
    seat_no   = data["seat_no"]
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
            SELECT capacity,
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

        # safe to insert booking
        cursor.execute("""
            INSERT INTO bookings (user_id, flight_id, seat_no, status)
            VALUES (%s, %s, %s, 'confirmed')
        """, (user_id, flight_id, seat_no))

        conn.commit()
        return jsonify({"message": f"Seat {seat_no} booked successfully"}), 201

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
        SELECT b.booking_id, b.seat_no, b.status, b.booked_at,
               f.flight_no, f.origin, f.destination,
               f.flight_date, f.flight_time, f.gate,
               a.airline_name
        FROM bookings b
        JOIN flights f ON b.flight_id = f.flight_id
        JOIN airliner_details a ON f.airliner_id = a.airliner_id
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

    cursor = conn.cursor()
    try:
        # make sure this booking belongs to the logged in passenger
        cursor.execute("""
            UPDATE bookings SET status = 'cancelled'
            WHERE booking_id = %s AND user_id = %s
        """, (booking_id, session["user_id"]))
        conn.commit()

        if cursor.rowcount == 0:
            return jsonify({"error": "Booking not found or not yours"}), 404

        return jsonify({"message": "Booking cancelled"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

