from flask import Flask, request, render_template, send_file
import PyPDF2
import spacy
import re
import string
from datetime import datetime
import os
import uuid
from sentence_transformers import SentenceTransformer, util
import google.generativeai as genai
import numpy as np
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
import time

app = Flask(__name__)

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables.")

# Configure Gemini API
genai.configure(api_key=GEMINI_API_KEY)

# Load NLP and AI models
nlp = spacy.load("en_core_web_sm")
sentence_model = SentenceTransformer('all-MiniLM-L6-v2')

def clean_text(text):
    """Clean text by removing special characters and extra spaces."""
    text = re.sub(r'[•\u0080-\uFFFF]', ' ', text)  # Remove special characters
    text = re.sub(r'\s+', ' ', text).strip()  # Normalize spaces
    return text

def extract_text_from_pdf(pdf_file_path):
    """Extract text from a PDF resume."""
    try:
        with open(pdf_file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            text = ' '.join(page.extract_text() or '' for page in reader.pages)
            return clean_text(text)
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def preprocess_text(text):
    """Clean and preprocess text using spaCy."""
    text = text.lower().translate(str.maketrans("", "", string.punctuation))
    doc = nlp(text)
    return [token.lemma_ for token in doc if not token.is_stop and not token.is_space]

def extract_entities(text):
    """Extract skills and organizations from text."""
    doc = nlp(text.lower())

    # Expanded skills detection
    skills = set()
    common_skills = {
        "python", "java", "javascript", "sql", "html", "css", "react", "node", "pandas", "streamlit", "tkinter",
        "aws", "azure", "cloud", "agile", "scrum", "oop", "dbms", "mysql", "mongodb", "docker", "kubernetes",
        "git", "jenkins", "linux", "c", "cpp", "ruby", "php", "typescript", "angular", "vue", "bootstrap",
        "jquery", "flask", "django", "tensorflow", "pytorch", "cybersecurity", "ethical hacking", "power bi",
        "tableau", "excel", "r", "machine learning", "data analysis", "data visualization", "statistical modeling"
    }

    # Exclude non-skill entities
    excluded_entities = set()
    for ent in doc.ents:
        if ent.label_ in {"PERSON", "ORG", "DATE", "GPE"}:  # Exclude names, organizations, dates, locations
            excluded_entities.add(ent.text.lower())

    # Additional terms to exclude (hobbies, generic terms, etc.)
    excluded_terms = {
        "acquire", "back", "choose", "contain", "such", "scale", "resource", "carnatic", "music", "club",
        "email", "education", "coursework", "certification", "project", "extracurricular", "dynamic", "selection",
        "combobox", "responsive", "build", "develop", "ongoing", "btech", "cgpa", "introduction", "interface",
        "science", "scratch", "source", "structure", "structured", "technical", "technology"
    }

    # Split text into sections for context-aware skill detection
    sections = re.split(r'(technical skills|skills|projects|certifications):', text.lower())
    skill_sections = []
    for i in range(len(sections)):
        if sections[i].strip() in {"technical skills", "skills", "projects", "certifications"} and i + 1 < len(sections):
            skill_sections.append(sections[i + 1])

    # Combine skill-relevant sections for focused skill extraction
    skill_text = " ".join(skill_sections) if skill_sections else text.lower()
    skill_doc = nlp(skill_text)

    for token in skill_doc:
        token_text = token.lemma_.strip()
        # Clean up malformed tokens (e.g., remove parentheses, special characters)
        token_text = re.sub(r'[\(\)\|]', '', token_text)
        if not token_text:
            continue

        # Skip excluded entities and terms
        if token_text in excluded_entities or token_text in excluded_terms:
            continue
        if "@" in token_text:  # Skip emails
            continue

        # Match skills exactly or check if token is a relevant substring
        if token_text in common_skills:
            skills.add(token_text)
        elif any(skill in token_text for skill in common_skills if len(skill) > 3):  # Avoid overly short matches
            # Extract the skill part from the token
            for skill in common_skills:
                if skill in token_text and len(skill) > 3:
                    skills.add(skill)
                    break

    # Extract organizations
    orgs = set(ent.text.lower() for ent in doc.ents if ent.label_ == "ORG")
    return skills, orgs

def compute_similarity(resume_text, job_keywords):
    """Compute semantic similarity using sentence transformers."""
    job_text = " ".join(job_keywords)
    resume_embedding = sentence_model.encode(resume_text, convert_to_tensor=True)
    job_embedding = sentence_model.encode(job_text, convert_to_tensor=True)
    similarity = util.cos_sim(resume_embedding, job_embedding).item()
    return similarity * 100

def analyze_with_gemini(resume_text, job_role, matched_keywords, total_keywords, semantic_score, missing_keywords):
    """Consolidated Gemini API call for keywords and recommendations."""
    model = genai.GenerativeModel('gemini-1.5-pro')

    missing_keywords_str = ', '.join(list(missing_keywords)[:3]) if missing_keywords else "none"

    prompt = f"""
    Perform the following tasks for a resume analysis for the job role '{job_role}':

    1. **Extract Job Keywords**: List 10-15 specific technical skills, tools, methodologies, or qualifications typically required for the role (e.g., 'python, java, javascript, cloud, aws, agile, problem solving' for a software engineer). Provide only the list, separated by commas, without explanations.

    2. **Generate Recommendations for Missing Skills**: The resume is missing the following skills: {missing_keywords_str}. Suggest 2-3 specific, actionable steps to acquire these skills and improve the resume for the {job_role} role (e.g., projects, certifications). Keep it concise, professional, under 100 words, and avoid generic advice.

    Format the response as follows:
    Keywords: <comma-separated list>
    Recommendations: <recommendations text>
    """
    response = model.generate_content(prompt)
    response_text = response.text.strip()

    # Parse the response
    keywords, recommendations = None, None
    lines = response_text.split('\n')
    for line in lines:
        if line.startswith("Keywords:"):
            keywords = set(kw.strip().lower() for kw in line.replace("Keywords:", "").strip().split(","))
        elif line.startswith("Recommendations:"):
            recommendations = line.replace("Recommendations:", "").strip()

    # Fallbacks if parsing fails
    if not keywords or len(keywords) < 5:
        keywords = set(["development", "programming", "coding", "software", "engineer"])
        if "software" in job_role.lower():
            keywords.update(["python", "java", "javascript", "cloud", "aws", "agile", "sql", "react", "problem solving"])
    if not recommendations:
        recommendations = f"Add {missing_keywords_str} to your resume by including a project or certification that highlights these skills."

    return keywords, recommendations

def analyze_resume(resume_text, job_role):
    """Analyze resume using NLP and Gemini API."""
    # Initial keyword extraction for semantic similarity
    initial_keywords = set(["development", "programming", "coding", "software", "engineer"])
    if "software" in job_role.lower():
        initial_keywords.update(["python", "java", "javascript", "cloud", "aws", "agile", "sql", "react", "problem solving"])
    elif "data" in job_role.lower():
        initial_keywords.update(["python", "sql", "tableau", "power bi", "data analysis", "machine learning", "excel"])

    resume_tokens = preprocess_text(resume_text)
    # Flexible keyword matching
    matched_keywords = set()
    for token in resume_tokens:
        for keyword in initial_keywords:
            if token in keyword or keyword in token:
                matched_keywords.add(keyword)
    keyword_match_percentage = (len(set(matched_keywords)) / len(initial_keywords)) * 100 if initial_keywords else 0

    # Semantic similarity
    semantic_score = compute_similarity(resume_text, initial_keywords)

    # Entity extraction
    resume_skills, resume_orgs = extract_entities(resume_text)

    # Consolidated Gemini API call
    job_keywords, recommendations = analyze_with_gemini(
        resume_text, job_role, matched_keywords, len(initial_keywords), semantic_score, set()
    )

    # Update matched keywords with the new keyword list
    matched_keywords = set()
    for token in resume_tokens:
        for keyword in job_keywords:
            if token in keyword or keyword in token:
                matched_keywords.add(keyword)
    keyword_match_percentage = (len(set(matched_keywords)) / len(job_keywords)) * 100 if job_keywords else 0

    # Compute missing keywords after getting job_keywords
    missing_keywords = set(job_keywords) - set(matched_keywords)

    # Re-run Gemini API call with missing keywords to get tailored recommendations
    _, recommendations = analyze_with_gemini(
        resume_text, job_role, matched_keywords, len(job_keywords), semantic_score, missing_keywords
    )

    # Adjusted scoring
    final_score = 0.6 * semantic_score + 0.4 * min(keyword_match_percentage, 80)
    final_score = max(min(final_score, 100), 0)

    return {
        "score": round(final_score, 2),
        "semantic_score": round(semantic_score, 2),
        "keyword_match_percentage": round(keyword_match_percentage, 2),
        "matched_keywords": list(set(matched_keywords)),
        "total_keywords": len(job_keywords),
        "job_keywords": list(job_keywords),
        "missing_keywords": list(missing_keywords),
        "recommendations": recommendations,
        "resume_skills": resume_skills
    }

def generate_report(analysis, candidate_name, job_role):
    """Generate a PDF resume analysis report using reportlab."""
    current_date = datetime.now().strftime("%B %d, %Y")
    candidate_name = candidate_name or "Candidate"
    job_keywords = ', '.join(sorted(analysis['job_keywords'])) if analysis['job_keywords'] else 'None'
    matched_keywords = ', '.join(sorted(analysis['matched_keywords'])) if analysis['matched_keywords'] else 'None'
    missing_keywords = ', '.join(sorted(analysis['missing_keywords'])) if analysis['missing_keywords'] else 'None'
    resume_skills = ', '.join(sorted(analysis['resume_skills'])) if analysis['resume_skills'] else 'None'
    recommendations = analysis['recommendations']

    # Set up PDF
    report_base_name = f"Resume_Analysis_Report_{uuid.uuid4()}"
    report_pdf_path = os.path.join('Uploads', f"{report_base_name}.pdf")
    doc = SimpleDocTemplate(report_pdf_path, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()

    # Define custom styles
    styles.add(ParagraphStyle(name='TitleBlue', parent=styles['Title'], fontSize=20, textColor=colors.HexColor('#003366'), spaceAfter=10))
    styles.add(ParagraphStyle(name='Header', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#808080'), alignment=2))
    styles.add(ParagraphStyle(name='Section', parent=styles['Heading1'], fontSize=14, textColor=colors.HexColor('#003366'), spaceBefore=10, spaceAfter=5))
    styles.add(ParagraphStyle(name='Body', parent=styles['Normal'], fontSize=10, leading=12, spaceAfter=5))
    styles.add(ParagraphStyle(name='Bold', parent=styles['Body'], fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='Footer', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#808080'), alignment=1, spaceBefore=20))

    # Content elements
    elements = []

    # Header
    elements.append(Paragraph(f"Resume Analysis Report", styles['TitleBlue']))
    elements.append(Paragraph(f"Prepared for: {candidate_name}", styles['Body']))
    elements.append(Paragraph(f"Date: {current_date}", styles['Body']))
    elements.append(Paragraph(f"Target Position: {job_role}", styles['Body']))
    elements.append(Spacer(1, 0.5*cm))

    # Horizontal line
    elements.append(Paragraph("<hr>", styles['Body']))
    elements.append(Spacer(1, 0.5*cm))

    # Section 1: Summary
    elements.append(Paragraph("1. Summary", styles['Section']))
    elements.append(Paragraph(f"<b>Overall Score:</b> {analysis['score']}/100", styles['Body']))
    elements.append(Paragraph(f"<b>Semantic Alignment:</b> {analysis['semantic_score']}% (contextual match with job requirements)", styles['Body']))
    elements.append(Paragraph(f"<b>Keyword Match:</b> {analysis['keyword_match_percentage']}% ({len(analysis['matched_keywords'])}/{analysis['total_keywords']})", styles['Body']))
    elements.append(Spacer(1, 0.2*cm))

    # Section 2: Keywords
    elements.append(Paragraph("2. Keywords", styles['Section']))
    elements.append(Paragraph(f"<b>Job-Relevant Keywords:</b> {job_keywords}", styles['Body']))
    elements.append(Paragraph(f"<b>Matched:</b> {matched_keywords}", styles['Body']))
    elements.append(Paragraph(f"<b>Missing:</b> {missing_keywords}", styles['Body']))
    elements.append(Spacer(1, 0.2*cm))

    # Section 3: Skills Detected
    elements.append(Paragraph("3. Skills Detected", styles['Section']))
    elements.append(Paragraph(f"<b>Resume Skills:</b> {resume_skills}", styles['Body']))
    elements.append(Spacer(1, 0.2*cm))

    # Section 4: Skillsets Needed and Recommendations
    elements.append(Paragraph("4. Skillsets Needed and Recommendations", styles['Section']))
    elements.append(Paragraph(f"<b>Missing Skills:</b> {missing_keywords}", styles['Body']))
    elements.append(Paragraph(f"<b>Recommendations:</b> {recommendations}", styles['Body']))
    elements.append(Spacer(1, 0.5*cm))

    # Footer
    elements.append(Paragraph("<i>Best of luck with your application!</i>", styles['Footer']))
    elements.append(Paragraph("<b>AI Resume Analyzer Team</b>", styles['Footer']))

    # Build PDF
    doc.build(elements)
    return report_pdf_path

def safe_remove(file_path, max_attempts=5, delay=0.5):
    """Attempt to remove a file with retries to handle file lock issues."""
    for attempt in range(max_attempts):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
            return
        except PermissionError:
            if attempt == max_attempts - 1:
                print(f"Warning: Could not delete {file_path} after {max_attempts} attempts.")
                return
            time.sleep(delay)

@app.after_request
def cleanup_files(response):
    """Clean up temporary files after the response is sent."""
    if hasattr(g, 'files_to_cleanup'):
        for file_path in g.files_to_cleanup:
            safe_remove(file_path)
    return response

from flask import g

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        candidate_name = request.form.get('candidate_name', '')
        job_role = request.form.get('job_role')
        resume_file = request.files.get('resume_file')

        if not job_role or not resume_file:
            return render_template('index.html', error="Job role and resume file are required.")

        if not resume_file.filename.lower().endswith('.pdf'):
            return render_template('index.html', error="Upload a valid PDF file.")

        try:
            upload_folder = 'Uploads'
            os.makedirs(upload_folder, exist_ok=True)
            resume_path = os.path.join(upload_folder, f"resume_{uuid.uuid4()}.pdf")
            resume_file.save(resume_path)

            resume_text = extract_text_from_pdf(resume_path)
            if "Error" in resume_text:
                safe_remove(resume_path)
                return render_template('index.html', error=resume_text)

            analysis = analyze_resume(resume_text, job_role)
            report_pdf_path = generate_report(analysis, candidate_name, job_role)

            # Store files to cleanup after response
            g.files_to_cleanup = [resume_path, report_pdf_path]

            # Sending the PDF file
            response = send_file(
                report_pdf_path,
                as_attachment=True,
                download_name="Resume_Analysis_Report.pdf",
                mimetype='application/pdf'
            )

            return response

        except Exception as e:
            print(f"Error processing request: {e}")
            return render_template('index.html', error=str(e))

    return render_template('index.html', error=None)

if __name__ == '__main__':
    print("Launching Flask server... Visit http://127.0.0.1:5000")
    app.run(debug=True)