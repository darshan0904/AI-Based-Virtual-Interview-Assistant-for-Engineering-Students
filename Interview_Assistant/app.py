from flask import Flask, render_template, request, jsonify, send_file
import os
import requests
import pyttsx3
import uuid
import re
import PyPDF2
import logging
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_FOLDER = 'data'
IMP_QUESTION_FOLDER = os.path.join('IMP', 'questions')
os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(IMP_QUESTION_FOLDER, exist_ok=True)

ENGINEERING_FIELDS = [
    "Computer Engineering", "Mechanical Engineering", "Electrical Engineering",
    "Civil Engineering", "Electronics & Communication Engineering", "Chemical Engineering",
    "Biomedical Engineering", "Aerospace Engineering", "Industrial Engineering",
    "Environmental Engineering"
]

DOMAINS = {
    "Computer Engineering": [
        "Software Development", "Data Science & AI", "Cybersecurity", "UI/UX Design",
        "Cloud & Infrastructure", "Blockchain & Web3", "Embedded Systems", "Game Development"
    ],
    "Mechanical Engineering": [
        "Automotive Engineering", "Robotics", "Manufacturing", "HVAC", "Design & CAD",
        "Aerospace Systems", "Material Science", "Energy Systems"
    ],
}

ROLES = {
    "Software Development": [
        "Frontend Developer", "Backend Developer", "Full Stack Developer",
        "DevOps Engineer", "Mobile App Developer", "Software Architect"
    ],
    "Data Science & AI": [
        "Data Analyst", "Data Scientist", "Machine Learning Engineer",
        "AI Researcher", "NLP Engineer", "Deep Learning Engineer"
    ],
}

sessions = {}

@app.route('/')
def index():
    return render_template('index.html', engineering_fields=ENGINEERING_FIELDS)

