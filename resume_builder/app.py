from flask import Flask, request, render_template, send_file
import spacy
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import io

app = Flask(__name__)

# Load spaCy model for NLP
nlp = spacy.load("en_core_web_sm")

# Sample data for ML skill recommendation (job title -> skills)
training_data = {
    "Software Engineer": ["Python", "Java", "SQL", "Git", "Docker"],
    "Data Scientist": ["Python", "R", "Machine Learning", "SQL", "Tableau"],
    "Product Manager": ["Agile", "Scrum", "Stakeholder Management", "Roadmap Planning"],
    "Marketing Specialist": ["SEO", "Content Creation", "Google Analytics", "Social Media"],
}

# Prepare ML model for skill recommendation
job_titles = list(training_data.keys())
skills = [" ".join(training_data[title]) for title in job_titles]
vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(skills)
y = job_titles
clf = MultinomialNB()
clf.fit(X, y)

def suggest_phrasing(text):
    """Use NLP to suggest improved phrasing for job descriptions."""
    doc = nlp(text)
    # Simple example: Replace weak verbs with stronger ones
    verb_replacements = {"worked": "collaborated", "did": "executed", "made": "developed"}
    improved_text = text
    for token in doc:
        if token.pos_ == "VERB" and token.text.lower() in verb_replacements:
            improved_text = improved_text.replace(token.text, verb_replacements[token.text.lower()])
    return improved_text

def recommend_skills(job_title):
    """Use ML to recommend skills based on job title."""
    input_vec = vectorizer.transform([job_title])
    predicted_title = clf.predict(input_vec)[0]
    return training_data.get(predicted_title, ["Communication", "Teamwork"])

# Define resume templates
def apply_template(name, email, job_title, enhanced_experience, education, all_skills, template):
    if template == "professional":
        resume_content = f"""
{name.upper()}
{email} | {job_title}

PROFESSIONAL EXPERIENCE
{'=' * 50}
"""
        for exp in enhanced_experience:
            resume_content += f"{exp}\n\n"

        resume_content += f"""
EDUCATION
{'=' * 50}
"""
        for edu in education:
            resume_content += f"{edu}\n\n"

        resume_content += f"""
SKILLS
{'=' * 50}
{', '.join(all_skills)}
"""
    elif template == "modern":
        resume_content = f"""
*** {name.upper()} ***
{job_title}
Contact: {email}

-- Work Experience --
{'-' * 30}
"""
        for exp in enhanced_experience:
            resume_content += f"• {exp}\n\n"

        resume_content += f"""
-- Education --
{'-' * 30}
"""
        for edu in education:
            resume_content += f"• {edu}\n\n"

        resume_content += f"""
-- Skills --
{'-' * 30}
{'; '.join(all_skills)}
"""
    else:  # creative
        resume_content = f"""
🌟 {name.upper()} 🌟
{job_title} | {email}

✨ Experience ✨
{'*' * 40}
"""
        for exp in enhanced_experience:
            resume_content += f"→ {exp}\n\n"

        resume_content += f"""
✨ Education ✨
{'*' * 40}
"""
        for edu in education:
            resume_content += f"→ {edu}\n\n"

        resume_content += f"""
✨ Skills ✨
{'*' * 40}
{', '.join(all_skills)}
"""
    return resume_content

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/build_resume', methods=['POST'])
def build_resume():
    # Collect user input
    name = request.form.get('name')
    email = request.form.get('email')
    job_title = request.form.get('job_title')
    experience = request.form.getlist('experience[]')
    education = request.form.getlist('education[]')
    skills = request.form.getlist('skills[]')
    template = request.form.get('template', 'professional')  # Default to professional

    # Apply NLP to enhance experience descriptions
    enhanced_experience = [suggest_phrasing(exp) for exp in experience]

    # Recommend additional skills using ML
    recommended_skills = recommend_skills(job_title)
    all_skills = list(set(skills + recommended_skills))

    # Generate resume content using selected template
    resume_content = apply_template(name, email, job_title, enhanced_experience, education, all_skills, template)

    # Save resume to a temporary file
    resume_file = io.StringIO(resume_content)
    resume_file.seek(0)

    return send_file(
        io.BytesIO(resume_content.encode()),
        mimetype='text/plain',
        as_attachment=True,
        download_name=f"{name}_resume.txt"
    )

if __name__ == '__main__':
    app.run(debug=True)