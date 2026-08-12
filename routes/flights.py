from flask import Flask, Blueprint, request, jsonify, render_template, session
from flask_cors import CORS
import bcrypt
from db import get_connection

flights = Blueprint("flights", __name__)
# ─── AIRLINER: REQUEST A FLIGHT ───────────────────────────

@flights.route("/api/flights/request", methods=["POST"])
def request_flight():
    if session.get("role") != "airliner":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO flights 
            (flight_no, aircraft_type, origin, destination, 
             flight_date, flight_time, gate, capacity, airliner_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            data["flight_no"],
            data["aircraft_type"],
            data["origin"],
            data["destination"],
            data["flight_date"],
            data["flight_time"],
            data["gate"],
            data["capacity"],
            session["user_id"]
        ))
        conn.commit()
        return jsonify({"message": "Flight requested successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()


# ─── AIRLINER: VIEW OWN FLIGHTS ───────────────────────────

@flights.route("/api/flights/mine", methods=["GET"])
def my_flights():
    if session.get("role") != "airliner":
        return jsonify({"error": "Unauthorized"}), 403

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT flight_id, flight_no, aircraft_type, origin, destination,
               flight_date, flight_time, gate, capacity, status
        FROM flights
        WHERE airliner_id = %s
        ORDER BY flight_date, flight_time
    """, (session["user_id"],))
    flights = cursor.fetchall()
    cursor.close()
    conn.close()

    # convert date/time to string so jsonify can handle them
    for f in flights:
        f["flight_date"] = str(f["flight_date"])
        f["flight_time"] = str(f["flight_time"])

    return jsonify(flights), 200

# ─── STAFF: VIEW PENDING FLIGHTS ──────────────────────────

@flights.route("/api/flights/pending", methods=["GET"])
def pending_flights():
    if session.get("role") != "staff":
        return jsonify({"error": "Unauthorized"}), 403

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT f.flight_id, f.flight_no, f.aircraft_type, f.origin, 
               f.destination, f.flight_date, f.flight_time, 
               f.gate, f.capacity, f.status,
               a.airline_name
        FROM flights f
        JOIN airliner_details a ON f.airliner_id = a.airliner_id
        WHERE f.status = 'pending'
        ORDER BY f.flight_date, f.flight_time
    """)
    flights = cursor.fetchall()
    cursor.close()
    conn.close()

    for f in flights:
        f["flight_date"] = str(f["flight_date"])
        f["flight_time"] = str(f["flight_time"])

    return jsonify(flights), 200


# ─── STAFF: APPROVE OR REJECT FLIGHT ──────────────────────

@flights.route("/api/flights/update_status", methods=["POST"])
def update_flight_status():
    if session.get("role") != "staff":
        return jsonify({"error": "Unauthorized"}), 403

    data      = request.get_json()
    flight_id = data["flight_id"]
    new_status = data["status"]  # approved / rejected / on_route / completed / cancelled

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE flights SET status = %s WHERE flight_id = %s
        """, (new_status, flight_id))
        conn.commit()
        return jsonify({"message": f"Flight status updated to {new_status}"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()


# ─── PASSENGER: VIEW APPROVED FLIGHTS ─────────────────────

@flights.route("/api/flights/available", methods=["GET"])
def available_flights():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT f.flight_id, f.flight_no, f.aircraft_type,
               f.origin, f.destination, f.flight_date, f.flight_time,
               f.gate, f.capacity, a.airline_name,
               f.capacity - COUNT(b.booking_id) AS seats_remaining
        FROM flights f
        JOIN airliner_details a ON f.airliner_id = a.airliner_id
        LEFT JOIN bookings b ON f.flight_id = b.flight_id 
                             AND b.status = 'confirmed'
        WHERE f.status = 'approved'
        GROUP BY f.flight_id
        HAVING seats_remaining > 0
        ORDER BY f.flight_date, f.flight_time
    """)
    flights = cursor.fetchall()
    cursor.close()
    conn.close()

    for f in flights:
        f["flight_date"] = str(f["flight_date"])
        f["flight_time"] = str(f["flight_time"])

    return jsonify(flights), 200