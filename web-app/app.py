from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)
UPLOAD_FOLDER = 'Uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    resume_path = db.Column(db.String(500), nullable=True)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/info')
def info():
    return render_template('info.html')

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
        if not email or not password:
            flash('Email and password are required.', 'danger')
            return redirect(url_for('login'))
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['user_name'] = user.name
            flash('Login successful!', 'success')
            return redirect(url_for('post_login'))
        else:
            flash('Invalid email or password.', 'danger')
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/post_login')
def post_login():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    return render_template('post_login.html')

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        flash('User not found. Please log in again.', 'danger')
        session.clear()
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Update name
        new_name = request.form.get('name')
        if not new_name:
            flash('Name is required.', 'danger')
            return redirect(url_for('profile'))
        
        # Handle resume upload
        resume = request.files.get('resume')
        resume_path = user.resume_path  # Keep existing path unless a new file is uploaded

        if resume and resume.filename:
            if allowed_file(resume.filename):
                filename = secure_filename(resume.filename)
                resume_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    resume.save(resume_path)
                except Exception as e:
                    flash(f'Error saving resume: {str(e)}', 'danger')
                    return redirect(url_for('profile'))
            else:
                flash('Invalid file type. Only PDF, DOC, or DOCX allowed.', 'danger')
                return redirect(url_for('profile'))

        # Update user in database
        try:
            user.name = new_name
            user.resume_path = resume_path
            session['user_name'] = new_name  # Update session name
            db.session.commit()
            flash('Profile updated successfully!', 'success')
        except Exception as e:
            flash(f'Error updating profile: {str(e)}', 'danger')
        
        return redirect(url_for('profile'))

    return render_template('profile.html', user=user)

@app.route('/resume_builder')
def resume_builder():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    return render_template('resume_builder.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('home'))

@app.route('/select_domain', methods=['GET', 'POST'])
def select_domain():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    if request.method == 'POST':
        domain = request.form.get('domain')
        if not domain:
            flash('Please select a domain.', 'danger')
            return redirect(url_for('select_domain'))
        session['selected_domain'] = domain
        return redirect(url_for('resume_upload'))
    return render_template('select_domain.html')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'pdf', 'doc', 'docx'}

@app.route('/resume_upload', methods=['GET', 'POST'])
def resume_upload():
    if 'user_id' not in session or 'selected_domain' not in session:
        flash('Please complete the previous steps first.', 'warning')
        return redirect(url_for('select_domain'))

    domain = session['selected_domain']
    job_roles = {
        "Computer Science": [
            "Software Developer", "Data Scientist", "AI Engineer", "Web Developer",
            "Cybersecurity Analyst", "Cloud Engineer", "DevOps Engineer", "Mobile App Developer",
            "Game Developer", "Blockchain Developer"
        ],
        "Electronics and Communication": [
            "Embedded Systems Engineer", "VLSI Design Engineer", "Signal Processing Engineer", "Telecom Engineer",
            "RF Engineer", "IoT Developer", "Control Systems Engineer", "Network Engineer"
        ],
        "Mechanical": [
            "Design Engineer", "Automobile Engineer", "Manufacturing Engineer", "Thermal Engineer",
            "Aerospace Engineer", "Robotics Engineer", "HVAC Engineer", "Maintenance Engineer"
        ],
        "Civil": [
            "Structural Engineer", "Construction Manager", "Geotechnical Engineer", "Urban Planner",
            "Transportation Engineer", "Environmental Engineer", "Surveyor", "Site Engineer"
        ]
    }

    roles = job_roles.get(domain, [])

    if request.method == 'POST':
        selected_role = request.form.get('role')
        selected_roles = [selected_role] if selected_role else []

        resume = request.files.get('resume')

        print("Form data:", request.form)
        print("Selected role:", selected_role)
        print("Selected roles (combined):", selected_roles)
        print("Resume file:", resume)

        if not selected_roles:
            flash('Please select a job role.', 'danger')
            return redirect(url_for('resume_upload'))

        resume_path = None
        if resume and resume.filename:
            if allowed_file(resume.filename):
                filename = secure_filename(resume.filename)
                resume_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                try:
                    resume.save(resume_path)
                except Exception as e:
                    flash(f'Error saving resume: {str(e)}', 'danger')
                    return redirect(url_for('resume_upload'))
            else:
                flash('Invalid file type. Only PDF, DOC, or DOCX allowed.', 'danger')
                return redirect(url_for('resume_upload'))

        session['selected_roles'] = selected_roles
        session['resume_path'] = resume_path

        try:
            user = User.query.get(session['user_id'])
            if not user:
                flash('User not found. Please log in again.', 'danger')
                return redirect(url_for('login'))
            user.resume_path = resume_path
            db.session.commit()
        except Exception as e:
            flash(f'Database error: {str(e)}', 'danger')
            return redirect(url_for('resume_upload'))

        flash('Job role and resume submitted successfully!', 'success')
        return redirect(url_for('aptitude_test'))

    return render_template('resume_upload.html', domain=domain, roles=roles)

