from flask import Flask, render_template, request, redirect, session, jsonify
from pymongo import MongoClient
from functools import wraps
import os
from datetime import datetime
from bson import ObjectId

app = Flask(__name__)
app.secret_key = os.urandom(24)

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['notes_db']

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect('/signin')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    return redirect('/notes')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        role = 'hr' if email == 'hr@gmail.com' else 'user'

        if db.users.find_one({'email': email}):
            return jsonify({'error': 'Email already exists'}), 400

        user = {
            'name': name,
            'email': email,
            'password': password,
            'role': role
        }
        db.users.insert_one(user)
        return redirect('/signin')

    return render_template('signup.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = db.users.find_one({'email': email, 'password': password})
        if user:
            session['user_id'] = str(user['_id'])
            session['role'] = user['role']
            return redirect('/notes')
        return jsonify({'error': 'Invalid credentials'}), 401

    return render_template('signin.html')

@app.route('/notes')
@login_required
def notes():
    if session.get('role') == 'hr':
        return redirect('/forms')
    user_notes = list(db.notes.find({'user_id': session['user_id']}))
    return render_template('notes.html', notes=user_notes)

@app.route('/api/notes', methods=['POST'])
@login_required
def save_note():
    category = request.json['category']
    message = request.json['message']
    timestamp = datetime.now()

    note = {
        'user_id': session['user_id'],
        'category': category,
        'message': message,
        'created_at': timestamp
    }
    db.notes.insert_one(note)
    return jsonify({'success': True})

@app.route('/api/toggle-form', methods=['POST'])
@login_required
def toggle_form():
    if session.get('role') != 'hr':
        return jsonify({'error': 'Unauthorized'}), 403

    form_status = db.form_status.find_one({'id': 1})
    if form_status is None:
        return jsonify({'error': 'Form status not initialized'}), 500

    new_status = not form_status['enabled']
    db.form_status.update_one({'id': 1}, {'$set': {'enabled': new_status}})

    return jsonify({'success': True, 'enabled': new_status})

@app.route('/notifications')
@login_required
def notifications():
    user_notifications = list(db.notifications.find({'user_id': session['user_id']}))
    return render_template('notifications.html', notifications=user_notifications)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/signin')

@app.route('/forms')
@login_required
def forms():
    is_hr = session.get('role') == 'hr'
    form_status = db.form_status.find_one({'id': 1})

    if form_status is None:
        return jsonify({'error': 'Form status not initialized'}), 500

    if is_hr:
        submissions = list(db.form_submissions.find())
        for submission in submissions:
            user = db.users.find_one({'_id': ObjectId(submission['user_id'])})
            submission['user_name'] = user['name'] if user else 'Unknown'
        return render_template('forms_hr.html', submissions=submissions, form_enabled=form_status['enabled'])

    if not form_status['enabled']:
        return render_template('forms.html', form_enabled=False)

    user_notes = {}
    notes = db.notes.find({'user_id': session['user_id']})
    for note in notes:
        category = note['category']
        if category not in user_notes:
            user_notes[category] = []
        user_notes[category].append({
            'message': note['message']
        })

    return render_template('forms.html', form_enabled=True, notes=user_notes)

@app.route('/api/submit-form', methods=['POST'])
@login_required
def submit_form():
    if session.get('role') == 'hr':
        return jsonify({'error': 'Unauthorized'}), 403

    form_data = request.json
    form_data = {k: v for k, v in form_data.items() if v}

    if not form_data:
        return jsonify({'error': 'At least one field must be filled'}), 400

    timestamp = datetime.now()

    submission = {
        'user_id': session['user_id'],
        'data': form_data,
        'created_at': timestamp
    }
    db.form_submissions.insert_one(submission)

    notification = {
        'user_id': session['user_id'],
        'message': 'You have submitted a new form.',
        'created_at': timestamp
    }
    db.notifications.insert_one(notification)

    return jsonify({'success': True})

if __name__ == '__main__':
    if not db.form_status.find_one({'id': 1}):
        db.form_status.insert_one({'id': 1, 'enabled': True})
    app.run(debug=True)