@app.route('/get_domains', methods=['POST'])
def get_domains():
    try:
        data = request.json
        engineering = data.get('engineering')
        if not engineering:
            logger.error("Engineering field missing in get_domains request")
            return jsonify({"error": "Engineering field required"}), 400
        domains = DOMAINS.get(engineering, [])
        logger.info(f"Returning domains for {engineering}: {domains}")
        return jsonify({"domains": domains})
    except Exception as e:
        logger.error(f"Error in get_domains: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/get_roles', methods=['POST'])
def get_roles():
    try:
        data = request.json
        domain = data.get('domain')
        if not domain:
            logger.error("Domain missing in get_roles request")
            return jsonify({"error": "Domain required"}), 400
        roles = ROLES.get(domain, [])
        logger.info(f"Returning roles for {domain}: {roles}")
        return jsonify({"roles": roles})
    except Exception as e:
        logger.error(f"Error in get_roles: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/start_interview', methods=['POST'])
def start_interview():
    try:
        session_id = str(uuid.uuid4())
        name = request.form.get('name')
        engineering = request.form.get('engineering')
        domain = request.form.get('domain')
        role = request.form.get('role')
        resume = request.files.get('resume')

        if not all([name, engineering, domain, role]):
            logger.error("Missing required fields in start_interview")
            return jsonify({"error": "All fields are required"}), 400

        sanitized_name = re.sub(r'[^a-zA-Z0-9]', '_', name)
        user_folder = os.path.join(DATA_FOLDER, sanitized_name)
        os.makedirs(user_folder, exist_ok=True)
        user_audio_folder = os.path.join(user_folder, 'audio')
        user_video_folder = os.path.join(user_folder, 'video')
        os.makedirs(user_audio_folder, exist_ok=True)
        os.makedirs(user_video_folder, exist_ok=True)

        resume_text = None
        resume_filename = None
        if resume:
            resume_filename = secure_filename(resume.filename)
            resume_path = os.path.join(user_folder, resume_filename)
            resume.save(resume_path)
            try:
                with open(resume_path, 'rb') as f:
                    pdf_reader = PyPDF2.PdfReader(f)
                    resume_text = ""
                    for page in pdf_reader.pages:
                        extracted_text = page.extract_text()
                        if extracted_text:
                            resume_text += extracted_text
                logger.info(f"Extracted resume text for {name}: {resume_text[:100]}...")
            except Exception as e:
                logger.warning(f"Failed to parse resume for {name}: {str(e)}")
                resume_text = None

        sessions[session_id] = {
            "name": name,
            "sanitized_name": sanitized_name,
            "engineering": engineering,
            "domain": domain,
            "role": role,
            "resume": resume_filename,
            "resume_text": resume_text,
            "current_question": 0,
            "responses": [],
            "questions": [],
            "domains": [],
            "ai_answers": [],
            "user_folder": user_folder,
            "audio_folder": user_audio_folder,
            "video_folder": user_video_folder
        }

        transcript_path = os.path.join(user_folder, "transcript.txt")
        try:
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(f"{name}\n\n")
            logger.info(f"Initialized transcript file at {transcript_path}")
        except Exception as e:
            logger.error(f"Failed to initialize transcript file: {str(e)}")
            return jsonify({"error": f"Failed to initialize transcript: {str(e)}"}), 500

        logger.info(f"Started interview session {session_id} for {name}")
        return jsonify({"session_id": session_id})
    except Exception as e:
        logger.error(f"Error in start_interview: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/generate_questions/<session_id>', methods=['POST'])
def generate_questions(session_id):
    try:
        if session_id not in sessions:
            logger.error(f"Session {session_id} not found")
            return jsonify({"error": "Session not found"}), 404

        data = request.json
        domain = data.get('domain')
        role = data.get('role')
        has_resume = data.get('has_resume')
        name = sessions[session_id]['name']
        resume_text = sessions[session_id].get('resume_text')

        prompts = [
            (f"Generate exactly 2 basic introduction questions for a candidate named {name}. Focus on their personal background, interests, or general experience, such as asking about themselves or their career journey, not specific to any role or domain. Format each question as a single line without numbering.", "Introduction", 2),
            (f"Generate exactly 4 technically challenging role-specific interview questions for a candidate named {name}, applying for the role of {role} in {domain}. Focus on in-depth core concepts, advanced tools, or complex problem-solving skills relevant to the role, ensuring the questions assess deep technical knowledge and expertise. Format each question as a single line without numbering.", "Role-Specific", 4),
            (f"Generate exactly 3 behavioral interview questions for a candidate applying for the role of {role} in {domain}. Focus on teamwork, problem-solving, and adaptability, with a technical slant to assess their approach to technical challenges. Format each question as a single line without numbering.", "Behavioral", 3),
            (f"Generate exactly 3 situational or hypothetical interview questions for a candidate applying for the role of {role} in {domain}. Focus on complex technical scenarios they might face in the role, requiring deep technical understanding to answer effectively. Format each question as a single line without numbering.", "Situational", 3)
        ]

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
            prompts.insert(1, (
                f"Generate exactly 3 technically focused resume-based interview questions for a candidate named {name} applying for the role of {role} in {domain}. "
                f"Assume the resume includes typical experiences and projects for this role, and ask about specific project details to assess deep technical knowledge and problem-solving skills. "
                f"Format each question as a single line without numbering.", "Resume-Based", 3))

        questions = []
        question_domains = []

        def fetch_questions(prompt, category, count):
            try:
                response = requests.post(
                    "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=AIzaSyCVyhDktWeeV7rvUxz1GBSKNQCPBTvK8uY",
                    json={"contents": [{"parts": [{"text": prompt}]}]},
                    timeout=10
                )
                response.raise_for_status()
                result = response.json()
                if 'candidates' not in result or not result['candidates']:
                    logger.error(f"Gemini API returned no candidates for {category}")
                    return [f"Fallback question {i+1} for {category}" for i in range(count)]
                generated_text = result['candidates'][0]['content']['parts'][0]['text']
                category_questions = [q.strip() for q in generated_text.split('\n') if q.strip() and not q.startswith('#')]
                category_questions = [re.sub(r'^\d+\.\s*', '', q).strip() for q in category_questions]
                if len(category_questions) < count:
                    category_questions.extend([f"Fallback question {i+1} for {category}" for i in range(count - len(category_questions))])
                elif len(category_questions) > count:
                    category_questions = category_questions[:count]
                return category_questions
            except requests.exceptions.RequestException as e:
                logger.error(f"Gemini API request failed for {category}: {str(e)}")
                return [f"Fallback question {i+1} for {category}" for i in range(count)]

        for prompt, category, count in prompts:
            category_questions = fetch_questions(prompt, category, count)
            questions.extend(category_questions)
            question_domains.extend([category] * count)

        logger.info(f"Generated questions for session {session_id}:")
        for i, (q, d) in enumerate(zip(questions, question_domains), 1):
            logger.info(f"Question {i}: {q} (Domain: {d})")

        question_path = os.path.join(sessions[session_id]['user_folder'], 'questions.txt')
        try:
            with open(question_path, 'w', encoding='utf-8') as f:
                for i, (question, q_domain) in enumerate(zip(questions, question_domains), 1):
                    f.write(f"Question {i}: {question}\n")
                    f.write(f"Domain: {q_domain}\n\n")
        except Exception as e:
            logger.error(f"Failed to save questions file: {str(e)}")
            return jsonify({"error": f"Failed to save questions: {str(e)}"}), 500

        sessions[session_id]['questions'] = questions
        sessions[session_id]['domains'] = question_domains

        return jsonify({"questions": questions})
    except Exception as e:
        logger.error(f"Error in generate_questions: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/next_question/<session_id>', methods=['POST'])
def next_question(session_id):
    try:
        if session_id not in sessions:
            logger.error(f"Session {session_id} not found")
            return jsonify({"end": True}), 404

        session_data = sessions[session_id]
        current_question_idx = session_data['current_question']
        questions = session_data['questions']

        if current_question_idx >= len(questions):
            logger.info(f"Session {session_id} has no more questions")
            return jsonify({"end": True})

        question = questions[current_question_idx]
        sanitized_username = session_data['sanitized_name']

        audio_filename = f"question_{session_id}_{current_question_idx + 1}.wav"
        audio_path = os.path.join(IMP_QUESTION_FOLDER, audio_filename)
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
            engine.save_to_file(question, audio_path)
            engine.runAndWait()
            logger.info(f"Generated audio for question {current_question_idx + 1} at {audio_path}")
        except Exception as e:
            logger.error(f"Failed to generate audio for question {current_question_idx + 1}: {str(e)}")
            return jsonify({"error": f"Failed to generate audio: {str(e)}"}), 500

        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found at {audio_path}")
            return jsonify({"error": "Audio file generation failed"}), 500

        ai_answer = generate_ai_answer(session_id, question)
        session_data['current_question'] += 1
        audio_url = f"/imp/questions/{audio_filename}"
        logger.info(f"Returning audio URL for question {current_question_idx + 1}: {audio_url}")
        return jsonify({"ai_answer": ai_answer, "audio": audio_url})
    except Exception as e:
        logger.error(f"Error in next_question: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/imp/questions/<filename>')
def serve_imp_question(filename):
    try:
        file_path = os.path.join(IMP_QUESTION_FOLDER, filename)
        if os.path.exists(file_path):
            logger.info(f"Serving audio file: {file_path}")
            return send_file(file_path, mimetype='audio/wav')
        logger.error(f"Audio file not found: {file_path}")
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        logger.error(f"Error serving audio file {filename}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/record_response/<session_id>/<int:question_idx>', methods=['POST'])
def record_response(session_id, question_idx):
    try:
        if session_id not in sessions:
            logger.error(f"Session {session_id} not found")
            return jsonify({"error": "Session not found"}), 404

        session_data = sessions[session_id]
        audio = request.files.get('audio')
        video = request.files.get('video')
        transcript = request.form.get('transcript', 'No transcript provided')

        sanitized_username = session_data['sanitized_name']
        user_folder = session_data['user_folder']
        audio_folder = session_data['audio_folder']
        video_folder = session_data['video_folder']

        audio_filename = f"{sanitized_username}_q{question_idx}_audio.wav"
        video_filename = f"{sanitized_username}_q{question_idx}_video.mp4"

        # Validate and save audio
        if audio and audio.content_length > 0 and audio.mimetype.startswith('audio/'):
            audio_path = os.path.join(audio_folder, audio_filename)
            try:
                audio.save(audio_path)
                if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                    logger.info(f"Saved audio for question {question_idx}: {audio_path} (size: {os.path.getsize(audio_path)} bytes)")
                else:
                    logger.warning(f"Audio file empty or not created: {audio_path}")
                    audio_filename = None
            except Exception as e:
                logger.error(f"Failed to save audio for question {question_idx}: {str(e)}")
                audio_filename = None
        else:
            logger.warning(f"No valid audio provided for question {question_idx} (content_length: {audio.content_length if audio else 0}, mimetype: {audio.mimetype if audio else 'None'})")
            audio_filename = None

        # Validate and save video
        if video and video.content_length > 0 and video.mimetype.startswith('video/'):
            video_path = os.path.join(video_folder, video_filename)
            try:
                video.save(video_path)
                if os.path.exists(video_path) and os.path.getsize(video_path) > 0:
                    logger.info(f"Saved video for question {question_idx}: {video_path} (size: {os.path.getsize(video_path)} bytes)")
                else:
                    logger.warning(f"Video file empty or not created: {video_path}")
                    video_filename = None
            except Exception as e:
                logger.error(f"Failed to save video for question {question_idx}: {str(e)}")
                video_filename = None
        else:
            logger.warning(f"No valid video provided for question {question_idx} (content_length: {video.content_length if video else 0}, mimetype: {video.mimetype if video else 'None'})")
            video_filename = None

        # Update session responses
        sessions[session_id]["responses"].append({
            "question_idx": question_idx,
            "audio": audio_filename,
            "video": video_filename,
            "transcript": transcript
        })

        # Append to transcript file
        transcript_path = os.path.join(user_folder, "transcript.txt")
        try:
            question_text = session_data['questions'][question_idx-1] if question_idx-1 < len(session_data['questions']) else "Unknown Question"
            ai_answer = "N/A"
            for ans in session_data.get('ai_answers', []):
                if ans.get('question_idx') == question_idx:
                    ai_answer = ans.get('ai_answer', 'N/A')
                    break
            domain = session_data['domains'][question_idx-1] if question_idx-1 < len(session_data['domains']) else "Unknown"

            with open(transcript_path, 'a', encoding='utf-8') as f:
                f.write(f"Question {question_idx}: {question_text}\n")
                f.write(f"User Answer: {transcript}\n")
                f.write(f"AI Answer: {ai_answer}\n")
                f.write(f"Domain: {domain}\n")
                f.write(f"Audio File: {audio_filename or 'None'}\n")
                f.write(f"Video File: {video_filename or 'None'}\n\n")
                f.write(f"================================================================================\n\n")
            logger.info(f"Appended to transcript for question {question_idx}")
        except Exception as e:
            logger.error(f"Failed to append to transcript file: {str(e)}")
            return jsonify({"error": f"Failed to append to transcript: {str(e)}"}), 500

        return jsonify({"status": "success"})
    except Exception as e:
        logger.error(f"Error in record_response for session {session_id}, question {question_idx}: {str(e)}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

def generate_ai_answer(session_id, question):
    try:
        session_data = sessions[session_id]
        current_question_idx = session_data['current_question']
        domain = session_data['domains'][current_question_idx] if current_question_idx < len(session_data['domains']) else "Unknown"

        if domain == "Introduction":
            logger.info(f"Skipping AI answer for introduction question {current_question_idx + 1}")
            if 'ai_answers' not in session_data:
                session_data['ai_answers'] = []
            session_data['ai_answers'].append({
                "question_idx": current_question_idx + 1,
                "ai_answer": "N/A"
            })
            return "N/A"

        prompt = (
            f"Provide a detailed and structured sample answer for the following interview question: '{question}'. "
            f"The answer should demonstrate deep technical knowledge or relevant experience appropriate for the role of {session_data['role']} in {session_data['domain']}. "
            f"Format the answer as a concise paragraph without additional headings or numbering."
        )

        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=AIzaSyCVyhDktWeeV7rvUxz1GBSKNQCPBTvK8uY",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        if 'candidates' in result and result['candidates']:
            generated_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
            if 'ai_answers' not in session_data:
                session_data['ai_answers'] = []
            session_data['ai_answers'].append({
                "question_idx": current_question_idx + 1,
                "ai_answer": generated_text
            })
            logger.info(f"Generated AI answer for question {current_question_idx + 1}: {generated_text[:100]}...")
            return generated_text
        else:
            logger.error(f"Gemini API returned no candidates for question {current_question_idx + 1}")
            if 'ai_answers' not in session_data:
                session_data['ai_answers'] = []
            session_data['ai_answers'].append({
                "question_idx": current_question_idx + 1,
                "ai_answer": "Unable to generate AI answer due to API error."
            })
            return "Unable to generate AI answer due to API error."
    except requests.exceptions.RequestException as e:
        logger.error(f"Gemini API request failed for question {current_question_idx + 1}: {str(e)}")
        if 'ai_answers' not in sessions[session_id]:
            sessions[session_id]['ai_answers'] = []
        sessions[session_id]['ai_answers'].append({
            "question_idx": current_question_idx + 1,
            "ai_answer": "Unable to generate AI answer due to API error."
        })
        return "Unable to generate AI answer due to API error."
    except Exception as e:
        logger.error(f"Error generating AI answer for question {current_question_idx + 1}: {str(e)}")
        if 'ai_answers' not in sessions[session_id]:
            sessions[session_id]['ai_answers'] = []
        sessions[session_id]['ai_answers'].append({
            "question_idx": current_question_idx + 1,
            "ai_answer": "Unable to generate AI answer due to an error."
        })
        return "Unable to generate AI answer due to an error."

if __name__ == '__main__':
<<<<<<< HEAD
    app.run(debug=True,port=5003)
=======
    app.run(debug=True, port=9999, threaded=True)
>>>>>>> 8a9a5ef523a840655d56f689819a3048cc161e0a
