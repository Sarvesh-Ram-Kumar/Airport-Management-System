from flask import Flask, request, jsonify, render_template, session
from flask_cors import CORS
import bcrypt
from db import get_connection

app = Flask(__name__)
CORS(app)
app.secret_key = "---"

# ─── SERVE FRONTEND ───────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")

# ─── SIGNUP ───────────────────────────────────────────────

@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.get_json()
    username      = data["username"]
    password      = data["password"]
    name          = data["name"]
    role          = data["role"]

    password_hash = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, name)
            VALUES (%s, %s, %s, %s)
        """, (username, password_hash, role, name))
        conn.commit()

        if role == "airliner":
            user_id       = cursor.lastrowid
            airline_name  = data["airline_name"]
            license_no    = data["license_no"]
            contact_email = data["contact_email"]
            country       = data["country"]
            cursor.execute("""
                INSERT INTO airliner_details
                (airliner_id, airline_name, license_no, contact_email, country)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_id, airline_name, license_no, contact_email, country))
            conn.commit()

        return jsonify({"message": "Signup successful"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

# ─── LOGIN ────────────────────────────────────────────────

@app.route("/api/login", methods=["POST"])
def login():
    data     = request.get_json()
    username = data["username"]
    password = data["password"]

    conn = get_connection()
    if not conn:
        return jsonify({"error": "Database connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    if user and bcrypt.checkpw(
        password.encode("utf-8"),
        user["password_hash"].encode("utf-8")
    ):
        session["user_id"]  = user["id"]
        session["role"]     = user["role"]
        session["name"]     = user["name"]
        return jsonify({
            "message": "Login successful",
            "role":     user["role"],
            "name":     user["name"]
        }), 200
    else:
        return jsonify({"error": "Invalid username or password"}), 401

# ─── LOGOUT ───────────────────────────────────────────────

@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200

# ─── DASHBOARDS ───────────────────────────────────────────

@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    return jsonify({
        "role": session["role"],
        "name": session["name"]
    }), 200

# ─── AIRLINER: REQUEST A FLIGHT ───────────────────────────

@app.route("/api/flights/request", methods=["POST"])
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

@app.route("/api/flights/mine", methods=["GET"])
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

@app.route("/api/flights/pending", methods=["GET"])
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

@app.route("/api/flights/update_status", methods=["POST"])
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


# ─── STAFF: VIEW ALL BOOKINGS ─────────────────────────────

@app.route("/api/bookings/all", methods=["GET"])
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

# ─── PASSENGER: VIEW APPROVED FLIGHTS ─────────────────────

@app.route("/api/flights/available", methods=["GET"])
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


# ─── PASSENGER: BOOK A SEAT ───────────────────────────────

@app.route("/api/bookings/book", methods=["POST"])
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

@app.route("/api/bookings/mine", methods=["GET"])
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

@app.route("/api/bookings/cancel", methods=["POST"])
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



if __name__ == "__main__":
    app.run(debug=True)
