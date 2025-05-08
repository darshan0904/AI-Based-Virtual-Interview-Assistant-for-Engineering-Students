from flask import Flask, render_template, request, jsonify, send_file
import os
import aiohttp
import pyttsx3
import uuid
import re
import PyPDF2

app = Flask(__name__)

# Directories
DATA_FOLDER = 'data'
IMP_QUESTION_FOLDER = os.path.join('IMP', 'questions')
os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(IMP_QUESTION_FOLDER, exist_ok=True)

# Domains and Roles (8 domains, 5 roles each)
DOMAINS = [
    "Software Development",
    "Data Science & AI",
    "Cybersecurity",
    "UI/UX Design",
    "Cloud & Infrastructure",
    "Marketing & Sales",
    "Human Resources",
    "Finance & Business Analysis"
]

ROLES = {
    "Software Development": ["Frontend Developer", "Backend Developer", "Full Stack Developer", "DevOps Engineer", "Mobile App Developer"],
    "Data Science & AI": ["Data Analyst", "Data Scientist", "Machine Learning Engineer", "AI Researcher", "NLP Engineer"],
    "Cybersecurity": ["Security Analyst", "Penetration Tester", "Security Engineer", "SOC Analyst", "Cybersecurity Consultant"],
    "UI/UX Design": ["UX Designer", "UI Designer", "Product Designer", "Interaction Designer", "UX Researcher"],
    "Cloud & Infrastructure": ["Cloud Engineer", "Solutions Architect", "Site Reliability Engineer", "Cloud Consultant", "Platform Engineer"],
    "Marketing & Sales": ["Digital Marketer", "SEO Specialist", "Content Strategist", "Sales Executive", "Brand Manager"],
    "Human Resources": ["HR Executive", "Talent Acquisition Specialist", "HRBP (Business Partner)", "L&D Coordinator", "Recruitment Coordinator"],
    "Finance & Business Analysis": ["Financial Analyst", "Business Analyst", "Investment Analyst", "Risk Consultant", "Corporate Strategist"]
}

sessions = {}

@app.route('/')
def index():
    return render_template('index.html', domains=DOMAINS)

@app.route('/get_roles', methods=['POST'])
async def get_roles():
    data = request.json
    domain = data.get('domain')
    app.logger.info(f"Received request for roles in domain: {domain}")
    roles = ROLES.get(domain, [])
    app.logger.info(f"Returning roles: {roles}")
    return jsonify({"roles": roles})

