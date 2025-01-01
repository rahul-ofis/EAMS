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
db = client['EmployeeManagement']

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'employee_id' not in session:
            return redirect('/signin')
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    return redirect('/critical-incidents')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']

        if db.employees.find_one({'email': email}):
            return jsonify({'error': 'Email already exists'}), 400

        employee = {
            'name': name,
            'email': email,
            'password': password,
            'role': role
        }
        db.employees.insert_one(employee)
        return jsonify({'success': True, 'redirect': '/signin'})
    return render_template('auth.html', title='Sign Up', is_signup=True)

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        employee = db.employees.find_one({'email': email, 'password': password})
        if employee:
            session['employee_id'] = str(employee['_id'])
            session['role'] = employee['role']
            return jsonify({'success': True, 'redirect': '/critical-incidents'})
        return jsonify({'error': 'Invalid credentials'}), 401
    return render_template('auth.html', title='Sign In', is_signup=False)

@app.route('/critical-incidents')
@login_required
def critical_incidents():
    if session.get('role') == 'hr':
        return redirect('/forms')
    employee_critical_incidents = list(db.critical_incidents.find({'employee_id': session['employee_id']}))
    return render_template('critical_incidents.html', critical_incidents=employee_critical_incidents)

@app.route('/api/critical-incidents', methods=['POST'])
@login_required
def save_critical_incident():
    category = request.json['category']
    message = request.json['message']
    timestamp = datetime.now()

    critical_incident = {
        'employee_id': session['employee_id'],
        'category': category,
        'message': message,
        'created_at': timestamp
    }
    db.critical_incidents.insert_one(critical_incident)
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

    # Add notification for all employees
    status_text = 'enabled' if new_status else 'disabled'
    employees = db.employees.find({'role': {'$ne': 'hr'}})
    for employee in employees:
        notification = {
            'employee_id': str(employee['_id']),
            'message': f'The form has been {status_text} by HR',
            'created_at': datetime.now()
        }
        db.notifications.insert_one(notification)

    return jsonify({'success': True, 'enabled': new_status})

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/signin')

@app.route('/forms')
@login_required
def forms():
    if session.get('role') == 'admin':
        return redirect('/all-submissions')
    try:
        is_hr = session.get('role') == 'hr'
        form_status = db.form_status.find_one({'id': 1})

        if form_status is None:
            # Initialize form status if not present
            db.form_status.insert_one({'id': 1, 'enabled': False})
            form_status = {'enabled': False}

        if is_hr:
            employees = list(db.employees.find({'role': {'$ne': 'hr'}}))
            submissions = list(db.form_submissions.find())
            for submission in submissions:
                employee = db.employees.find_one({'_id': ObjectId(submission['employee_id'])})
                submission['employee_name'] = employee['name'] if employee else 'Unknown'
                submission['employee_role'] = employee['role'] if employee else 'Unknown'
            return render_template('forms_hr.html', submissions=submissions, form_enabled=form_status['enabled'], employees=employees)

        if not form_status['enabled'] and not is_hr:
            return render_template('forms.html', form_enabled=False)

        # Get the latest submission for this employee
        submission = db.form_submissions.find_one(
            {'employee_id': session['employee_id']},
            sort=[('created_at', -1)]
        )

        # Get employee's critical incidents
        employee_critical_incidents = {}
        critical_incidents = db.critical_incidents.find({'employee_id': session['employee_id']})
        for critical_incident in critical_incidents:
            category = critical_incident['category']
            if category not in employee_critical_incidents:
                employee_critical_incidents[category] = []
            employee_critical_incidents[category].append({
                'message': critical_incident['message']
            })

        employees = list(db.employees.find())
        return render_template('forms.html', form_enabled=True, critical_incidents=employee_critical_incidents, submission=submission, employees=employees)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit-form', methods=['POST'])
