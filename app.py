import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

# Load the .env file
load_dotenv()

# Configuration

app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret_key_to_change' #session security and flash messages

# Database configuration
db_password = os.getenv('DB_PASSWORD')
db_name = 'budget_db'
db_user = 'postgres'

# Check if the password was loaded
if not db_password:
    raise ValueError("No DB_PASSWORD set. Check your .env file.")

# This line builds the connection string.
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{db_user}:{db_password}@localhost/{db_name}'

# This setting silences a warning from SQLAlchemy
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize the SQLAlchemy database object. This is our 'db' connection.
db = SQLAlchemy(app)

# --- 3. DEFINE DATABASE MODELS (TABLES) ---

class User(db.Model):
    # Set the table name 
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # --- Relationships ---
       
    # Connects User to their Categories
    
    categories = db.relationship('Category', backref='user', lazy=True)
    
    # Connects User to their Transactions
    transactions = db.relationship('Transaction', backref='user', lazy=True)

class Category(db.Model):
    __tablename__ = 'category'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(10), nullable=False) # "Income" or "Expense"
    
    # --- Foreign Key ---
   
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # --- Relationship ---
    # Connects Category to its Transactions
    transactions = db.relationship('Transaction', backref='category', lazy=True)

class Transaction(db.Model):
    __tablename__ = 'transaction'
    
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255))
    transaction_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # --- Foreign Keys ---
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)


# --- NEW CODE ---

# --- 3.5. DEFINE ROUTES (WEB PAGES) ---

# This is the 'decorator' that tells Flask what URL to listen for.
# The '/' means the main homepage (like http://127.0.0.1:5000/)
@app.route('/')
def home():
    # This is the function that runs when someone visits '/'
    # For now, it just returns a simple string.
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    # This function  handle both GET (display form) and POST (submit form)

    if request.method == 'POST':
        # --- This is the POST logic ---
        # 1. Get data from the form
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # 2. Hash the password for security
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # 3. Create a new User object and save to database
        new_user = User(
            username=username, 
            email=email, 
            password_hash=hashed_password
        )

        try:
            # Add the new user to the session and commit
            db.session.add(new_user)
            db.session.commit()

            # Send a success message to the user
            flash('Account created successfully! You can now log in.', 'success')

            # Redirect to the homepage
            return redirect(url_for('home'))

        except Exception as e:
            # This 'except' block will catch errors, e.g., if the username is already taken
            db.session.rollback() # Rollback the changes
            flash(f'Error creating account: {e}. Please try again.', 'danger')
            return redirect(url_for('register'))

    # --- This is the GET logic ---
    # If the method is GET, just show the registration page
    return render_template('register.html')


# --- 4. RUN THE APPLICATION (FOR TESTING) ---

if __name__ == '__main__':
    
    # This is a one-time setup step:
    # It tells SQLAlchemy to look at all the Models defined
    # and create those tables in 'budget_db' database.
    with app.app_context():
        # This command creates the tables
        db.create_all()
        print("Database tables created successfully!")

    # This starts the web server.
    # 'debug=True' will auto-reload the server when save the file
    app.run(debug=True)