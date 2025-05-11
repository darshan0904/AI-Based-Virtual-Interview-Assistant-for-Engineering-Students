import os
from flask import Flask, request, render_template, send_file
import PyPDF2
import spacy
import re
import string
from datetime import datetime
import io
from sentence_transformers import SentenceTransformer, util
import google.generativeai as genai
import numpy as np
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

app = Flask(__name__)

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY not found in environment variables.")

# Configure Gemini API if key is available
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Error configuring Gemini API: {e}")

# Load NLP and AI models with fallbacks
try:
    nlp = spacy.load("en_core_web_sm")
except Exception as e:
    print(f"Error loading spaCy model: {e}")
    nlp = None

try:
    sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
except Exception as e:
    print(f"Error loading SentenceTransformer: {e}")
    sentence_model = None

# Store generated files in memory
app.config['REPORT_BUFFER'] = None
app.config['RESUME_BUFFER'] = None

def clean_text(text):
    """Clean text by removing special characters and extra spaces."""
    text = re.sub(r'[•\u0080-\uFFFF]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_text_from_pdf(pdf_file_stream):
    """Extract text from a PDF resume stream."""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file_stream)
        text = ' '.join(page.extract_text() or '' for page in pdf_reader.pages)
        return clean_text(text)
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def preprocess_text(text):
    """Clean and preprocess text using spaCy."""
    if not nlp:
        text = text.lower().translate(str.maketrans("", "", string.punctuation))
        return text.split()
    text = text.lower().translate(str.maketrans("", "", string.punctuation))
    doc = nlp(text)
    return [token.lemma_ for token in doc if not token.is_stop and not token.is_space]

def extract_entities(text):
    """Extract skills from text."""
    if not nlp:
        return set(), set()

    doc = nlp(text.lower())
    skills = set()
    common_skills = {
        "python", "java", "javascript", "sql", "html", "css", "react", "pandas", "aws", "azure",
        "agile", "mysql", "docker", "git", "linux", "tableau", "power bi", "excel", "r",
        "machine learning", "data analysis", "data visualization", "statistical analysis"
    }

    excluded_terms = {
        "email", "education", "project", "certification", "science", "technology"
    }

    for token in doc:
        token_text = token.lemma_.strip()
        if token_text in common_skills and token_text not in excluded_terms:
            skills.add(token_text)

    return skills, set()

def compute_similarity(resume_text, job_keywords):
    """Compute semantic similarity using sentence transformers."""
    if not sentence_model:
        return 50.0
    job_text = " ".join(job_keywords)
    resume_embedding = sentence_model.encode(resume_text, convert_to_tensor=True)
    job_embedding = sentence_model.encode(job_text, convert_to_tensor=True)
    similarity = util.cos_sim(resume_embedding, job_embedding).item()
    return similarity * 100

def analyze_with_gemini(resume_text, job_role, resume_tokens):
    """Generate keywords and recommendations using Gemini API or fallback."""
    if not GEMINI_API_KEY:
        keywords = set(["development", "programming", "coding"])
        if "software" in job_role.lower():
            keywords.update(["python", "java", "javascript", "sql", "aws", "agile"])
        elif "data" in job_role.lower():
            keywords.update(["python", "sql", "tableau", "power bi", "data analysis"])
        recommendations = "Complete a relevant online course to enhance your skills."
        return keywords, recommendations

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        For the job role '{job_role}':
        1. List 10-15 specific technical skills, tools, or methodologies required (e.g., 'python, sql, tableau' for data analyst).
        2. Suggest 2-3 actionable steps to acquire missing skills for the role (under 100 words).
        Format:
        Keywords: <comma-separated list>
        Recommendations: <text>
        """
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        keywords, recommendations = None, None
        for line in response_text.split('\n'):
            if line.startswith("Keywords:"):
                keywords = set(kw.strip().lower() for kw in line.replace("Keywords:", "").split(","))
            elif line.startswith("Recommendations:"):
                recommendations = line.replace("Recommendations:", "").strip()

        if not keywords:
            keywords = set(["development", "programming", "coding"])
            if "software" in job_role.lower():
                keywords.update(["python", "java", "javascript", "sql", "aws", "agile"])
        if not recommendations:
            recommendations = "Complete a relevant online course."

        return keywords, recommendations
    except Exception as e:
        print(f"Error with Gemini API: {e}")
        keywords = set(["development", "programming", "coding"])
        if "data" in job_role.lower():
            keywords.update(["python", "sql", "tableau", "power bi", "data analysis"])
        recommendations = "Complete a relevant online course."
        return keywords, recommendations

def analyze_resume(resume_text, job_role):
    """Analyze resume using NLP and Gemini API."""
    resume_tokens = preprocess_text(resume_text)
    resume_skills, _ = extract_entities(resume_text)
    
    job_keywords, recommendations = analyze_with_gemini(resume_text, job_role, resume_tokens)
    
    matched_keywords = set()
    for token in resume_tokens:
        for keyword in job_keywords:
            if token in keyword or keyword in token:
                matched_keywords.add(keyword)
    
    keyword_match_percentage = (len(matched_keywords) / len(job_keywords)) * 100 if job_keywords else 0
    semantic_score = compute_similarity(resume_text, job_keywords)
    final_score = 0.6 * semantic_score + 0.4 * min(keyword_match_percentage, 80)

    return {
        "score": round(final_score, 2),
        "semantic_score": round(semantic_score, 2),
        "keyword_match_percentage": round(keyword_match_percentage, 2),
        "matched_keywords": list(matched_keywords),
        "total_keywords": len(job_keywords),
        "job_keywords": list(job_keywords),
        "missing_keywords": list(job_keywords - matched_keywords),
        "recommendations": recommendations,
        "resume_skills": resume_skills
    }

def generate_analysis_report(analysis, job_role, pdf_buffer):
    """Generate a resume analysis report in plain text and PDF."""
    current_date = datetime.now().strftime("%B %d, %Y")
    plain_text_report = f"""Resume Analysis Report
