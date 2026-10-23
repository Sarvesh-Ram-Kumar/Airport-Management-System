# AirWay – Airport Management System

A web app that connects **airlines**, **airport staff** and **passengers** on one MySQL database. Airlines request flights, staff approve or reject them, and passengers book and pay for seats.

**Team 2:** Anirudh Jayan (CB.SC.U4AIE24007) · Sarvesh Ram Kumar (CB.SC.U4AIE24048) · Aravind S Harilal (CB.SC.U4AIE24008) · Adhwaidh K (CB.SC.U4AIE24003)

## Features

| Role | What they can do |
|---|---|
| Passenger | Browse approved flights with live seat counts, book and pay from a PIN-protected bank account, cancel with an automatic refund |
| Airliner | Register airline details, request flights, track approval status |
| Staff | Approve or reject flight requests, view all bookings |

Logins use bcrypt-hashed passwords and role-based sessions. Three wrong bank PINs lock the account for 15 minutes.

## Tech Stack

Python (Flask) · MySQL · HTML, CSS and JavaScript · bcrypt

## Setup

1. Install the dependencies:
   ```bash
   pip install flask flask-cors mysql-connector-python bcrypt python-dotenv
   ```
2. Create a MySQL database and run the `CREATE TABLE` script from the report (Section 8.2).
3. Fill in your MySQL username, password and database name in `db.py`.
4. Create a `.env` file containing `SECRET_KEY=<any random string>`.
5. Start the app with `python main.py`, then open http://127.0.0.1:5000.

## Project Structure

```
main.py          Flask app; registers the route blueprints
db.py            MySQL connection
routes/          auth.py, flights.py, booking.py, bank.py
templates/       index.html
static/          style.css and JavaScript for each role
bank_schema.sql  Migration that adds the bank tables and price columns
```

## Database

| Table | Purpose | Normal form |
|---|---|---|
| users | All accounts and their role | BCNF |
| airliner_details | Airline profile, linked one-to-one to a user | BCNF |
| flights | Flight requests and their status | BCNF |
| bookings | One seat on a flight | BCNF |
| bank_accounts | Simulated passenger bank accounts | BCNF |
| bank_transactions | Payment and refund log | 1NF (fix in report, Section 5.4) |

**DBMS concepts used:**
- **Transactions:** booking and cancelling are each a single transaction that commits or rolls back as a whole.
- **Row locking:** `SELECT … FOR UPDATE` stops two people from booking the same last seat.
- **Live seat counts:** a `LEFT JOIN` with `GROUP BY` and `HAVING` works out how many seats are left.
- **SQL injection protection:** every query is parameterised.

The ER diagram, UML class diagram, normalization proofs and sample data are in the project report.
