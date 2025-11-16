import os
from app import app, db
from sqlalchemy.exc import OperationalError

print("Starting database initialization...")

# We need to be inside the application context to interact with the database
with app.app_context():
    # A simple check to see if we can connect
    try:
        # db.create_all() is safe to run multiple times.
        # It will only create tables that do not already exist.
        db.create_all()
        print("Database tables checked/created successfully.")
    except OperationalError as e:
        print("=" * 30)
        print("Error: Could not connect to the database.")
        print("Please check your DATABASE_URL environment variable.")
        print(f"Details: {e}")
        print("=" * 30)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

print("Database initialization script finished.")