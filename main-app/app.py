from flask import Flask, render_template, request, redirect, url_for, session
app = Flask(__name__)
app.secret_key = 'main-app-secret-key-456'  # Required for session

# Simulated URLs for the separate Flask applications
RESUME_HELP_URL = "http://localhost:5001/"
APTITUDE_TEST_URL = "http://localhost:5002/"
MOCK_INTERVIEW_URL = "http://localhost:5003/"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form.get('name')
        age = request.form.get('age')
        gender = request.form.get('gender')
        session['user_name'] = name  # Store name in session
        return redirect(url_for('options'))
    return render_template('index.html')

@app.route('/options')
def options():
    user_name = session.get('user_name', '')  # Get name from session
    # Append name as query parameter to Aptitude URL
    aptitude_url_with_name = f"{APTITUDE_TEST_URL}?name={user_name}"
    return render_template('options.html', 
                         resume_url=RESUME_HELP_URL,
                         aptitude_url=aptitude_url_with_name,
                         interview_url=MOCK_INTERVIEW_URL)

if __name__ == '__main__':
    app.run(debug=True, port=5000)