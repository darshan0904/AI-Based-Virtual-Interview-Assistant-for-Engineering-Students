from flask import Flask, render_template, request, jsonify, send_file
import os
import requests
import pyttsx3
import uuid
import re
import PyPDF2

app = Flask(__name__)

DATA_FOLDER = 'data'
IMP_QUESTION_FOLDER = os.path.join('IMP', 'questions')
os.makedirs(DATA_FOLDER, exist_ok=True)
os.makedirs(IMP_QUESTION_FOLDER, exist_ok=True)

ENGINEERING_FIELDS = [
    "Computer Engineering",
    "Mechanical Engineering",
    "Electrical Engineering",
    "Civil Engineering",
    "Electronics & Communication Engineering",
    "Chemical Engineering",
    "Biomedical Engineering",
    "Aerospace Engineering",
    "Industrial Engineering",
    "Environmental Engineering"
]

DOMAINS = {
    "Computer Engineering": [
        "Software Development",
        "Data Science & AI",
        "Cybersecurity",
        "UI/UX Design",
        "Cloud & Infrastructure",
        "Blockchain & Web3",
        "Embedded Systems",
        "Game Development"
    ],
    "Mechanical Engineering": [
        "Automotive Engineering",
        "Robotics",
        "Manufacturing",
        "HVAC",
        "Design & CAD",
        "Aerospace Systems",
        "Material Science",
        "Energy Systems"
    ],
    "Electrical Engineering": [
        "Power Systems",
        "Control Systems",
        "Electronics Design",
        "Embedded Systems",
        "Telecommunications",
        "Lighting & Power",
        "Automation",
        "Renewable Energy"
    ],
    "Civil Engineering": [
        "Structural Engineering",
        "Construction Management",
        "Geotechnical Engineering",
        "Transportation Engineering",
        "Water Resources",
        "Environmental Engineering",
        "Urban Planning",
        "Surveying"
    ],
    "Electronics & Communication Engineering": [
        "VLSI Design",
        "Embedded Systems",
        "Telecommunications",
        "Signal Processing",
        "Consumer Electronics",
        "Instrumentation",
        "Automation & Robotics",
        "Optoelectronics"
    ],
    "Chemical Engineering": [
        "Process Engineering",
        "Pharmaceuticals",
        "Petrochemicals",
        "Environmental",
        "Food & Beverage",
        "Polymers & Plastics",
        "Fertilizers & Agrochemicals",
        "Energy & Fuel Cells"
    ],
    "Biomedical Engineering": [
        "Medical Devices",
        "Biomechanics",
        "Medical Imaging",
        "Clinical Engineering",
        "Bioinformatics",
        "Tissue Engineering",
        "Neuroengineering",
        "Rehabilitation Engineering"
    ],
    "Aerospace Engineering": [
        "Aerodynamics",
        "Propulsion",
        "Structures",
        "Avionics",
        "Space Systems",
        "Flight Testing",
        "Manufacturing",
        "Defense Systems"
    ],
    "Industrial Engineering": [
        "Operations Research",
        "Quality Engineering",
        "Supply Chain Management",
        "Manufacturing Systems",
        "Human Factors",
        "Production Planning",
        "Data Analytics",
        "Cost Engineering"
    ],
    "Environmental Engineering": [
        "Water Treatment",
        "Air Pollution Control",
        "Waste Management",
        "Sustainability",
        "Environmental Impact Assessment",
        "Climate Change",
        "Renewable Energy",
        "Regulations & Policy"
    ]
}

