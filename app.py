from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
import bcrypt
import requests
import json
import os
from flask import g

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # For session management and flash messages
DATABASE = 'database.db'

# OpenAI API key - should be stored as an environment variable in production
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY', 'your_openai_api_key_here')

# Database connection helper
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Initialize database and create tables if not exist
def init_db():
    with app.app_context():
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )''')
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )''')
        db.commit()

# Home/Login Page
@app.route('/', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('chat'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT user_id, password_hash FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        
        if user and bcrypt.checkpw(password.encode(), user[1]):
            session['user_id'] = user[0]
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('chat'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('index.html')

# Sign-Up Page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('chat'))
        
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm-password']
        
        if password != confirm_password:
            flash('Passwords do not match!', 'danger')
            return redirect(url_for('signup'))
        
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return redirect(url_for('signup'))
        
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash))
            db.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists.', 'danger')
    
    return render_template('signup.html')

# Chat Interface Page
@app.route('/chat')
def chat():
    if 'user_id' not in session:
        flash('Please log in to access the chatbot.', 'warning')
        return redirect(url_for('login'))
    
    return render_template('chat.html', username=session.get('username', 'User'))

# API endpoint for chat
@app.route('/api/chat', methods=['POST'])
def handle_chat():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    user_message = data.get('message', '')
    
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400
    
    # Get AI response
    ai_response = get_ai_response(user_message, data.get('history', []))
    
    # Save to database
    save_chat_history(session['user_id'], user_message, ai_response)
    
    return jsonify({'response': ai_response})

# Function to get AI response using OpenAI's API
def get_ai_response(message, history):
    try:
        url = "https://api.openai.com/v1/chat/completions"
        
        # Format the conversation history
        messages = [
            {"role": "system", "content": "You are Tela, a helpful AI assistant. Provide concise and friendly responses."}
        ]
        
        # Add conversation history (limited to last 10 messages for efficiency)
        for item in history[-10:]:
            messages.append({"role": item['role'], "content": item['content']})
        
        # Add the current user message
        messages.append({"role": "user", "content": message})
        
        payload = {
            "model": "gpt-3.5-turbo",  # You can use other models like "gpt-4" if available
            "messages": messages,
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENAI_API_KEY}"
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()
        
        if 'choices' in response_data and len(response_data['choices']) > 0:
            return response_data['choices'][0]['message']['content'].strip()
        else:
            app.logger.error(f"API Error: {response_data}")
            return "I'm sorry, I couldn't process your request at the moment."
            
    except Exception as e:
        app.logger.error(f"Error getting AI response: {str(e)}")
        return "I apologize for the inconvenience. There was an error processing your request."

# Function to save chat history to database
def save_chat_history(user_id, message, response):
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO chat_history (user_id, message, response) VALUES (?, ?, ?)",
            (user_id, message, response)
        )
        db.commit()
    except Exception as e:
        app.logger.error(f"Error saving chat history: {str(e)}")

# Logout Route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Logged out successfully.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)
