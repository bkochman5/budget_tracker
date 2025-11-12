import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date
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

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login' 
login_manager.login_message_category = 'info' # for styling flash messages
# --- 3. DEFINE DATABASE MODELS (TABLES) ---

class User(db.Model, UserMixin):
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

# --- 3.2. FLASK-LOGIN USER LOADER ---

@login_manager.user_loader
def load_user(user_id):
    # This function is used by Flask-Login to reload the user object from the session
    return User.query.get(int(user_id))


# --- 3.5. DEFINE ROUTES (WEB PAGES) ---

# This is the 'decorator' that tells Flask what URL to listen for.
# The '/' means the main homepage (like http://127.0.0.1:5000/)

# NEW LOGIN ROUTE

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, send them to the homepage
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    if request.method == 'POST':
        # --- This is the POST logic ---
        username = request.form['username']
        password = request.form['password']

        # 1. Find the user in the database by their username
        user = User.query.filter_by(username=username).first()

        # 2. Check if user exists and if the password is correct
        if user and bcrypt.check_password_hash(user.password_hash, password):
            # 3. If correct, log the user in
            login_user(user, remember=True) # 'remember=True' keeps them logged in
            flash('Login successful!', 'success')

            # Send them to the homepage
            return redirect(url_for('home'))
        else:
            # If a-ha, show an error
            flash('Login unsuccessful. Please check username and password.', 'danger')

    # --- This is the GET logic ---
    return render_template('login.html')

# NEW LOGOUT ROUTE

@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/')
def home():
    """
    This is the main homepage.
    It checks if a user is logged in.
    If they are, it redirects them to their dashboard.
    If not, it shows the public landing page (index.html).
    """
    if current_user.is_authenticated:
        # User is logged in, send them to the main app
        return redirect(url_for('dashboard'))
    
    # User is not logged in, show the public homepage
    return render_template('index.html')

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required  # Protects this page, user must be logged in
def dashboard():
    """
    This route handles both displaying the dashboard (GET)
    and adding a new transaction (POST).
    """
    
    if request.method == 'POST':
        # --- POST LOGIC: User is submitting the 'Add Transaction' form ---
        
        # 1. Get all data from the form
        amount = request.form['amount']
        description = request.form['description']
        category_id = request.form['category_id']
        # The date comes from the form as a string, e.g., "2025-11-09"
        date_string = request.form['transaction_date'] 
        
        # 2. Convert the date string into a Python 'date' object
        transaction_date = datetime.strptime(date_string, '%Y-%m-%d').date()

        # 3. Create the new Transaction object
        new_transaction = Transaction(
            amount=amount,
            description=description,
            transaction_date=transaction_date,
            user_id=current_user.id,    # Link to the logged-in user
            category_id=category_id     # Link to the chosen category
        )
        
        # 4. Add to database and save
        db.session.add(new_transaction)
        db.session.commit()
        
        flash('Transaction added successfully!', 'success')
        
        # 5. Redirect back to the dashboard to refresh the page
        return redirect(url_for('dashboard'))

    # --- GET LOGIC: User is just visiting the page ---
    
    # 1. Fetch all categories for the current user
    #    We need this to populate the dropdown menu in the form.
    user_categories = Category.query.filter_by(user_id=current_user.id).all()
    
    # 2. Fetch all transactions for the current user
    #    We 'order_by' to show the newest ones first.
    user_transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.transaction_date.desc()).all()

    # 3. Render the dashboard page
    #    We pass both lists (categories and transactions) to the HTML.
    return render_template('dashboard.html', categories=user_categories, transactions=user_transactions)
# NEW CATEGORIES ROUTE

@app.route('/categories', methods=['GET', 'POST'])
@login_required  # This is the decorator to protect the route
def categories():
    if request.method == 'POST':
        # --- This is the POST logic (form submitted) ---

        # 1. Get data from the form
        name = request.form['name']
        type = request.form['type']

        # 2. Check if this category already exists for this user
        existing_category = Category.query.filter_by(user_id=current_user.id, name=name).first()

        if existing_category:
            flash('This category name already exists.', 'danger')
        else:
            # 3. Create a new Category object
            new_category = Category(
                name=name,
                type=type,
                user_id=current_user.id  # Link the category to the logged-in user
            )

            # 4. Add to database
            db.session.add(new_category)
            db.session.commit()
            flash('Category added successfully!', 'success')

        # 5. Redirect back to this same page (to clear the form)
        return redirect(url_for('categories'))

    # --- This is the GET logic (page loaded) ---
    # 1. Fetch all categories that belong to the current logged-in user
    user_categories = Category.query.filter_by(user_id=current_user.id).all()

    # 2. Render the HTML, passing in the list of categories
    return render_template('categories.html', categories=user_categories)

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
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

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