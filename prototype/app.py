from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from pymongo import MongoClient
from bson import ObjectId

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a random secret key

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['notes_db']
users_collection = db['users']
notes_collection = db['notes']
settings_collection = db['settings']

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'signin'

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.role = user_data.get('role', 'user')

@login_manager.user_loader
def load_user(user_id):
    user_data = users_collection.find_one({'_id': ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None

@app.route('/')
def index():
    form_setting = settings_collection.find_one({'_id': 'form_toggle'})
    form_active = form_setting.get('form_active', False)  # Default to False if key is missing
    print(form_active)
    return render_template('index.html', form_active=form_active)


# Sign-up route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form.get('role', 'user')  # default to 'user' role
        existing_user = users_collection.find_one({'username': username})
        
        if existing_user:
            return 'Username already exists', 400
        
        # Insert new user into the users collection
        new_user = {
            'username': username,
            'password': password,  # Store the password securely (e.g., hash it before saving)
            'role': role
        }
        result = users_collection.insert_one(new_user)
        
        user_obj = User(new_user)
        login_user(user_obj)
        return redirect(url_for('index'))
    
    return render_template('signup.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users_collection.find_one({'username': username})
        if user and user['password'] == password:
            user_obj = User(user)
            login_user(user_obj)
            
            # Redirect based on role after login
            if user['role'] == 'hr':
                return redirect(url_for('hr_overview'))  # Redirect HR users directly to the HR overview page
            else:
                return redirect(url_for('index'))  # Redirect normal users to the homepage
        else:
            return 'Invalid username or password', 401
    return render_template('signin.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('signin'))

# Notes management
@app.route('/save_note', methods=['POST'])
@login_required
def save_note():
    category = request.json['category']
    message = request.json['message']
    
    note = {
        'user_id': current_user.id,
        'username': current_user.username,
        'category': category,
        'message': message
    }
    
    result = notes_collection.insert_one(note)
    return jsonify({'success': True, 'id': str(result.inserted_id)})

@app.route('/get_notes', methods=['GET'])
@login_required
def get_notes():
    notes = list(notes_collection.find({'user_id': current_user.id}))
    for note in notes:
        note['_id'] = str(note['_id'])
    return jsonify(notes)

@app.route('/get_notes_by_category', methods=['GET'])
@login_required
def get_notes_by_category():
    categories = ['category1', 'category2', 'category3']
    notes_by_category = {}
    for category in categories:
        notes = list(notes_collection.find({'user_id': current_user.id, 'category': category}))
        notes_by_category[category] = [note['message'] for note in notes]
    return jsonify(notes_by_category)

@app.route('/form')
@login_required
def form():
    if current_user.role == 'hr':
        # Redirect HR users directly to HR overview
        return redirect(url_for('hr_overview'))
    
    # Fetch the form_active value safely
    form_setting = settings_collection.find_one({'_id': 'form_toggle'})
    form_active = form_setting.get('form_active', False) if form_setting else False

    # Debugging - Print the state to the console
    print(f"Form setting from database: {form_setting}, form_active: {form_active}")

    if not form_active:
        # Logically handle inactive form scenario
        return redirect(url_for('index'))

    return render_template('form.html')


@app.route('/save_form', methods=['POST'])
@login_required
def save_form():
    form_data = request.json
    for category, messages in form_data.items():
        # Remove existing notes for this category
        notes_collection.delete_many({'user_id': current_user.id, 'category': category})
        
        # Insert new notes
        for message in messages:
            if message.strip():  # Only insert non-empty messages
                notes_collection.insert_one({
                    'user_id': current_user.id,
                    'username': current_user.username,
                    'category': category,
                    'message': message.strip()
                })
    return jsonify({'success': True})

# HR overview for HR users
@app.route('/hr_overview')
@login_required
def hr_overview():
    if current_user.role != 'hr':
        abort(403)  # Forbidden
    
    # Fetch all notes for users
    users = list(users_collection.find({'role': 'user'}))
    all_notes = {}
    for user in users:
        user_notes = list(notes_collection.find({'user_id': str(user['_id'])}))
        all_notes[user['username']] = user_notes
    
    # Get form activation status
    form_active = settings_collection.find_one({'name': 'form_active'})
    return render_template('hr_overview.html', all_notes=all_notes, form_active=form_active['value'] if form_active else False)

@app.route('/toggle_form', methods=['POST'])
def toggle_form():
    # Parse JSON payload
    data = request.get_json()
    form_active = data.get('active', False)

    # Update or insert the form state into MongoDB
    settings_collection.update_one(
        {"_id": "form_toggle"},  # Unique identifier
        {"$set": {"form_active": form_active}},
        upsert=True
    )
    
    return jsonify({"success": True, "form_active": form_active})


@app.route('/get_form_status', methods=['GET'])
def get_form_status():
    # Fetch the current state from MongoDB
    settings = settings_collection.find_one({"_id": "form_toggle"})
    form_active = settings.get('form_active', False) if settings else False
    return jsonify({"form_active": form_active})

if __name__ == '__main__':
    app.run(debug=True)
