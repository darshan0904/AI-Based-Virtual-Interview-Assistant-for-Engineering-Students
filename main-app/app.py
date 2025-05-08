from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from aptitude_manager import AptitudeTestManager
from interview_manager import InterviewManager
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

# Directories
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Managers
aptitude_manager = AptitudeTestManager(
    general_csv='clean_general_aptitude_dataset.csv',
    logical_csv='logical_reasoning_questions.csv',
    api_key='AIzaSyAA92C3_BnZiH-2V47VV32OdgS6Trpc8FQ'
)
interview_manager = InterviewManager(
    upload_folder=UPLOAD_FOLDER,
    api_key='AIzaSyAA92C3_BnZiH-2V47VV32OdgS6Trpc8FQ'
)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Web App Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        if not name or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('signup'))
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered. Please login.', 'warning')
            return redirect(url_for('login'))
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(name=name, email=email, password=hashed_password)
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully. Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error creating account: {str(e)}', 'danger')
            return redirect(url_for('signup'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    return render_template('dashboard.html', name=session.get('user_name'))

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home'))

# Aptitude Routes
@app.route('/aptitude/', methods=['GET', 'POST'])
def aptitude_index():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    return render_template('aptitude_index.html', domains=aptitude_manager.supported_domains)

@app.route('/aptitude/start_test', methods=['POST'])
def start_test():
    domain = (request.form.get('domain') or request.form.get('domain_input')).upper().strip()
    result = aptitude_manager.start_test(domain, session)
    if 'error' in result:
        return jsonify(result), result.get('status', 400)
    return jsonify(result)

@app.route('/aptitude/submit_test', methods=['POST'])
def submit_test():
    answers = request.json.get('answers', [])
    result = aptitude_manager.submit_test(answers, session)
    if 'error' in result:
        return jsonify(result), result.get('status', 400)
    if result['total_score'] >= 7:
        result['status'] = 'pass'
        result['redirect'] = url_for('interview_index')
    else:
        flash('You did not pass the aptitude test. Please try again.', 'danger')
        result['status'] = 'fail'
        result['redirect'] = url_for('aptitude_index')
    return jsonify(result)

# AI Interview Routes
@app.route('/interview/', methods=['GET', 'POST'])
def interview_index():
    if 'user_id' not in session or session.get('total_score', 0) < 7:
        flash('You must pass the aptitude test first.', 'warning')
        return redirect(url_for('aptitude_index'))
    return render_template('interview_index.html', domains=interview_manager.domains)

@app.route('/interview/get_roles', methods=['POST'])
async def get_roles():
    data = request.json
    domain = data.get('domain')
    return jsonify({"roles": interview_manager.get_roles(domain)})

@app.route('/interview/start_interview', methods=['POST'])
async def start_interview():
    name = session['user_name']
    domain = request.form.get('domain')
    role = request.form.get('role')
    session_id = interview_manager.start_interview(name, domain, role)
    return jsonify({"session_id": session_id})

@app.route('/interview/generate_questions/<session_id>', methods=['POST'])
async def generate_questions(session_id):
    data = request.json
    domain = data.get('domain')
    role = data.get('role')
    name = session.get('user_name')
    result = interview_manager.generate_questions(session_id, domain, role, name)
    if 'error' in result:
        return jsonify(result), result.get('status', 404)
    return jsonify(result)

@app.route('/interview/next_question/<session_id>', methods=['POST'])
async def next_question(session_id):
    data = request.json
    question = data.get('question')
    result = interview_manager.next_question(session_id, question)
    return jsonify(result)

@app.route('/Uploads/imp/questions/<filename>')
def serve_imp_question(filename):
    return send_file(os.path.join(interview_manager.imp_question_folder, filename), mimetype='audio/wav')

@app.route('/interview/record_response/<session_id>', methods=['POST'])
async def record_response(session_id):
    audio = request.files.get('audio')
    video = request.files.get('video')
    transcript = request.form.get('transcript', 'No response recorded')
    question_idx = interview_manager.sessions.get(session_id, {}).get('current_question', 1)
    result = interview_manager.record_response(session_id, audio, video, transcript, question_idx)
    if 'error' in result:
        return jsonify(result), result.get('status', 404)
    return jsonify(result)

if __name__ == '__main__':
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=9999)