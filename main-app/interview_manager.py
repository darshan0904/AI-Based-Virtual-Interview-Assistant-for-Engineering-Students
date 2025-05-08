import os
import uuid
import re
import pyttsx3
import google.generativeai as genai

class InterviewManager:
    def __init__(self, upload_folder='uploads', api_key=None):
        self.upload_folder = upload_folder
        self.data_folder = os.path.join(upload_folder, 'data')
        self.imp_question_folder = os.path.join(upload_folder, 'imp', 'questions')
        os.makedirs(self.data_folder, exist_ok=True)
        os.makedirs(self.imp_question_folder, exist_ok=True)
        self.domains = [
            "Software Development", "Data Science & AI", "Cybersecurity", "UI/UX Design",
            "Cloud & Infrastructure", "Marketing & Sales", "Human Resources", "Finance & Business Analysis"
        ]
        self.roles = {
            "Software Development": ["Frontend Developer", "Backend Developer", "Full Stack Developer", "DevOps Engineer", "Mobile App Developer"],
            "Data Science & AI": ["Data Analyst", "Data Scientist", "Machine Learning Engineer", "AI Researcher", "NLP Engineer"],
            "Cybersecurity": ["Security Analyst", "Penetration Tester", "Security Engineer", "SOC Analyst", "Cybersecurity Consultant"],
            "UI/UX Design": ["UX Designer", "UI Designer", "Product Designer", "Interaction Designer", "UX Researcher"],
            "Cloud & Infrastructure": ["Cloud Engineer", "Solutions Architect", "Site Reliability Engineer", "Cloud Consultant", "Platform Engineer"],
            "Marketing & Sales": ["Digital Marketer", "SEO Specialist", "Content Strategist", "Sales Executive", "Brand Manager"],
            "Human Resources": ["HR Executive", "Talent Acquisition Specialist", "HRBP (Business Partner)", "L&D Coordinator", "Recruitment Coordinator"],
            "Finance & Business Analysis": ["Financial Analyst", "Business Analyst", "Investment Analyst", "Risk Consultant", "Corporate Strategist"]
        }
        self.sessions = {}
        # Initialize Gemini API
        try:
            genai.configure(api_key=api_key)
            preferred_models = ['gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro']
            models = genai.list_models()
            available_models = [model.name for model in models]
            self.model_name = next((model for model in preferred_models if f'models/{model}' in available_models), None)
            if self.model_name:
                self.model = genai.GenerativeModel(self.model_name)
                print(f"Using model: {self.model_name}")
            else:
                raise Exception("No suitable model found.")
        except Exception as e:
            print(f"Failed to initialize Gemini API: {e}. Using fallback mode.")
            self.model = None

    def start_interview(self, name, domain, role):
        session_id = str(uuid.uuid4())
        sanitized_name = re.sub(r'[^a-zA-Z0-9]', '_', name)
        user_folder = os.path.join(self.data_folder, sanitized_name)
        os.makedirs(user_folder, exist_ok=True)
        user_audio_folder = os.path.join(user_folder, 'audio')
        user_video_folder = os.path.join(user_folder, 'video')
        os.makedirs(user_audio_folder, exist_ok=True)
        os.makedirs(user_video_folder, exist_ok=True)
        self.sessions[session_id] = {
            "name": name, "sanitized_name": sanitized_name, "domain": domain, "role": role,
            "current_question": 0, "responses": [], "questions": [], "domains": [],
            "user_folder": user_folder, "audio_folder": user_audio_folder, "video_folder": user_video_folder
        }
        transcript_path = os.path.join(user_folder, "transcript.txt")
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write(f"{name}\n\n")
        return session_id

    def generate_questions(self, session_id, domain, role, name):
        if session_id not in self.sessions:
            return {"error": "Session not found"}, 404
        prompts = [
            (f"Generate 2 basic introduction questions for {name}.", "Introduction", 2),
            (f"Generate 4 technical questions for {role} in {domain}.", "Role-Specific", 4)
        ]
        questions = []
        question_domains = []
        for prompt, category, count in prompts:
            if not self.model:
                questions.extend([f"Fallback {category} question {i+1}" for i in range(count)])
                question_domains.extend([category] * count)
            else:
                try:
                    response = self.model.generate_content(prompt)
                    text = response.text.strip().split('\n')[:count]
                    questions.extend(text)
                    question_domains.extend([category] * count)
                except:
                    questions.extend([f"Fallback {category} question {i+1}" for i in range(count)])
                    question_domains.extend([category] * count)
        self.sessions[session_id]['questions'] = questions
        self.sessions[session_id]['domains'] = question_domains
        question_path = os.path.join(self.sessions[session_id]['user_folder'], 'questions.txt')
        with open(question_path, 'w') as f:
            for i, (q, d) in enumerate(zip(questions, question_domains), 1):
                f.write(f"Question {i}: {q}\nDomain: {d}\n\n")
        return {"questions": questions}

    def next_question(self, session_id, question):
        if session_id not in self.sessions:
            return {"end": True}
        session_data = self.sessions[session_id]
        sanitized_username = session_data['sanitized_name']
        engine = pyttsx3.init()
        audio_filename = f"question_{sanitized_username}_{session_data['current_question'] + 1}.wav"
        audio_path = os.path.join(self.imp_question_folder, audio_filename)
        engine.save_to_file(question, audio_path)
        engine.runAndWait()
        session_data['current_question'] += 1
        audio_url = f"/uploads/imp/questions/{audio_filename}"
        return {"question": question, "audio": audio_url}

    def record_response(self, session_id, audio_file, video_file, transcript, question_idx):
        if session_id not in self.sessions:
            return {"error": "Session not found"}, 404
        session_data = self.sessions[session_id]
        current_question = question_idx
        sanitized_username = session_data['sanitized_name']
        audio_filename = f"{sanitized_username}_q{current_question}_audio.wav" if audio_file else None
        video_filename = f"{sanitized_username}_q{current_question}_video.mp4" if video_file else None
        if audio_file:
            audio_file.save(os.path.join(session_data['audio_folder'], audio_filename))
        if video_file:
            video_file.save(os.path.join(session_data['video_folder'], video_filename))
        session_data["responses"].append({"audio": audio_filename, "video": video_filename})
        question = session_data['questions'][current_question - 1]
        q_domain = session_data['domains'][current_question - 1]
        ai_answer = self.generate_ai_answer(question)
        transcript_entry = f"Question {current_question}: {question}\nUser Answer: {transcript}\nAI Answer: {ai_answer}\nDomain: {q_domain}\nAudio File: {audio_filename or 'Not recorded'}\nVideo File: {video_filename or 'Not recorded'}\n\n{'=' * 80}\n\n"
        transcript_path = os.path.join(session_data['user_folder'], "transcript.txt")
        with open(transcript_path, 'a', encoding='utf-8') as f:
            f.write(transcript_entry)
        return {"status": "success"}

    def generate_ai_answer(self, question):
        return "Sample AI response based on question context."

    def get_roles(self, domain):
        return self.roles.get(domain, [])