ROLES = {
    "Software Development": ["Frontend Developer", "Backend Developer", "Full Stack Developer", "DevOps Engineer", "Mobile App Developer", "Software Architect"],
    "Data Science & AI": ["Data Analyst", "Data Scientist", "Machine Learning Engineer", "AI Researcher", "NLP Engineer", "Deep Learning Engineer"],
    "Cybersecurity": ["Security Analyst", "Penetration Tester", "Security Engineer", "SOC Analyst", "Cybersecurity Consultant", "Threat Hunter"],
    "UI/UX Design": ["UX Designer", "UI Designer", "Product Designer", "Interaction Designer", "UX Researcher", "Design Systems Engineer"],
    "Cloud & Infrastructure": ["Cloud Engineer", "Solutions Architect", "Site Reliability Engineer", "Cloud Consultant", "Platform Engineer", "Infrastructure Engineer"],
    "Blockchain & Web3": ["Smart Contract Developer", "Blockchain Engineer", "Crypto Analyst", "DeFi Developer", "Security Auditor", "Tokenomics Consultant"],
    "Embedded Systems": ["Embedded Software Engineer", "Firmware Developer", "IoT Developer", "RTOS Specialist", "Systems Integrator", "Board Support Engineer"],
    "Game Development": ["Game Developer", "Gameplay Programmer", "Game Designer", "Graphics Programmer", "Level Designer", "Game Tester"],
    "Automotive Engineering": ["Vehicle Dynamics Engineer", "Powertrain Engineer", "CAE Analyst", "NVH Engineer", "Design Engineer", "Test Engineer"],
    "Robotics": ["Robotics Engineer", "Automation Engineer", "Controls Engineer", "Mechatronics Engineer", "System Integrator", "Simulation Engineer"],
    "Manufacturing": ["Production Engineer", "Process Engineer", "Manufacturing Engineer", "Tool Designer", "CNC Programmer", "Quality Inspector"],
    "HVAC": ["HVAC Engineer", "Thermal Analyst", "Refrigeration Engineer", "Energy Auditor", "Building Systems Engineer", "HVAC Designer"],
    "Design & CAD": ["CAD Engineer", "Design Engineer", "Product Designer", "Mechanical Drafter", "Simulation Engineer", "PLM Specialist"],
    "Aerospace Systems": ["Flight Systems Engineer", "Propulsion Engineer", "Stress Analyst", "CFD Engineer", "Avionics Integrator", "Aircraft Design Engineer"],
    "Material Science": ["Materials Engineer", "Metallurgist", "Composite Engineer", "Failure Analyst", "Testing Technician", "Ceramics Specialist"],
    "Energy Systems": ["Thermal Engineer", "Power Plant Engineer", "Renewable Energy Engineer", "Turbomachinery Specialist", "Energy Analyst", "Thermodynamics Specialist"],
    "Power Systems": ["Power Systems Engineer", "Substation Designer", "Transmission Engineer", "Grid Analyst", "Load Flow Analyst", "Protection Engineer"],
    "Control Systems": ["Control Engineer", "Automation Engineer", "Process Control Engineer", "PLC Programmer", "SCADA Developer", "HMI Developer"],
    "Electronics Design": ["PCB Designer", "Circuit Design Engineer", "Analog Engineer", "Signal Integrity Engineer", "Component Engineer", "Test Engineer"],
    "Telecommunications": ["Network Engineer", "RF Engineer", "Telecom Engineer", "Signal Processing Engineer", "5G Researcher", "Wireless Communications Analyst"],
    "Lighting & Power": ["Lighting Designer", "Electrical Designer", "Building Services Engineer", "Energy Efficiency Consultant", "Compliance Officer", "Load Analyst"],
    "Automation": ["Industrial Automation Engineer", "Drives Engineer", "Instrumentation Engineer", "Panel Designer", "Field Service Engineer", "Factory Systems Specialist"],
    "Renewable Energy": ["Solar Design Engineer", "Wind Turbine Technician", "Energy Auditor", "Grid Integration Specialist", "Sustainability Consultant", "Battery Systems Engineer"],
    "Structural Engineering": ["Structural Engineer", "Bridge Designer", "Seismic Analyst", "Steel Designer", "Concrete Specialist", "Draftsman"],
    "Construction Management": ["Project Manager", "Site Engineer", "Planning Engineer", "Quantity Surveyor", "Construction Scheduler", "Procurement Manager"],
    "Geotechnical Engineering": ["Geotechnical Engineer", "Soil Analyst", "Foundation Designer", "Slope Stability Analyst", "Drilling Supervisor", "Geo-Structural Engineer"],
    "Transportation Engineering": ["Traffic Analyst", "Highway Engineer", "Railway Engineer", "Urban Planner", "Pavement Designer", "Transport Policy Analyst"],
    "Water Resources": ["Hydraulic Engineer", "Irrigation Engineer", "Stormwater Manager", "Hydrologist", "Canal Designer", "Dam Safety Specialist"],
    "Environmental Engineering": ["Wastewater Engineer", "Water Treatment Specialist", "Air Quality Analyst", "Solid Waste Manager", "Sustainability Analyst", "Climate Engineer"],
    "Urban Planning": ["Urban Designer", "Zoning Analyst", "GIS Specialist", "Land Use Planner", "City Infrastructure Consultant", "Smart City Planner"],
    "Surveying": ["Surveyor", "GIS Technician", "Mapping Analyst", "Remote Sensing Specialist", "Drone Survey Specialist", "Topographer"],
    "VLSI Design": ["VLSI Engineer", "ASIC Designer", "FPGA Engineer", "RTL Designer", "Physical Design Engineer", "Verification Engineer"],
    "Signal Processing": ["DSP Engineer", "Audio Signal Processor", "Image Processing Specialist", "Speech Processing Engineer", "RF Signal Analyst", "Waveform Developer"],
    "Consumer Electronics": ["Product Developer", "Testing Engineer", "Hardware Engineer", "Quality Analyst", "Repair Specialist", "Field Support Engineer"],
    "Instrumentation": ["Instrumentation Engineer", "Measurement Analyst", "Sensor Integration Engineer", "Calibration Engineer", "Control Systems Engineer", "Test Bench Developer"],
    "Automation & Robotics": ["Robotics Developer", "PLC Programmer", "Embedded Roboticist", "Electronics Systems Integrator", "Mechatronics Developer", "System Designer"],
    "Optoelectronics": ["Optical Engineer", "Laser Systems Engineer", "Photonics Specialist", "Fiber Optics Engineer", "Electro-Optics Technician", "Lidar Systems Engineer"],
    "Process Engineering": ["Process Engineer", "Chemical Plant Operator", "Simulation Analyst", "Production Planner", "Plant Design Engineer", "Scale-up Engineer"],
    "Pharmaceuticals": ["Formulation Chemist", "Quality Control Analyst", "Regulatory Affairs Specialist", "R&D Scientist", "Manufacturing Chemist", "Validation Engineer"],
    "Petrochemicals": ["Petroleum Engineer", "Refinery Operator", "Pipeline Engineer", "Oil & Gas Analyst", "Downstream Process Engineer", "Reservoir Engineer"],
    "Environmental": ["Waste Treatment Engineer", "Air Emissions Analyst", "Green Chemistry Researcher", "Compliance Officer", "Sustainability Engineer", "Hazardous Waste Specialist"],
    "Food & Beverage": ["Food Process Engineer", "Quality Assurance Manager", "Production Manager", "Food Technologist", "Packaging Engineer", "Hygiene Specialist"],
    "Polymers & Plastics": ["Polymer Engineer", "Plastic Processing Technician", "Material Scientist", "Injection Molding Engineer", "Extrusion Operator", "Composite Materials Engineer"],
    "Fertilizers & Agrochemicals": ["Agrochemical Developer", "Process Chemist", "Fertilizer Plant Operator", "Soil Scientist", "Agronomist", "Field Application Engineer"],
    "Energy & Fuel Cells": ["Fuel Cell Engineer", "Battery Chemist", "Electrochemical Engineer", "Energy Storage Specialist", "Hydrogen Systems Analyst", "Energy Systems Modeler"],
    "Medical Devices": ["Device Design Engineer", "Validation Specialist", "Biomedical Technician", "Testing Engineer", "Clinical Engineer", "Regulatory Engineer"],
    "Biomechanics": ["Biomechanical Engineer", "Gait Analyst", "Orthopedic Design Engineer", "Rehabilitation Engineer", "Ergonomics Specialist", "Motion Capture Analyst"],
    "Medical Imaging": ["MRI Specialist", "CT Imaging Technician", "Ultrasound Engineer", "Radiology Technologist", "Imaging Software Developer", "Biomedical Signal Analyst"],
    "Clinical Engineering": ["Clinical Equipment Specialist", "Maintenance Engineer", "Clinical Trials Analyst", "Hospital Systems Engineer", "Medical Equipment Planner", "Service Engineer"],
    "Bioinformatics": ["Genomics Analyst", "Biomedical Data Scientist", "Biostatistician", "Molecular Modeler", "Database Curator", "Computational Biologist"],
    "Tissue Engineering": ["Biomaterials Scientist", "Tissue Engineer", "Stem Cell Researcher", "Regenerative Medicine Specialist", "Biomedical Research Associate", "Histology Analyst"],
    "Neuroengineering": ["Neural Interface Engineer", "EEG Specialist", "BCI Developer", "Neuroprosthetics Developer", "Brain Imaging Analyst", "Neurosignal Analyst"],
    "Rehabilitation Engineering": ["Assistive Tech Developer", "Prosthetics Engineer", "Rehab Equipment Designer", "Mobility Solutions Specialist", "Accessibility Engineer", "Therapy Tech Innovator"],
    "Aerodynamics": ["CFD Analyst", "Wind Tunnel Specialist", "Flight Dynamics Engineer", "Aircraft Performance Analyst", "Airflow Simulation Expert", "Aero Design Engineer"],
    "Propulsion": ["Jet Engine Designer", "Rocket Propulsion Engineer", "Combustion Analyst", "Turbine Engineer", "Propellant Researcher", "Engine Systems Engineer"],
    "Structures": ["Aircraft Structures Analyst", "Stress Engineer", "Fatigue Analyst", "Composite Materials Expert", "Crashworthiness Engineer", "Vibration Analyst"],
    "Avionics": ["Avionics Systems Engineer", "Navigation Systems Developer", "Flight Control Software Developer", "Communication Systems Analyst", "Cockpit Interface Designer", "Radar Engineer"],
    "Space Systems": ["Satellite Engineer", "Orbital Analyst", "Launch Systems Designer", "Spacecraft Systems Engineer", "Payload Integrator", "Ground Station Engineer"],
    "Flight Testing": ["Flight Test Engineer", "Instrumentation Engineer", "Telemetry Analyst", "Flight Data Processor", "Pilot Support Engineer", "Airworthiness Analyst"],
    "Defense Systems": ["Weapons Systems Engineer", "Missile Design Engineer", "Guidance Systems Analyst", "Radar Systems Engineer", "Surveillance Systems Developer", "Defense Integration Specialist"],
    "Operations Research": ["Operations Analyst", "Optimization Specialist", "Logistics Modeler", "Supply Chain Analyst", "Simulation Engineer", "Systems Analyst"],
    "Quality Engineering": ["Quality Engineer", "Six Sigma Specialist", "QA/QC Inspector", "Process Auditor", "Lean Manufacturing Consultant", "Standards Compliance Analyst"],
    "Supply Chain Management": ["Supply Chain Planner", "Procurement Officer", "Inventory Manager", "Logistics Coordinator", "Vendor Manager", "Freight Analyst"],
    "Manufacturing Systems": ["Plant Layout Designer", "Process Engineer", "Factory Automation Expert", "Industrial Systems Engineer", "Assembly Line Planner", "Maintenance Planner"],
    "Human Factors": ["Ergonomics Analyst", "User Experience Engineer", "Workplace Safety Specialist", "Cognitive Systems Analyst", "Human-Machine Interface Designer", "Task Analyst"],
    "Production Planning": ["Production Planner", "Operations Scheduler", "Material Requirement Planner", "Capacity Analyst", "Shop Floor Controller", "Workflow Coordinator"],
    "Data Analytics": ["Industrial Data Analyst", "Operations BI Developer", "Process Mining Analyst", "Predictive Maintenance Engineer", "Dashboard Developer", "Decision Support Analyst"],
    "Cost Engineering": ["Cost Estimator", "Budget Analyst", "Value Engineer", "Cost Controller", "Bid Analyst", "Profitability Analyst"],
    "Water Treatment": ["Water Treatment Engineer", "Hydrologist", "Filtration Specialist", "Water Quality Analyst", "Desalination Expert", "Process Design Engineer"],
    "Air Pollution Control": ["Air Quality Engineer", "Emissions Analyst", "Stack Testing Technician", "Carbon Capture Researcher", "Atmospheric Modeler", "Environmental Compliance Officer"],
    "Waste Management": ["Solid Waste Engineer", "Recycling Specialist", "Landfill Engineer", "Hazardous Waste Manager", "Composting Facility Planner", "E-Waste Specialist"],
    "Sustainability": ["Sustainability Consultant", "Carbon Footprint Analyst", "Green Building Advisor", "Environmental Strategist", "Sustainable Energy Planner", "ESG Analyst"],
    "Environmental Impact Assessment": ["EIA Consultant", "Biodiversity Analyst", "Ecological Surveyor", "Impact Modeler", "Compliance Reporter", "Remediation Planner"],
    "Climate Change": ["Climate Data Analyst", "Carbon Credit Consultant", "Resilience Planner", "Adaptation Specialist", "Global Climate Modeler", "Mitigation Strategist"],
    "Regulations & Policy": ["Environmental Policy Analyst", "Regulatory Affairs Specialist", "Compliance Auditor", "Public Policy Advisor", "Sustainability Reporting Officer", "Environmental Law Associate"]
}