Date: {current_date}
Target Position: {job_role}

1. Summary
- Overall Score: {analysis['score']}/100
- Semantic Alignment: {analysis['semantic_score']}% (contextual match with job requirements)
- Keyword Match: {analysis['keyword_match_percentage']}% ({len(analysis['matched_keywords'])}/{analysis['total_keywords']})

2. Keywords
- Job-Relevant Keywords: {', '.join(sorted(analysis['job_keywords'])) if analysis['job_keywords'] else 'None'}
- Matched: {', '.join(sorted(analysis['matched_keywords'])) if analysis['matched_keywords'] else 'None'}
- Missing: {', '.join(sorted(analysis['missing_keywords'])) if analysis['missing_keywords'] else 'None'}

3. Skills Detected
- Resume Skills: {', '.join(sorted(analysis['resume_skills'])) if analysis['resume_skills'] else 'None'}

4. Recommendations
- Missing Skills: {', '.join(sorted(analysis['missing_keywords'])) if analysis['missing_keywords'] else 'None'}
- Recommendations: {analysis['recommendations']}

Best of luck with your application!
AI Resume Analyzer Team
"""

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name='TitleStyle', fontName='Helvetica-Bold', fontSize=18, alignment=1, spaceAfter=16, textColor=colors.HexColor('#1E3A8A'))
    normal_style = ParagraphStyle(name='NormalStyle', fontName='Helvetica', fontSize=11, leading=14, spaceAfter=6)
    heading_style = ParagraphStyle(name='HeadingStyle', fontName='Helvetica-Bold', fontSize=14, spaceBefore=12, spaceAfter=8, textColor=colors.HexColor('#1E3A8A'))
    bullet_style = ParagraphStyle(name='BulletStyle', fontName='Helvetica', fontSize=11, leftIndent=20, firstLineIndent=-10, spaceAfter=4)

    elements = []
    elements.append(Paragraph("Resume Analysis Report", title_style))
    elements.append(Paragraph(f"Date: {current_date}", normal_style))
    elements.append(Paragraph(f"Target Position: {job_role}", normal_style))
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph("1. Summary", heading_style))
    elements.append(Paragraph(f"• Overall Score: {analysis['score']}/100", bullet_style))
    elements.append(Paragraph(f"• Semantic Alignment: {analysis['semantic_score']}%", bullet_style))
    elements.append(Paragraph(f"• Keyword Match: {analysis['keyword_match_percentage']}% ({len(analysis['matched_keywords'])}/{analysis['total_keywords']})", bullet_style))
    
    elements.append(Paragraph("2. Keywords", heading_style))
    elements.append(Paragraph(f"• Job-Relevant Keywords: {', '.join(sorted(analysis['job_keywords']))}", bullet_style))
    elements.append(Paragraph(f"• Matched: {', '.join(sorted(analysis['matched_keywords']))}", bullet_style))
    elements.append(Paragraph(f"• Missing: {', '.join(sorted(analysis['missing_keywords']))}", bullet_style))

    elements.append(Paragraph("3. Skills Detected", heading_style))
    elements.append(Paragraph(f"• Resume Skills: {', '.join(sorted(analysis['resume_skills']))}", bullet_style))

    elements.append(Paragraph("4. Recommendations", heading_style))
    elements.append(Paragraph(f"• Missing Skills: {', '.join(sorted(analysis['missing_keywords']))}", bullet_style))
    elements.append(Paragraph(f"• Recommendations: {analysis['recommendations']}", bullet_style))

    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, rightMargin=inch, leftMargin=inch, topMargin=inch, bottomMargin=inch)
    doc.build(elements)

    return plain_text_report

def generate_resume_pdf(name, email, job_title, template, experiences, educations, skills, pdf_buffer):
    """Generate a resume PDF based on user input and template."""
    styles = getSampleStyleSheet()
    template_styles = {
        "professional": {
            "title": ParagraphStyle(name='Title', fontName='Helvetica-Bold', fontSize=16, alignment=1, spaceAfter=12),
            "heading": ParagraphStyle(name='Heading', fontName='Helvetica-Bold', fontSize=12, spaceBefore=10, spaceAfter=6),
            "normal": ParagraphStyle(name='Normal', fontName='Helvetica', fontSize=10, leading=12)
        },
        "modern": {
            "title": ParagraphStyle(name='Title', fontName='Helvetica-Bold', fontSize=18, alignment=1, spaceAfter=14, textColor=colors.HexColor('#2E4053')),
            "heading": ParagraphStyle(name='Heading', fontName='Helvetica-Bold', fontSize=12, spaceBefore=12, spaceAfter=8, textColor=colors.HexColor('#2E4053')),
            "normal": ParagraphStyle(name='Normal', fontName='Helvetica', fontSize=10, leading=12)
        },
        "creative": {
            "title": ParagraphStyle(name='Title', fontName='Helvetica-Bold', fontSize=20, alignment=1, spaceAfter=16, textColor=colors.HexColor('#C0392B')),
            "heading": ParagraphStyle(name='Heading', fontName='Helvetica-Bold', fontSize=12, spaceBefore=12, spaceAfter=8, textColor=colors.HexColor('#C0392B')),
            "normal": ParagraphStyle(name='Normal', fontName='Helvetica', fontSize=10, leading=12)
        }
    }

    style = template_styles.get(template, template_styles["professional"])
    
    elements = []
    elements.append(Paragraph(name, style['title']))
    elements.append(Paragraph(f"{email} | {job_title}", style['normal']))
    elements.append(Spacer(1, 0.3 * inch))

    elements.append(Paragraph("Work Experience", style['heading']))
    for exp in experiences:
        if exp.strip():
            elements.append(Paragraph(exp, style['normal']))
    elements.append(Spacer(1, 0.2 * inch))

    elements.append(Paragraph("Education", style['heading']))
    for edu in educations:
        if edu.strip():
            elements.append(Paragraph(edu, style['normal']))
    elements.append(Spacer(1, 0.2 * inch))

    elements.append(Paragraph("Skills", style['heading']))
    skills_text = ", ".join([skill.strip() for skill in skills if skill.strip()])
    elements.append(Paragraph(skills_text, style['normal']))

    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, rightMargin=inch, leftMargin=inch, topMargin=inch, bottomMargin=inch)
    doc.build(elements)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['GET', 'POST'])
def analyze():
    if request.method == 'GET':
        return render_template('analyze.html', error=None, report_content=None)

    job_role = request.form.get('job_role')
    resume_file = request.files.get('resume_file')

    if not job_role or not resume_file:
        return render_template('analyze.html', error="Job role and resume file are required.", report_content=None)

    if not resume_file.filename.lower().endswith('.pdf'):
        return render_template('analyze.html', error="Upload a valid PDF file.", report_content=None)

    try:
        resume_stream = io.BytesIO(resume_file.read())
        resume_text = extract_text_from_pdf(resume_stream)
        if "Error" in resume_text:
            return render_template('analyze.html', error=resume_text, report_content=None)

        analysis = analyze_resume(resume_text, job_role)
        pdf_buffer = io.BytesIO()
        plain_text_report = generate_analysis_report(analysis, job_role, pdf_buffer)

        pdf_buffer.seek(0)
        app.config['REPORT_BUFFER'] = pdf_buffer

        return render_template('analyze.html', error=None, report_content=plain_text_report)
    except Exception as e:
        print(f"Error processing request: {e}")
        return render_template('analyze.html', error=f"Error processing request: {str(e)}", report_content=None)

@app.route('/build', methods=['GET', 'POST'])
def build():
    if request.method == 'GET':
        return render_template('build.html', error=None, report_content=None)

    try:
        name = request.form.get('name')
        email = request.form.get('email')
        job_title = request.form.get('job_title')
        template = request.form.get('template')
        experiences = request.form.getlist('experience[]')
        educations = request.form.getlist('education[]')
        skills = request.form.getlist('skills[]')

        if not all([name, email, job_title, template]):
            return render_template('build.html', error="All personal information fields are required.", report_content=None)

        pdf_buffer = io.BytesIO()
        generate_resume_pdf(name, email, job_title, template, experiences, educations, skills, pdf_buffer)
        
        pdf_buffer.seek(0)
        app.config['RESUME_BUFFER'] = pdf_buffer

        return render_template('build.html', error=None, report_content="Resume generated successfully! Download below.", resume_generated=True)
    except Exception as e:
        print(f"Error generating resume: {e}")
        return render_template('build.html', error=f"Error generating resume: {str(e)}", report_content=None)

@app.route('/download_report', methods=['GET'])
def download_report():
    pdf_buffer = app.config['REPORT_BUFFER']
    if pdf_buffer:
        pdf_buffer.seek(0)
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name="Resume_Analysis_Report.pdf",
            mimetype='application/pdf'
        )
    return "Report not found.", 404

@app.route('/download_resume', methods=['GET'])
def download_resume():
    pdf_buffer = app.config['RESUME_BUFFER']
    if pdf_buffer:
        pdf_buffer.seek(0)
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name="Generated_Resume.pdf",
            mimetype='application/pdf'
        )
    return "Resume not found.", 404

if __name__ == '__main__':
    app.run(debug=True, port=9002)