@app.route('/start_interview', methods=['POST'])
async def start_interview():
    session_id = str(uuid.uuid4())
    name = request.form.get('name')
    domain = request.form.get('domain')
    role = request.form.get('role')
    resume = request.files.get('resume')

    # Sanitize the name for folder and file creation
    sanitized_name = re.sub(r'[^a-zA-Z0-9]', '_', name)

    # Create user-specific folder structure
    user_folder = os.path.join(DATA_FOLDER, sanitized_name)
    os.makedirs(user_folder, exist_ok=True)  # Create parent folder first
    user_audio_folder = os.path.join(user_folder, 'audio')
    user_video_folder = os.path.join(user_folder, 'video')
    os.makedirs(user_audio_folder, exist_ok=True)
    os.makedirs(user_video_folder, exist_ok=True)

    # Parse resume if uploaded
    resume_text = None
    if resume:
        resume_path = os.path.join(user_folder, 'resume.pdf')
        resume.save(resume_path)
        try:
            with open(resume_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                resume_text = ""
                for page in pdf_reader.pages:
                    resume_text += page.extract_text()
            app.logger.info(f"Extracted resume text: {resume_text[:500]}...")  # Log first 500 chars
        except Exception as e:
            app.logger.error(f"Failed to parse resume: {str(e)}")
            resume_text = None

    sessions[session_id] = {
        "name": name,  # Keep original name for display
        "sanitized_name": sanitized_name,  # Store sanitized name for file operations
        "domain": domain,
        "role": role,
        "resume": resume.filename if resume else None,
        "resume_text": resume_text,  # Store parsed resume text
        "current_question": 0,
        "responses": [],
        "questions": [],
        "domains": [],
        "user_folder": user_folder,
        "audio_folder": user_audio_folder,
        "video_folder": user_video_folder
    }

    # Initialize transcript file with username
    transcript_path = os.path.join(user_folder, "transcript.txt")
    try:
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(f"{name}\n\n")
        app.logger.info(f"Initialized transcript file at {transcript_path}")
    except Exception as e:
        app.logger.error(f"Failed to initialize transcript file: {str(e)}")
        return jsonify({"error": f"Failed to initialize transcript file: {str(e)}"}), 500

    return jsonify({"session_id": session_id})

@app.route('/generate_questions/<session_id>', methods=['POST'])
async def generate_questions(session_id):
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404

    data = request.json
    domain = data.get('domain')
    role = data.get('role')
    has_resume = data.get('has_resume')
    name = sessions[session_id]['name']
    resume_text = sessions[session_id].get('resume_text', '')

    # Updated prompts for super hard, technical questions
    prompts = [
        (f"Generate exactly 2 basic introduction questions for a candidate named {name}. Focus on their personal background, interests, or general experience, such as asking about themselves or their career journey, not specific to any role or domain. Format each question as a single line without numbering.", "Introduction", 2),
        (f"Generate exactly 4 technically challenging role-specific interview questions for a candidate named {name}, applying for the role of {role} in {domain}. Focus on in-depth core concepts, advanced tools, or complex problem-solving skills relevant to the role, ensuring the questions assess deep technical knowledge and expertise. Format each question as a single line without numbering.", "Role-Specific", 4),
        (f"Generate exactly 3 behavioral interview questions for a candidate applying for the role of {role} in {domain}. Focus on teamwork, problem-solving, and adaptability, with a technical slant to assess their approach to technical challenges. Format each question as a single line without numbering.", "Behavioral", 3),
        (f"Generate exactly 3 situational or hypothetical interview questions for a candidate applying for the role of {role} in {domain}. Focus on complex technical scenarios they might face in the role, requiring deep technical understanding to answer effectively. Format each question as a single line without numbering.", "Situational", 3)
    ]

    # Adjust resume-based prompt to use actual resume content
    if has_resume and resume_text:
        resume_prompt = (
            f"Here is the resume content for a candidate named {name} applying for the role of {role} in {domain}:\n\n"
            f"{resume_text}\n\n"
            f"Generate exactly 3 technically focused resume-based interview questions based on the specific projects and skills mentioned in the resume. "
            f"Focus on asking about specific project details (e.g., 'In your project [Project Name], how did you handle...') to assess deep technical knowledge and problem-solving skills. "
            f"Ensure the questions are challenging and evaluate the candidate's technical expertise. Format each question as a single line without numbering."
        )
        prompts.insert(1, (resume_prompt, "Resume-Based", 3))
    elif has_resume:
        # Fallback if resume parsing fails
        prompts.insert(1, (f"Generate exactly 3 technically focused resume-based interview questions for a candidate named {name} applying for the role of {role} in {domain}. Assume the resume includes typical experiences and projects for this role, and ask about specific project details to assess deep technical knowledge and problem-solving skills. Format each question as a single line without numbering.", "Resume-Based", 3))

    questions = []
    question_domains = []
    async with aiohttp.ClientSession() as session:
        for prompt, category, count in prompts:
            try:
                async with session.post(
                    "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=AIzaSyAA92C3_BnZiH-2V47VV32OdgS6Trpc8FQ",
                    json={"contents": [{"parts": [{"text": prompt}]}]}
                ) as response:
                    result = await response.json()
                    if 'candidates' not in result or not result['candidates']:
                        app.logger.error(f"API response error for category {category}: {result}")
                        category_questions = [f"Fallback question {i+1} for {category}" for i in range(count)]
                    else:
                        generated_text = result['candidates'][0]['content']['parts'][0]['text']
                        category_questions = [q.strip() for q in generated_text.split('\n') if q.strip() and not q.startswith('#')]
                        category_questions = [re.sub(r'^\d+\.\s*', '', q).strip() for q in category_questions]
                        if len(category_questions) < count:
                            category_questions.extend([f"Fallback question {i+1} for {category}" for i in range(count - len(category_questions))])
                        elif len(category_questions) > count:
                            category_questions = category_questions[:count]
            except Exception as e:
                app.logger.error(f"Error generating questions for category {category}: {str(e)}")
                category_questions = [f"Fallback question {i+1} for {category}" for i in range(count)]

            questions.extend(category_questions)
            question_domains.extend([category] * count)

    # Log generated questions for debugging
    app.logger.info(f"Generated questions for session {session_id}:")
    for i, (q, d) in enumerate(zip(questions, question_domains), 1):
        app.logger.info(f"Question {i}: {q} (Domain: {d})")

    # Save questions to file in user folder
    question_path = os.path.join(sessions[session_id]['user_folder'], 'questions.txt')
    with open(question_path, 'w') as f:
        for i, (question, q_domain) in enumerate(zip(questions, question_domains), 1):
            f.write(f"Question {i}: {question}\n")
            f.write(f"Domain: {q_domain}\n\n")

    sessions[session_id]['questions'] = questions
    sessions[session_id]['domains'] = question_domains

    return jsonify({"questions": questions})

@app.route('/next_question/<session_id>', methods=['POST'])
async def next_question(session_id):
    if session_id not in sessions:
        return jsonify({"end": True})

    data = request.json
    question = data.get('question')
    sanitized_username = sessions[session_id]['sanitized_name']

    # Use pyttsx3 to generate audio and save to a file in IMP/questions
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)  # Slow down the speech rate (default is 200)
    audio_filename = f"question_{sanitized_username}_{sessions[session_id]['current_question'] + 1}.wav"
    audio_path = os.path.join(IMP_QUESTION_FOLDER, audio_filename)
    engine.save_to_file(question, audio_path)
    engine.runAndWait()

    # Increment the current question index
    sessions[session_id]['current_question'] += 1

    # Return the URL to the audio file
    audio_url = f"/imp/questions/{audio_filename}"
    return jsonify({"question": question, "audio": audio_url})

