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
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

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

# Store the path of the generated report file for download
app.config['REPORT_PATH'] = None

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

def analyze_with_gemini(resume_text, job_role, matched_keywords, total_keywords, semantic_score, resume_tokens):
    """Consolidated Gemini API call for keywords and recommendations using gemini-1.5-flash."""
    model = genai.GenerativeModel('gemini-1.5-flash')

    # Compute initial matched keywords to estimate missing keywords
    initial_keywords = set(["development", "programming", "coding", "software", "engineer"])
    if "software" in job_role.lower():
        initial_keywords.update(["python", "java", "javascript", "cloud", "aws", "agile", "sql", "react", "problem solving"])
    elif "data" in job_role.lower():
        initial_keywords.update(["python", "sql", "tableau", "power bi", "data analysis", "machine learning", "excel"])

    initial_matched_keywords = set()
    for token in resume_tokens:
        for keyword in initial_keywords:
            if token in keyword or keyword in token:
                initial_matched_keywords.add(keyword)

    # Estimate missing keywords (this is a rough estimate for the prompt)
    estimated_missing_keywords = initial_keywords - initial_matched_keywords
    missing_keywords_str = ', '.join(list(estimated_missing_keywords)[:3]) if estimated_missing_keywords else "none"

    prompt = f"""
    Perform the following tasks for a resume analysis for the job role '{job_role}':

    1. **Extract Job Keywords**: List 10-15 specific technical skills, tools, methodologies, or qualifications typically required for the role (e.g., 'python, java, javascript, cloud, aws, agile, problem solving' for a software engineer). Provide only the list, separated by commas, without explanations.

    2. **Generate Recommendations for Missing Skills**: The resume is likely missing skills similar to: {missing_keywords_str}. After extracting the job keywords, identify which of these (or similar skills) are missing based on your keyword list, and suggest 2-3 specific, actionable steps to acquire those missing skills and improve the resume for the {job_role} role (e.g., projects, certifications). Keep it concise, professional, under 100 words, and avoid generic advice.

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

    # Single Gemini API call for keywords and recommendations
    job_keywords, recommendations = analyze_with_gemini(
        resume_text, job_role, matched_keywords, len(initial_keywords), semantic_score, resume_tokens
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

def generate_report(analysis, job_role, pdf_path):
    """Generate a resume analysis report in both plain text (for web display) and PDF (using reportlab)."""
    current_date = datetime.now().strftime("%B %d, %Y")
    job_keywords = analysis['job_keywords']
    missing_keywords = analysis['missing_keywords']

    # Plain text version for web display
    plain_text_report = f"""Resume Analysis Report
Date: {current_date}
Target Position: {job_role}

---

1. Summary
- Overall Score: {analysis['score']}/100
- Semantic Alignment: {analysis['semantic_score']}% (contextual match with job requirements)
- Keyword Match: {analysis['keyword_match_percentage']}% ({len(analysis['matched_keywords'])}/{analysis['total_keywords']})

2. Keywords
- Job-Relevant Keywords: {', '.join(sorted(job_keywords)) if job_keywords else 'None'}
- Matched: {', '.join(sorted(analysis['matched_keywords'])) if analysis['matched_keywords'] else 'None'}
- Missing: {', '.join(sorted(missing_keywords)) if missing_keywords else 'None'}

3. Skills Detected
- Resume Skills: {', '.join(sorted(analysis['resume_skills'])) if analysis['resume_skills'] else 'None'}

4. Skillsets Needed and Recommendations
- Missing Skills: {', '.join(sorted(missing_keywords)) if missing_keywords else 'None'}
- Recommendations: {analysis['recommendations']}