@login_required
def submit_form():
    if session.get('role') == 'hr':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        data = request.json
        form_data = data.get('formData', {})
        new_critical_incidents = data.get('newCriticalIncidents', [])

        if not form_data:
            return jsonify({'error': 'At least one field must be filled'}), 400

        timestamp = datetime.now()

        # Save new form submission
        submission = {
            'employee_id': session['employee_id'],
            'data': form_data,
            'created_at': timestamp
        }
        result = db.form_submissions.insert_one(submission)
        if not result.inserted_id:
            return jsonify({'error': 'Failed to save submission'}), 500

        # Save new critical incidents
        for critical_incident in new_critical_incidents:
            existing = db.critical_incidents.find_one({
                'employee_id': session['employee_id'],
                'category': critical_incident['category'],
                'message': critical_incident['message']
            })
            
            if not existing:
                critical_incident['employee_id'] = session['employee_id']
                critical_incident['created_at'] = timestamp
                db.critical_incidents.insert_one(critical_incident)

        return jsonify({'success': True})
    except Exception as e:
        print(f"Error in submit_form: {str(e)}")  # For debugging
        return jsonify({'error': 'An error occurred while submitting the form'}), 500

@app.route('/api/create-team', methods=['POST'])
@login_required
def create_team():
    if session.get('role') != 'hr':
        return jsonify({'error': 'Unauthorized'}), 403

    team_name = request.form['team_name']
    manager_id = request.form['manager']
    member_ids = request.form.getlist('members')

    team = {
        'name': team_name,
        'manager_id': manager_id,
        'member_ids': member_ids
    }
    db.teams.insert_one(team)

    # Update the employee's role to 'manager'
    db.employees.update_one({'_id': ObjectId(manager_id)}, {'$set': {'role': 'manager'}})

    # Add notifications for manager and members
    notification_manager = {
        'employee_id': manager_id,
        'message': f'You have been assigned as the manager of team {team_name}',
        'created_at': datetime.now()
    }
    db.notifications.insert_one(notification_manager)

    for member_id in member_ids:
        notification_member = {
            'employee_id': member_id,
            'message': f'You have been added to team {team_name}',
            'created_at': datetime.now()
        }
        db.notifications.insert_one(notification_member)

    return jsonify({'success': True})

@app.route('/api/delete-team/<team_id>', methods=['DELETE'])
@login_required
def delete_team(team_id):
    if session.get('role') != 'hr':
        return jsonify({'error': 'Unauthorized'}), 403

    team = db.teams.find_one({'_id': ObjectId(team_id)})
    if not team:
        return jsonify({'error': 'Team not found'}), 404

    # Notify manager about role change
    notification_manager = {
        'employee_id': str(team['manager_id']),
        'message': f'You are no longer the manager of team {team["name"]}',
        'created_at': datetime.now()
    }
    db.notifications.insert_one(notification_manager)

    # Notify members about team deletion
    for member_id in team['member_ids']:
        notification_member = {
            'employee_id': str(member_id),
            'message': f'You have been removed from team {team["name"]}',
            'created_at': datetime.now()
        }
        db.notifications.insert_one(notification_member)

    # Reassign manager role to employee
    db.employees.update_one({'_id': ObjectId(team['manager_id'])}, {'$set': {'role': 'employee'}})
    db.teams.delete_one({'_id': ObjectId(team_id)})

    return jsonify({'success': True})

@app.route('/api/get-team/<team_id>', methods=['GET'])
@login_required
def get_team(team_id):
    if session.get('role') != 'hr':
        return jsonify({'error': 'Unauthorized'}), 403

    team = db.teams.find_one({'_id': ObjectId(team_id)})
    if not team:
        return jsonify({'error': 'Team not found'}), 404

    team['_id'] = str(team['_id'])
    team['manager_id'] = str(team['manager_id'])
    team['member_ids'] = [str(member_id) for member_id in team['member_ids']]

    return jsonify(team)