sessions = {}

@app.route('/')
def index():
    return render_template('index.html', engineering_fields=ENGINEERING_FIELDS)

@app.route('/get_domains', methods=['POST'])
def get_domains():
    data = request.json
    engineering = data.get('engineering')
    app.logger.info(f"Received request for domains in engineering: {engineering}")
    domains = DOMAINS.get(engineering, [])
    app.logger.info(f"Returning domains: {domains}")
    return jsonify({"domains": domains})

@app.route('/get_roles', methods=['POST'])
def get_roles():
    data = request.json
    domain = data.get('domain')
    app.logger.info(f"Received request for roles in domain: {domain}")
    roles = ROLES.get(domain, [])
    app.logger.info(f"Returning roles: {roles}")
    return jsonify({"roles": roles})

@app.route('/start_interview', methods=['POST'])
def start_interview():
    session_id = str(uuid.uuid4())
    name = request.form.get('name')
    engineering = request.form.get('engineering')
    domain = request.form.get('domain')
    role = request.form.get('role')
    resume = request.files.get('resume')

    sanitized_name = re.sub(r'[^a-zA-Z0-9]', '_', name)

    user_folder = os.path.join(DATA_FOLDER, sanitized_name)
    os.makedirs(user_folder, exist_ok=True)
    user_audio_folder = os.path.join(user_folder, 'audio')
    user_video_folder = os.path.join(user_folder, 'video')
    os.makedirs(user_audio_folder, exist_ok=True)
    os.makedirs(user_video_folder, exist_ok=True)

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
            app.logger.info(f"Extracted resume text: {resume_text[:500]}...")
        except Exception as e:
            app.logger.error(f"Failed to parse resume: {str(e)}")
            resume_text = None

    sessions[session_id] = {
        "name": name,
        "sanitized_name": sanitized_name,
        "engineering": engineering,
        "domain": domain,
        "role": role,
        "resume": resume.filename if resume else None,
        "resume_text": resume_text,
        "current_question": 0,
        "responses": [],
        "questions": [],
        "domains": [],
        "user_folder": user_folder,
        "audio_folder": user_audio_folder,
        "video_folder": user_video_folder
    }

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
def generate_questions(session_id):
    if session_id not in sessions:
        return jsonify({"error": "Session not found"}), 404

    data = request.json
    domain = data.get('domain')
    role = data.get('role')
    has_resume = data.get('has_resume')
    name = sessions[session_id]['name']
    resume_text = sessions[session_id].get('resume_text', '')

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
        prompts.insert(1, (f"Generate exactly 3 technically focused resume-based interview questions for a candidate named {name} applying for the role of {role} in {domain}. Assume the resume includes typical experiences and projects for this role, and ask about specific project details to assess deep technical knowledge and problem-solving skills. Format each question as a single line without numbering.", "Resume-Based", 3))

    questions = []
    question_domains = []

    def fetch_questions(prompt, category, count):
        try:
            response = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=AIzaSyDQW2Db-ZryHQ04iXgl4Is5aK9ANJy7i5A",
                json={"contents": [{"parts": [{"text": prompt}]}]}
            )
            response.raise_for_status()
            result = response.json()
            if 'candidates' not in result or not result['candidates']:
                app.logger.error(f"API response error for category {category}: {result}")
                return [f"Fallback question {i+1} for {category}" for i in range(count)]
            generated_text = result['candidates'][0]['content']['parts'][0]['text']
            category_questions = [q.strip() for q in generated_text.split('\n') if q.strip() and not q.startswith('#')]
            category_questions = [re.sub(r'^\d+\.\s*', '', q).strip() for q in category_questions]
            if len(category_questions) < count:
                category_questions.extend([f"Fallback question {i+1} for {category}" for i in range(count - len(category_questions))])
            elif len(category_questions) > count:
                category_questions = category_questions[:count]
            return category_questions
        except Exception as e:
            app.logger.error(f"Error generating questions for category {category}: {str(e)}")
            return [f"Fallback question {i+1} for {category}" for i in range(count)]

    for prompt, category, count in prompts:
        category_questions = fetch_questions(prompt, category, count)
        questions.extend(category_questions)
        question_domains.extend([category] * count)

    app.logger.info(f"Generated questions for session {session_id}:")
    for i, (q, d) in enumerate(zip(questions, question_domains), 1):
        app.logger.info(f"Question {i}: {q} (Domain: {d})")

    question_path = os.path.join(sessions[session_id]['user_folder'], 'questions.txt')
    with open(question_path, 'w') as f:
        for i, (question, q_domain) in enumerate(zip(questions, question_domains), 1):
            f.write(f"Question {i}: {question}\n")
            f.write(f"Domain: {q_domain}\n\n")

    sessions[session_id]['questions'] = questions
    sessions[session_id]['domains'] = question_domains

    return jsonify({"questions": questions})