Best of luck with your application!
AI Resume Analyzer Team
"""

    # PDF version using reportlab
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='TitleStyle',
        parent=styles['Title'],
        fontSize=16,
        leading=20,
        alignment=1,  # Center
        spaceAfter=12
    )
    normal_style = ParagraphStyle(
        name='NormalStyle',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        spaceAfter=6
    )
    heading_style = ParagraphStyle(
        name='HeadingStyle',
        parent=styles['Heading2'],
        fontSize=14,
        leading=16,
        spaceBefore=12,
        spaceAfter=6
    )
    bullet_style = ParagraphStyle(
        name='BulletStyle',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        leftIndent=20,
        firstLineIndent=-10,
        spaceAfter=4
    )

    # Create PDF elements
    elements = []

    # Title and header
    elements.append(Paragraph("Resume Analysis Report", title_style))
    elements.append(Paragraph(f"Date: {current_date}", normal_style))
    elements.append(Paragraph(f"Target Position: {job_role}", normal_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Horizontal line (simulated with a paragraph of underscores)
    elements.append(Paragraph("_" * 80, normal_style))
    elements.append(Spacer(1, 0.1 * inch))

    # Section 1: Summary
    elements.append(Paragraph("1. Summary", heading_style))
    elements.append(Paragraph(f"&bull; <b>Overall Score:</b> {analysis['score']}/100", bullet_style))
    elements.append(Paragraph(f"&bull; <b>Semantic Alignment:</b> {analysis['semantic_score']}% (contextual match with job requirements)", bullet_style))
    elements.append(Paragraph(f"&bull; <b>Keyword Match:</b> {analysis['keyword_match_percentage']}% ({len(analysis['matched_keywords'])}/{analysis['total_keywords']})", bullet_style))
    elements.append(Spacer(1, 0.1 * inch))

    # Section 2: Keywords
    elements.append(Paragraph("2. Keywords", heading_style))
    elements.append(Paragraph(f"&bull; <b>Job-Relevant Keywords:</b> {', '.join(sorted(job_keywords)) if job_keywords else 'None'}", bullet_style))
    elements.append(Paragraph(f"&bull; <b>Matched:</b> {', '.join(sorted(analysis['matched_keywords'])) if analysis['matched_keywords'] else 'None'}", bullet_style))
    elements.append(Paragraph(f"&bull; <b>Missing:</b> {', '.join(sorted(missing_keywords)) if missing_keywords else 'None'}", bullet_style))
    elements.append(Spacer(1, 0.1 * inch))

    # Section 3: Skills Detected
    elements.append(Paragraph("3. Skills Detected", heading_style))
    elements.append(Paragraph(f"&bull; <b>Resume Skills:</b> {', '.join(sorted(analysis['resume_skills'])) if analysis['resume_skills'] else 'None'}", bullet_style))
    elements.append(Spacer(1, 0.1 * inch))

    # Section 4: Skillsets Needed and Recommendations
    elements.append(Paragraph("4. Skillsets Needed and Recommendations", heading_style))
    elements.append(Paragraph(f"&bull; <b>Missing Skills:</b> {', '.join(sorted(missing_keywords)) if missing_keywords else 'None'}", bullet_style))
    elements.append(Paragraph(f"&bull; <b>Recommendations:</b> {analysis['recommendations']}", bullet_style))
    elements.append(Spacer(1, 0.2 * inch))

    # Horizontal line
    elements.append(Paragraph("_" * 80, normal_style))
    elements.append(Spacer(1, 0.1 * inch))

    # Closing message
    elements.append(Paragraph("<i>Best of luck with your application!</i>", normal_style))
    elements.append(Paragraph("<i>AI Resume Analyzer Team</i>", normal_style))

    # Build the PDF
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=inch, leftMargin=inch, topMargin=inch, bottomMargin=inch)
    doc.build(elements)

    return plain_text_report

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        job_role = request.form.get('job_role')
        resume_file = request.files.get('resume_file')

        if not job_role or not resume_file:
            return render_template('index.html', error="Job role and resume file are required.", report_content=None)

        if not resume_file.filename.lower().endswith('.pdf'):
            return render_template('index.html', error="Upload a valid PDF file.", report_content=None)

        try:
            upload_folder = 'uploads'
            os.makedirs(upload_folder, exist_ok=True)
            resume_path = os.path.join(upload_folder, f"resume_{uuid.uuid4()}.pdf")
            resume_file.save(resume_path)

            resume_text = extract_text_from_pdf(resume_path)
            if "Error" in resume_text:
                os.remove(resume_path)
                return render_template('index.html', error=resume_text, report_content=None)

            analysis = analyze_resume(resume_text, job_role)

            # Define the path for the PDF report
            report_path = os.path.join(upload_folder, f"Resume_Analysis_Report_{uuid.uuid4()}.pdf")
            plain_text_report = generate_report(analysis, job_role, report_path)

            # Store the report path in app config for download
            app.config['REPORT_PATH'] = report_path

            # Clean up the resume file
            os.remove(resume_path)

            # Render the template with the plain text report content for display
            return render_template('index.html', error=None, report_content=plain_text_report)

        except Exception as e:
            print(f"Error processing request: {e}")
            return render_template('index.html', error=str(e), report_content=None)

    return render_template('index.html', error=None, report_content=None)

@app.route('/download_report', methods=['GET'])
def download_report():
    report_path = app.config['REPORT_PATH']
    if report_path and os.path.exists(report_path):
        return send_file(report_path, as_attachment=True, download_name="Resume_Analysis_Report.pdf")
    return "Report not found.", 404

if __name__ == '__main__':
    app.run(debug=True, port=9002)