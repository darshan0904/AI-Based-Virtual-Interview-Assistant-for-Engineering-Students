from flask import Flask, render_template, request, redirect, url_for, session
app = Flask(__name__)
app.secret_key = 'main-app-secret-key-456'

RESUME_BUILDER_URL = "http://localhost:9001/"
RESUME_ANALYSIS_URL = "http://localhost:9002/"
APTITUDE_TEST_URL = "http://localhost:9003/"
MOCK_INTERVIEW_URL = "http://localhost:9999/"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form.get('name')
        age = request.form.get('age')
        gender = request.form.get('gender')
        session['user_name'] = name
        return redirect(url_for('options'))
    return render_template('index.html')

@app.route('/options')
def options():
    user_name = session.get('user_name', '')
    resume_builder_url = f"{RESUME_BUILDER_URL}?name={user_name}"
    resume_analysis_url = f"{RESUME_ANALYSIS_URL}?name={user_name}"
    aptitude_url = f"{APTITUDE_TEST_URL}?name={user_name}"
    interview_url = f"{MOCK_INTERVIEW_URL}?name={user_name}"
    return render_template('options.html', 
                         resume_builder_url=resume_builder_url,
                         resume_analysis_url=resume_analysis_url,
                         aptitude_url=aptitude_url,
                         interview_url=interview_url)

if __name__ == '__main__':
    app.run(debug=True, port=5000)