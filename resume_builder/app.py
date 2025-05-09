from flask import Flask, request, render_template, send_file
import spacy
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

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
        resume_content = [
            Paragraph(f"<b>{name.upper()}</b>", ParagraphStyle(name="Name", fontSize=16, spaceAfter=6)),
            Paragraph(f"{email} | {job_title}", ParagraphStyle(name="Contact", fontSize=12, spaceAfter=12)),
            Paragraph("<b>PROFESSIONAL EXPERIENCE</b>", ParagraphStyle(name="Heading", fontSize=14, spaceBefore=12, spaceAfter=6)),
            Paragraph("=" * 50, ParagraphStyle(name="Divider", fontSize=10, spaceAfter=6))
        ]
        for exp in enhanced_experience:
            resume_content.append(Paragraph(exp, ParagraphStyle(name="Body", fontSize=12, spaceAfter=6)))
            resume_content.append(Spacer(1, 0.2 * inch))
        
        resume_content.extend([
            Paragraph("<b>EDUCATION</b>", ParagraphStyle(name="Heading", fontSize=14, spaceBefore=12, spaceAfter=6)),
            Paragraph("=" * 50, ParagraphStyle(name="Divider", fontSize=10, spaceAfter=6))
        ])
        for edu in education:
            resume_content.append(Paragraph(edu, ParagraphStyle(name="Body", fontSize=12, spaceAfter=6)))
            resume_content.append(Spacer(1, 0.2 * inch))
        
        resume_content.extend([
            Paragraph("<b>SKILLS</b>", ParagraphStyle(name="Heading", fontSize=14, spaceBefore=12, spaceAfter=6)),
            Paragraph("=" * 50, ParagraphStyle(name="Divider", fontSize=10, spaceAfter=6)),
            Paragraph(", ".join(all_skills), ParagraphStyle(name="Body", fontSize=12))
        ])
    
    elif template == "modern":
        resume_content = [
            Paragraph(f"<b>{name.upper()}</b>", ParagraphStyle(name="Name", fontSize=16, spaceAfter=6)),
            Paragraph(f"{job_title}", ParagraphStyle(name="Title", fontSize=12, spaceAfter=6)),
            Paragraph(f"Contact: {email}", ParagraphStyle(name="Contact", fontSize=12, spaceAfter=12)),
            Paragraph("<b>-- Work Experience --</b>", ParagraphStyle(name="Heading", fontSize=14, spaceBefore=12, spaceAfter=6)),
            Paragraph("-" * 30, ParagraphStyle(name="Divider", fontSize=10, spaceAfter=6))
        ]
        for exp in enhanced_experience:
            resume_content.append(Paragraph(f"• {exp}", ParagraphStyle(name="Body", fontSize=12, spaceAfter=6)))
            resume_content.append(Spacer(1, 0.2 * inch))
        
        resume_content.extend([
            Paragraph("<b>-- Education --</b>", ParagraphStyle(name="Heading", fontSize=14, spaceBefore=12, spaceAfter=6)),
            Paragraph("-" * 30, ParagraphStyle(name="Divider", fontSize=10, spaceAfter=6))
        ])
        for edu in education:
            resume_content.append(Paragraph(f"• {edu}", ParagraphStyle(name="Body", fontSize=12, spaceAfter=6)))
            resume_content.append(Spacer(1, 0.2 * inch))
        
        resume_content.extend([
            Paragraph("<b>-- Skills --</b>", ParagraphStyle(name="Heading", fontSize=14, spaceBefore=12, spaceAfter=6)),
            Paragraph("-" * 30, ParagraphStyle(name="Divider", fontSize=10, spaceAfter=6)),
            Paragraph("; ".join(all_skills), ParagraphStyle(name="Body", fontSize=12))
        ])
    
    else:  # creative
        resume_content = [
            Paragraph(f"<b>{name.upper()}</b>", ParagraphStyle(name="Name", fontSize=16, spaceAfter=6)),
            Paragraph(f"{job_title} | {email}", ParagraphStyle(name="Contact", fontSize=12, spaceAfter=12)),
            Paragraph("<b>✨ Experience ✨</b>", ParagraphStyle(name="Heading", fontSize=14, spaceBefore=12, spaceAfter=6)),
            Paragraph("*" * 40, ParagraphStyle(name="Divider", fontSize=10, spaceAfter=6))
        ]
        for exp in enhanced_experience:
            resume_content.append(Paragraph(f"→ {exp}", ParagraphStyle(name="Body", fontSize=12, spaceAfter=6)))
            resume_content.append(Spacer(1, 0.2 * inch))
        
        resume_content.extend([
            Paragraph("<b>✨ Education ✨</b>", ParagraphStyle(name="Heading", fontSize=14, spaceBefore=12, spaceAfter=6)),
            Paragraph("*" * 40, ParagraphStyle(name="Divider", fontSize=10, spaceAfter=6))
        ])
        for edu in education:
            resume_content.append(Paragraph(f"→ {edu}", ParagraphStyle(name="Body", fontSize=12, spaceAfter=6)))
            resume_content.append(Spacer(1, 0.2 * inch))
        
        resume_content.extend([
            Paragraph("<b>✨ Skills ✨</b>", ParagraphStyle(name="Heading", fontSize=14, spaceBefore=12, spaceAfter=6)),
            Paragraph("*" * 40, ParagraphStyle(name="Divider", fontSize=10, spaceAfter=6)),
            Paragraph(", ".join(all_skills), ParagraphStyle(name="Body", fontSize=12))
        ])
    
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

    # Create PDF
    pdf_file = io.BytesIO()
    doc = SimpleDocTemplate(pdf_file, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    doc.build(resume_content)

    pdf_file.seek(0)

    return send_file(
        pdf_file,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"{name}_resume.pdf"
    )

if __name__ == '__main__':
    app.run(debug=True)