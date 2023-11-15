from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configure MySQL
mysql = mysql.connector.connect(
    host="localhost",
    user="master",
    password="password",
    database="SEPROJ"
)
cursor = mysql.cursor(dictionary=True)

# Create tables if they don't exist
with app.app_context():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE,
            password VARCHAR(50),
            spending_limit FLOAT
        
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            amount FLOAT,
            category VARCHAR(50),
            description TEXT,
            transaction_type VARCHAR(10),
            transaction_date DATE,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    mysql.commit()

# Routes

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()

        if user:
            session['user_id'] = user['id']
            return redirect(url_for('profile'))
        else:
            return 'Invalid username or password'

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        mysql.commit()

        return f'Account created for {username}. You can now <a href="/login">login</a>.'

    return render_template('signup.html')

@app.route('/tracker', methods=['GET', 'POST'])
def tracker():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        amount = request.form['amount']
        category = request.form['category']
        description = request.form['description']
        transaction_type = request.form['transaction_type']
        transaction_date = request.form['transaction_date']

        cursor.execute("""
            INSERT INTO transactions (user_id, amount, category, description, transaction_type, transaction_date)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (session['user_id'], amount, category, description, transaction_type, transaction_date))
        mysql.commit()

    # Retrieve user transactions
    cursor.execute("SELECT * FROM transactions WHERE user_id = %s", (session['user_id'],))
    transactions = cursor.fetchall()

    # Calculate total balance
    total_balance = sum([t['amount'] if t['transaction_type'] == 'Income' else -t['amount'] for t in transactions])

    # Calculate category-wise expenses
    expense_summary = {}
    for transaction in transactions:
        if transaction['transaction_type'] == 'Expense':
            category = transaction['category']
            if category not in expense_summary:
                expense_summary[category] = 0
            
            expense_summary[category] += transaction['amount']

    # Calculate monthly expenses
    monthly_summary = {}
    for transaction in transactions:
        month = transaction['transaction_date'].strftime('%Y-%m')
        if month not in monthly_summary:
            monthly_summary[month] = 0
        if transaction['transaction_type'] == 'Expense':
            monthly_summary[month] += transaction['amount']

    return render_template('tracker.html', transactions=transactions, total_balance=total_balance,
                           expense_summary=expense_summary, monthly_summary=monthly_summary)

# app.py

# ... (previous code)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    # Fetch user details including spending_limit
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    if request.method == 'POST':
        spending_limit = request.form['limit']

        # Update user's spending_limit in the database
        cursor.execute("UPDATE users SET spending_limit = %s WHERE id = %s", (spending_limit, user_id))
        mysql.commit()

        # Redirect to my_profile page to display the updated spending_limit
        return redirect(url_for('profile'))

    # Fetch user transactions
    cursor.execute("SELECT * FROM transactions WHERE user_id = %s", (user_id,))
    transactions = cursor.fetchall()

    # Calculate total expenses
    total_expenses = sum([t['amount'] if t['transaction_type'] == 'Expense' else 0 for t in transactions])

    return render_template('profile.html', user=user, total_expenses=total_expenses)

# ... (remaining code)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
