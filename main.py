from flask import Flask, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import os

from routes.auth import auth
from routes.flights import flights
from routes.booking import bookings

load_dotenv()

app = Flask(__name__)
CORS(app)
app.secret_key = os.getenv("SECRET_KEY")

# ─── REGISTER BLUEPRINTS ──────────────────────────────────

app.register_blueprint(auth)
app.register_blueprint(flights)  
app.register_blueprint(bookings) 

# ─── SERVE FRONTEND ───────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True)