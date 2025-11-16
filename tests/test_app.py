# tests/test_app.py

import pytest
from app import app as flask_app, db, User

"""
This is new, more advanced 'client' fixture.
It will:
1. Set up the app for testing.
2. Use a temporary in-memory database (SQLite) so we don't touch our real one.
3. Create all the database tables before each test.
4. Delete all the tables after each test.
"""
@pytest.fixture
def client():
    # 1. Configure the app for testing
    flask_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",  # Use a new, in-memory database
        "WTF_CSRF_ENABLED": False,  # Disable CSRF forms (easier for testing)
        "SECRET_KEY": "test_secret_key" # Set a test secret key
    })

    # 2. Create the test client
    with flask_app.test_client() as client:
        # 3. Create all database tables
        with flask_app.app_context():
            db.create_all()
        
        # 4. 'yield' the client to the test function
        yield client
        
        # 5. After the test runs, drop all tables
        with flask_app.app_context():
            db.drop_all()

# --- First Test  ---
def test_home_page_logged_out(client):
    """
    GIVEN a test client (which is logged out by default)
    WHEN the '/' (home) page is requested (GET)
    THEN check that the response is valid and shows the welcome page
    """
    response = client.get('/')
    assert response.status_code == 200
    assert b"Welcome to Your Budget Tracker" in response.data
    assert b"Login" in response.data

# --- Second Test  ---
def test_dashboard_page_logged_out(client):
    """
    GIVEN a logged-out client
    WHEN the '/dashboard' page is requested (GET)
    THEN check that the user is redirected to the /login page
    """
    response = client.get('/dashboard')
    assert response.status_code == 302
    assert '/login' in response.location

# --- NEW LOGGED-IN TEST ---
def test_successful_registration_and_login(client):
    """
    GIVEN a test client
    WHEN a new user is registered (POST to /register)
    AND then logged in (POST to /login)
    THEN check that the dashboard is accessible
    """
    
    # 1. Register a new user
    # We use 'client.post' to send form data
    register_response = client.post('/register', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'password123'
    }, follow_redirects=True) # 'follow_redirects' follows the 302 redirect
    
    # Check that registration was successful and redirected to login
    assert register_response.status_code == 200
    assert b"Account created successfully!" in register_response.data
    assert b"Login" in register_response.data # Should be on the login page

    # 2. Log in as the new user
    login_response = client.post('/login', data={
        'username': 'testuser',
        'password': 'password123'
    }, follow_redirects=True)
    
    # Check that login was successful and redirected to dashboard
    assert login_response.status_code == 200
    assert b"Login successful!" in login_response.data
    assert b"Your Dashboard" in login_response.data
    assert b"Welcome, testuser!" in login_response.data

    # 3. Now that we are "logged in", test the dashboard directly
    dashboard_response = client.get('/dashboard')
    assert dashboard_response.status_code == 200
    assert b"Your Dashboard" in dashboard_response.data