@app.route('/api/edit-team', methods=['POST'])
@login_required
def edit_team():
    if session.get('role') != 'hr':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        team_id = request.form['team_id']
        team_name = request.form['team_name']
        new_member_ids = request.form.getlist('members')
        new_manager_id = request.form.get('manager')
    except KeyError as e:
        return jsonify({'error': f'Missing field: {str(e)}'}), 400

    team = db.teams.find_one({'_id': ObjectId(team_id)})
    if not team:
        return jsonify({'error': 'Team not found'}), 404

    # Handle manager change
    if new_manager_id and team['manager_id'] != new_manager_id:
        # Notify old manager
        notification_old_manager = {
            'employee_id': str(team['manager_id']),
            'message': f'You are no longer the manager of team {team_name}',
            'created_at': datetime.now()
        }
        db.notifications.insert_one(notification_old_manager)

        # Notify new manager
        notification_new_manager = {
            'employee_id': new_manager_id,
            'message': f'You have been assigned as the manager of team {team_name}',
            'created_at': datetime.now()
        }
        db.notifications.insert_one(notification_new_manager)

        # Update roles
        db.employees.update_one({'_id': ObjectId(team['manager_id'])}, {'$set': {'role': 'employee'}})
        db.employees.update_one({'_id': ObjectId(new_manager_id)}, {'$set': {'role': 'manager'}})
        team_update = {'name': team_name, 'manager_id': new_manager_id, 'member_ids': new_member_ids}
    else:
        team_update = {'name': team_name, 'member_ids': new_member_ids}

    # Handle member changes
    old_member_ids = set(str(mid) for mid in team['member_ids'])
    new_member_ids_set = set(new_member_ids)

    # Notify removed members
    for member_id in old_member_ids - new_member_ids_set:
        notification = {
            'employee_id': member_id,
            'message': f'You have been removed from team {team_name}',
            'created_at': datetime.now()
        }
        db.notifications.insert_one(notification)

    # Notify new members
    for member_id in new_member_ids_set - old_member_ids:
        notification = {
            'employee_id': member_id,
            'message': f'You have been added to team {team_name}',
            'created_at': datetime.now()
        }
        db.notifications.insert_one(notification)

    db.teams.update_one(
        {'_id': ObjectId(team_id)},
        {'$set': team_update}
    )

    return jsonify({'success': True})

@app.route('/teams')
@login_required
def teams():
    if session.get('role') != 'hr':
        return redirect('/forms')

    teams = list(db.teams.find())
    employees = list(db.employees.find())
    for team in teams:
        manager = db.employees.find_one({'_id': ObjectId(team['manager_id'])})
        team['manager_name'] = manager['name'] if manager else 'Unknown'
        team['members'] = [db.employees.find_one({'_id': ObjectId(member_id)})['name'] for member_id in team['member_ids']]
        for employee in employees:
            if str(employee['_id']) == str(team['manager_id']):
                employee['team'] = {'name': team['name'], 'role': 'Manager', '_id': str(team['_id'])}
            elif str(employee['_id']) in team['member_ids']:
                employee['team'] = {'name': team['name'], 'role': 'Member', '_id': str(team['_id'])}
    return render_template('teams.html', teams=teams, employees=employees)

@app.route('/team-submissions')
@login_required
def team_submissions():
    if session.get('role') != 'manager':
        return redirect('/forms')

    team = db.teams.find_one({'manager_id': session['employee_id']})
    if team:
        team_name = team['name']
        member_ids = [ObjectId(id) for id in team['member_ids']]
        team_members = list(db.employees.find({'_id': {'$in': member_ids}}))
        
        submissions = list(db.form_submissions.find({'employee_id': {'$in': [str(id) for id in member_ids]}}))
        for submission in submissions:
            employee = db.employees.find_one({'_id': ObjectId(submission['employee_id'])})
            submission['employee_name'] = employee['name'] if employee else 'Unknown'
            
        return render_template('forms_manager.html', 
                             team_name=team_name, 
                             submissions=submissions, 
                             team_members=team_members)
    else:
        return render_template('forms_manager.html', team_name=None, submissions=[], team_members=[])

@app.route('/api/notifications')
@login_required
def get_notifications():
    notifications = list(db.notifications.find(
        {'employee_id': session['employee_id']},
        {'_id': 1, 'message': 1, 'created_at': 1, 'read': 1}
    ).sort('created_at', -1))

    # Count unread notifications
    unread_count = sum(1 for notification in notifications if not notification.get('read', False))

    # Format the datetime objects to ISO strings and convert ObjectId to string
    for notification in notifications:
        notification['_id'] = str(notification['_id'])
        notification['created_at'] = notification['created_at'].isoformat()
        notification['read'] = notification.get('read', False)

    return jsonify({
        'notifications': notifications,
        'unread_count': unread_count
    })