@app.route('/next_question/<session_id>', methods=['POST'])
def next_question(session_id):
    if session_id not in sessions:
        return jsonify({"end": True})

    session_data = sessions[session_id]
    current_question_idx = session_data['current_question']
    questions = session_data['questions']
    
    if current_question_idx >= len(questions):
        return jsonify({"end": True})

    question = questions[current_question_idx]
    sanitized_username = session_data['sanitized_name']

    engine = pyttsx3.init()
    engine.setProperty('rate', 150)
    audio_filename = f"question_{sanitized_username}_{current_question_idx + 1}.wav"
    audio_path = os.path.join(IMP_QUESTION_FOLDER, audio_filename)
    engine.save_to_file(question, audio_path)
    engine.runAndWait()

    ai_answer = generate_ai_answer(session_id, question)

    session_data['current_question'] += 1
    audio_url = f"/imp/questions/{audio_filename}"
    return jsonify({"ai_answer": ai_answer, "audio": audio_url})

@app.route('/imp/questions/<filename>')
def serve_imp_question(filename):
    file_path = os.path.join(IMP_QUESTION_FOLDER, filename)
    if os.path.exists(file_path):
        return send_file(file_path, mimetype='audio/wav')
    return jsonify({"error": "File not found"}), 404

@app.route('/record_response/<session_id>', methods=['POST'])
def record_response(session_id):
    if session_id not in sessions:
        app.logger.error(f"Session {session_id} not found in sessions dict")
        return jsonify({"error": "Session not found"}), 404

    audio = request.files.get('audio')
    video = request.files.get('video')
    transcript = request.form.get('transcript')

    session_data = sessions[session_id]
    current_question = session_data['current_question']
    sanitized_username = session_data['sanitized_name']
    user_folder = session_data['user_folder']

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

    transcript_path = os.path.join(user_folder, "transcript.txt")
    try:
        with open(transcript_path, 'a', encoding='utf-8') as f:
            f.write(transcript)
        app.logger.info(f"Successfully appended to transcript for question {current_question}")
    except Exception as e:
        app.logger.error(f"Failed to append to transcript file: {str(e)}")
        return jsonify({"error": f"Failed to append to transcript file: {str(e)}"}), 500

    return jsonify({"status": "success"})

def generate_ai_answer(session_id, question):
    domain = sessions[session_id]['domains'][sessions[session_id]['current_question'] - 1]
    if domain == "Introduction":
        return "N/A"

    prompt = f"Provide a detailed and structured sample answer for the following interview question: '{question}'. The answer should demonstrate deep technical knowledge or relevant experience appropriate for the question's context. Format the answer as a concise paragraph without additional headings or numbering."
    
    try:
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=AIzaSyDQW2Db-ZryHQ04iXgl4Is5aK9ANJy7i5A",
            json={"contents": [{"parts": [{"text": prompt}]}]}
        )
        response.raise_for_status()
        result = response.json()
        if 'candidates' in result and result['candidates']:
            generated_text = result['candidates'][0]['content']['parts'][0]['text']
            return generated_text.strip()
        else:
            app.logger.error(f"API response error for AI answer: {result}")
            return "Unable to generate AI answer due to API error."
    except Exception as e:
        app.logger.error(f"Error generating AI answer: {str(e)}")
        return "Unable to generate AI answer due to an error."

if __name__ == '__main__':
    app.run(debug=True,port=9393)