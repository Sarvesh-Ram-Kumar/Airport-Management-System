from flask import Blueprint, request, jsonify, session
import bcrypt
from db import get_connection

auth = Blueprint("auth", __name__)

# ─── SIGNUP ───────────────────────────────────────────────

@auth.route("/api/signup", methods=["POST"])
def signup():
    data          = request.get_json()
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

@auth.route("/api/login", methods=["POST"])
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
        session["user_id"] = user["id"]
        session["role"]    = user["role"]
        session["name"]    = user["name"]
        return jsonify({
            "message": "Login successful",
            "role":    user["role"],
            "name":    user["name"]
        }), 200
    else:
        return jsonify({"error": "Invalid username or password"}), 401


# ─── LOGOUT ───────────────────────────────────────────────

@auth.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"}), 200


# ─── DASHBOARD ────────────────────────────────────────────

@auth.route("/api/dashboard", methods=["GET"])
def dashboard():
    if "user_id" not in session:
        return jsonify({"error": "Not logged in"}), 401
    return jsonify({
        "role": session["role"],
        "name": session["name"]
    }), 200