@app.route('/api/notifications/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    notification_ids = request.json.get('notification_ids', [])
    if notification_ids:
        db.notifications.update_many(
            {
                '_id': {'$in': [ObjectId(id) for id in notification_ids]},
                'employee_id': session['employee_id']
            },
            {'$set': {'read': True}}
        )
    return jsonify({'success': True})

@app.route('/employee-management')
@login_required
def employee_management():
    if session.get('role') != 'hr':
        return redirect('/forms')
    employees = list(db.employees.find())
    return render_template('employee_management.html', employees=employees)

@app.route('/api/add-employee', methods=['POST'])
@login_required
def add_employee():
    if session.get('role') != 'hr':
        return jsonify({'error': 'Unauthorized'}), 403

    name = request.form['name']
    email = request.form['email']
    password = request.form['password']
    role = request.form['role']

    if db.employees.find_one({'email': email}):
        return jsonify({'error': 'Email already exists'}), 400

    employee = {
        'name': name,
        'email': email,
        'password': password,
        'role': role
    }
    db.employees.insert_one(employee)
    return jsonify({'success': True})

@app.route('/api/delete-employee/<employee_id>', methods=['DELETE'])
@login_required
def delete_employee(employee_id):
    if session.get('role') != 'hr':
        return jsonify({'error': 'Unauthorized'}), 403

    db.employees.delete_one({'_id': ObjectId(employee_id)})
    return jsonify({'success': True})

@app.route('/api/get-employee/<employee_id>', methods=['GET'])
@login_required
def get_employee(employee_id):
    if session.get('role') != 'hr':
        return jsonify({'error': 'Unauthorized'}), 403

    employee = db.employees.find_one({'_id': ObjectId(employee_id)})
    if not employee:
        return jsonify({'error': 'Employee not found'}), 404

    employee['_id'] = str(employee['_id'])
    return jsonify(employee)

@app.route('/api/edit-employee', methods=['POST'])
@login_required
def edit_employee():
    if session.get('role') != 'hr':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        employee_id = request.form['employee_id']
        name = request.form['name']
        email = request.form['email']
        role = request.form['role']
    except KeyError as e:
        return jsonify({'error': f'Missing field: {str(e)}'}), 400

    db.employees.update_one(
        {'_id': ObjectId(employee_id)},
        {'$set': {'name': name, 'email': email, 'role': role}}
    )
    return jsonify({'success': True})

@app.route('/all-submissions')
@login_required
def all_submissions():
    if session.get('role') != 'admin':
        return redirect('/forms')

    submissions = list(db.form_submissions.find())
    employees = list(db.employees.find())
    for submission in submissions:
        employee = db.employees.find_one({'_id': ObjectId(submission['employee_id'])})
        submission['employee_name'] = employee['name'] if employee else 'Unknown'
        submission['employee_role'] = employee['role'] if employee else 'Unknown'
    return render_template('forms_admin.html', submissions=submissions, employees=employees)

@app.route('/goals')
@login_required
def goals():
    if session.get('role') == 'admin':
        return redirect('/all-submissions')
    if session.get('role') == 'hr':
        return redirect('/forms')
    user_id = session['employee_id']
    user_goals = list(db.goals.find({'employee_id': user_id}))
    return render_template('goals.html', goals=user_goals)

@app.route('/api/goals', methods=['POST'])
@login_required
def save_goal():
    data = request.json
    goal = {
        'employee_id': session['employee_id'],
        'description': data['description'],
        'weightage': data['weightage'],
        'time_period': data['time_period'],
        'ranking': data.get('ranking'),
        'feedback': data.get('feedback'),
        'created_at': datetime.now()
    }
    db.goals.insert_one(goal)
    return jsonify({'success': True})

@app.route('/api/update-feedback/<submission_id>', methods=['POST'])
@login_required
def update_feedback(submission_id):
    if session.get('role') != 'manager':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        updates = request.json
        submission = db.form_submissions.find_one({'_id': ObjectId(submission_id)})
        
        if not submission:
            return jsonify({'error': 'Submission not found'}), 404

        # Verify the submission belongs to a team member
        team = db.teams.find_one({'manager_id': session['employee_id']})
        if not team or submission['employee_id'] not in team['member_ids']:
            return jsonify({'error': 'Unauthorized'}), 403

        # Update the submission data
        submission['data'].update(updates)
        db.form_submissions.update_one(
            {'_id': ObjectId(submission_id)},
            {'$set': {'data': submission['data']}}
        )

        # Add notification for the employee
        notification = {
            'employee_id': submission['employee_id'],
            'message': 'Your manager has provided feedback on your submission.',
            'created_at': datetime.now()
        }
        db.notifications.insert_one(notification)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit-hr-feedback/<submission_id>', methods=['POST'])
@login_required
def submit_hr_feedback(submission_id):
    if session.get('role') != 'hr':
        return jsonify({'error': 'Unauthorized'}), 403

    try:
        updates = request.json
        submission = db.form_submissions.find_one({'_id': ObjectId(submission_id)})
        
        if not submission:
            return jsonify({'error': 'Submission not found'}), 404

        # Verify the submission is from a manager
        employee = db.employees.find_one({'_id': ObjectId(submission['employee_id'])})
        if not employee or employee['role'] != 'manager':
            return jsonify({'error': 'Unauthorized - Submission is not from a manager'}), 403

        # Update the submission data
        submission['data'].update(updates)
        db.form_submissions.update_one(
            {'_id': ObjectId(submission_id)},
            {'$set': {'data': submission['data']}}
        )

        # Add notification for the manager
        notification = {
            'employee_id': submission['employee_id'],
            'message': 'HR has provided feedback on your submission.',
            'created_at': datetime.now()
        }
        db.notifications.insert_one(notification)

        return jsonify({'success': True})
    except Exception as e:
        print(f"Error in submit_hr_feedback: {str(e)}")  # For debugging
        return jsonify({'error': 'An error occurred while submitting feedback'}), 500

@app.route('/my-submissions')
@login_required
def my_submissions():
    submissions = list(db.form_submissions.find({'employee_id': session['employee_id']}))
    for submission in submissions:
        submission['_id'] = str(submission['_id'])
        submission['created_at'] = submission['created_at'].strftime('%B %d, %Y, %I:%M:%S %p')
    return render_template('my_submissions.html', submissions=submissions)

@app.route('/hr-messages')
@login_required
def hr_messages():
    if session.get('role') != 'hr':
        return redirect('/forms')
    employees = list(db.employees.find())
    categories = db.hr_messages.distinct('category')
    return render_template('hr_messages.html', employees=employees, categories=categories)

@app.route('/api/save-message', methods=['POST'])
@login_required
def save_message():
    if session.get('role') != 'hr':
        return jsonify({'error': 'Unauthorized'}), 403

    recipient = request.form['recipient']
    category = request.form.get('category')
    message = request.form['message']
    timestamp = datetime.now()

    if recipient == 'other' and not category:
        return jsonify({'error': 'Category is required for "Other"'}), 400

    message_data = {
        'employee_id': recipient if not recipient.startswith('category_') else None,
        'category': category if recipient == 'other' else recipient.split('category_')[1] if recipient.startswith('category_') else None,
        'message': message,
        'created_at': timestamp
    }
    db.hr_messages.insert_one(message_data)
    return jsonify({'success': True})

@app.route('/api/get-messages/<recipient_id>', methods=['GET'])
@login_required
def get_messages(recipient_id):
    if session.get('role') != 'hr':
        return jsonify({'error': 'Unauthorized'}), 403

    query = {'employee_id': recipient_id} if not recipient_id.startswith('category_') else {'category': recipient_id.split('category_')[1]}
    messages = list(db.hr_messages.find(query))
    for message in messages:
        message['_id'] = str(message['_id'])
        message['created_at'] = message['created_at'].isoformat()
    return jsonify({'messages': messages})

if __name__ == '__main__':
    if not db.form_status.find_one({'id': 1}):
        db.form_status.insert_one({'id': 1, 'enabled': False})

    # Add default HR employee if not exists
    if not db.employees.find_one({'email': 'hr@gmail.com'}):
        db.employees.insert_one({
            'name': 'HR',
            'email': 'hr@gmail.com',
            'password': '1234',
            'role': 'hr'
        })

    app.run(debug=True)