@app.route('/imp/questions/<filename>')
def serve_imp_question(filename):
    file_path = os.path.join(IMP_QUESTION_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='audio/wav')
    return jsonify({"error": "File not found"}), 404

@app.route('/record_response/<session_id>', methods=['POST'])
async def record_response(session_id):
    if session_id not in sessions:
        app.logger.error(f"Session {session_id} not found in sessions dict")
        return jsonify({"error": "Session not found"}), 404

    audio = request.files.get('audio')
    video = request.files.get('video')

    # Get session data
    session_data = sessions[session_id]
    current_question = session_data['current_question']
    sanitized_username = session_data['sanitized_name']
    username = session_data['name']
    domain = session_data['domain']
    questions = session_data['questions']
    domains = session_data['domains']
    user_folder = session_data['user_folder']

    # Save audio and video files
    audio_filename = f"{sanitized_username}_q{current_question}_audio.wav"
    video_filename = f"{sanitized_username}_q{current_question}_video.mp4"

    if audio:
        audio_path = os.path.join(session_data['audio_folder'], audio_filename)
        audio.save(audio_path)

    if video:
        video_path = os.path.join(session_data['video_folder'], video_filename)
        video.save(video_path)

    sessions[session_id]["responses"].append({
        "audio": audio_filename if audio else None,
        "video": video_filename if video else None,
    })

    # Get user answer from transcript
    transcript = request.form.get('transcript', '')
    app.logger.info(f"Received transcript for question {current_question}: {transcript}")
    transcript_lines = transcript.split('\n')
    user_answer = "No response recorded"
    for line in transcript_lines:
        if line.startswith(f"Question {current_question}:"):
            continue
        if line.startswith("User Answer:"):
            user_answer = line.split(":", 1)[1].strip()
            break

    # Build transcript entry for this question
    question_idx = current_question
    question = questions[question_idx - 1] if question_idx - 1 < len(questions) else "No question available"
    q_domain = domains[question_idx - 1] if question_idx - 1 < len(domains) else "Unknown"
    audio_file = audio_filename if audio else "Not recorded"
    video_file = video_filename if video else "Not recorded"
    ai_answer = generate_ai_answer(question)

    transcript_entry = (
        f"Question {question_idx}: {question}\n"
        f"User Answer: {user_answer}\n"
        f"AI Answer: {ai_answer}\n"
        f"Domain: {q_domain}\n"
        f"Audio File: {audio_file}\n"
        f"Video File: {video_file}\n\n"
        f"{'=' * 80}\n\n"
    )

    # Append to transcript file
    transcript_path = os.path.join(user_folder, "transcript.txt")
    app.logger.info(f"Appending to transcript at {transcript_path}")
    app.logger.info(f"Transcript entry:\n{transcript_entry}")
    try:
        with open(transcript_path, 'a', encoding='utf-8') as f:
            f.write(transcript_entry)
        app.logger.info(f"Successfully appended to transcript for question {current_question}")
    except Exception as e:
        app.logger.error(f"Failed to append to transcript file: {str(e)}")
        return jsonify({"error": f"Failed to append to transcript file: {str(e)}"}), 500

    return jsonify({"status": "success"})

def generate_ai_answer(question):
    if "programming languages" in question.lower():
        return ("I'm proficient in Java, Python, and JavaScript. My experience with Java includes developing backend services using Spring Boot and utilizing core Java features such as multithreading and collections. With Python, I've worked on data analysis projects using Pandas and NumPy, and web scraping projects using Beautiful Soup. My JavaScript experience encompasses both front-end development using React, where I've built interactive user interfaces and single-page applications, and back-end development using Node.js.")
    elif "object-oriented programming" in question.lower() or "oop" in question.lower():
        return ("Object-Oriented Programming (OOP) is a programming paradigm that organizes software design around data, or objects, rather than functions and logic. An object can be defined as a data field that has unique attributes and behavior. OOP uses four main principles:\n\n"
                "Encapsulation: Bundling data and methods that operate on that data within a class, protecting the internal state from direct external access and modification. This promotes data integrity and reduces unintended side effects.\n\n"
                "Inheritance: Creating new classes (child classes) based on existing classes (parent classes), inheriting their properties and behaviors. This allows for code reuse and establishes a hierarchical relationship between classes.\n\n"
                "Polymorphism: The ability of objects of different classes to respond to the same method call in their own specific way. This enables flexibility and extensibility.\n\n"
                "Abstraction: Hiding complex implementation details and showing only essential information to the user. This simplifies the interaction with objects and improves code maintainability.\n\n"
                "These principles together contribute to creating modular, maintainable, and reusable code.")
    else:
        return "I would approach this question by providing a detailed and structured response based on my experience and knowledge in the domain."

if __name__ == '__main__':
    app.run(debug=True)