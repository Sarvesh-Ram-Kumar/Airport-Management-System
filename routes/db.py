import mysql.connector
from mysql.connector import Error

def get_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="---",          # your MySQL username
            password="---",  # your MySQL password
            database="---"     # whatever you named your database
        )
        return conn
    except Error as e:
        print(f"Database connection error: {e}")
        return None