@app.route('/aptitude_test', methods=['GET', 'POST'])
def aptitude_test():
    if 'user_id' not in session or 'selected_domain' not in session:
        flash('Please complete the previous steps first.', 'warning')
        return redirect(url_for('select_domain'))

    questions = [
        {
            'id': 1,
            'question': 'What is the time complexity of binary search?',
            'options': ['O(n)', 'O(log n)', 'O(n^2)', 'O(n log n)'],
            'correct': 'O(log n)'
        },
        {
            'id': 2,
            'question': 'Which data structure uses LIFO?',
            'options': ['Queue', 'Stack', 'Array', 'Linked List'],
            'correct': 'Stack'
        },
        {
            'id': 3,
            'question': 'What does SQL stand for?',
            'options': ['Structured Query Language', 'Simple Query Language', 'Sequential Query Language', 'Standard Query Language'],
            'correct': 'Structured Query Language'
        },
        {
            'id': 4,
            'question': 'Which of these is not a programming language?',
            'options': ['Python', 'HTML', 'Java', 'C++'],
            'correct': 'HTML'
        },
        {
            'id': 5,
            'question': 'What is the purpose of a constructor in OOP?',
            'options': ['To destroy objects', 'To initialize objects', 'To copy objects', 'To call methods'],
            'correct': 'To initialize objects'
        },
        {
            'id': 6,
            'question': 'Which protocol is used for secure web browsing?',
            'options': ['HTTP', 'FTP', 'HTTPS', 'SMTP'],
            'correct': 'HTTPS'
        },
        {
            'id': 7,
            'question': 'What is the output of 2 + 2 * 3 in Python?',
            'options': ['12', '8', '10', '6'],
            'correct': '8'
        },
        {
            'id': 8,
            'question': 'Which sorting algorithm has the best average-case time complexity?',
            'options': ['Bubble Sort', 'Quick Sort', 'Selection Sort', 'Insertion Sort'],
            'correct': 'Quick Sort'
        },
        {
            'id': 9,
            'question': 'What does API stand for?',
            'options': ['Application Programming Interface', 'Automated Program Integration', 'Application Process Interface', 'Advanced Programming Interface'],
            'correct': 'Application Programming Interface'
        },
        {
            'id': 10,
            'question': 'Which of these is a NoSQL database?',
            'options': ['MySQL', 'PostgreSQL', 'MongoDB', 'SQLite'],
            'correct': 'MongoDB'
        }
    ]

    if request.method == 'POST':
        score = 0
        total = len(questions)
        user_answers = {}

        for q in questions:
            answer = request.form.get(f'question_{q["id"]}')
            user_answers[q['id']] = answer
            if answer == q['correct']:
                score += 1

        session['test_score'] = score
        session['total_questions'] = total
        session['user_answers'] = user_answers

        return redirect(url_for('test_results'))

    return render_template('aptitude_test.html', questions=questions)

@app.route('/test_results')
def test_results():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    if 'test_score' not in session:
        flash('No test results available. Please take the test first.', 'warning')
        return redirect(url_for('aptitude_test'))

    score = session['test_score']
    total = session['total_questions']
    passed = score >= 7

    if passed:
        flash(f'Congratulations! You scored {score}/{total} and have passed the aptitude test!', 'success')
    else:
        flash(f'You scored {score}/{total}. Unfortunately, you did not pass. Please practice and try again.', 'danger')

    return render_template('test_results.html', score=score, total=total, passed=passed)

@app.route('/interview_instructions')
def interview_instructions():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    if 'test_score' not in session or session['test_score'] < 7:
        flash('You must pass the aptitude test to access this phase.', 'warning')
        return redirect(url_for('aptitude_test'))
    return render_template('interview_instructions.html', name=session.get('user_name'))

@app.route('/permission_request', methods=['GET', 'POST'])
def permission_request():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    if 'test_score' not in session or session['test_score'] < 7:
        flash('You must pass the aptitude test to access this phase.', 'warning')
        return redirect(url_for('aptitude_test'))

    if request.method == 'POST':
        mic_permission = request.form.get('mic_permission')
        cam_permission = request.form.get('cam_permission')
        if mic_permission == 'on' or cam_permission == 'on':
            return redirect(url_for('video_interview'))
        flash('Please grant microphone and/or camera permission to proceed.', 'warning')
        return redirect(url_for('permission_request'))

    return render_template('permission_request.html', name=session.get('user_name'))

@app.route('/video_interview')
def video_interview():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    if 'test_score' not in session or session['test_score'] < 7:
        flash('You must pass the aptitude test to access this phase.', 'warning')
        return redirect(url_for('aptitude_test'))
    return render_template('video_interview.html', name=session.get('user_name'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in first.', 'warning')
        return redirect(url_for('login'))
    return render_template('dashboard.html', name=session.get('user_name'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True,port=9999)