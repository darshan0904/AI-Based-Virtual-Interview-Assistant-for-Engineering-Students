from flask import Flask, render_template, request, jsonify, send_file
import os
import requests
import pyttsx3
import uuid
import re
import PyPDF2
import logging
from werkzeug.utils import secure_filename
import av
import wave
import io
import numpy as np
import tempfile

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATA_FOLDER = 'data'
IMP_QUESTION_FOLDER = os.path.join('IMP', 'questions')
os.makedirs(DATA_FOLDER, exist_ok=True, mode=0o755)
os.makedirs(IMP_QUESTION_FOLDER, exist_ok=True, mode=0o755)

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
    "Electrical Engineering": [
        "Power Systems", "Control Systems", "Electronics Design", "Embedded Systems",
        "Telecommunications", "Lighting & Power", "Automation", "Renewable Energy"
    ],
    "Civil Engineering": [
        "Structural Engineering", "Construction Management", "Geotechnical Engineering",
        "Transportation Engineering", "Water Resources", "Environmental Engineering",
        "Urban Planning", "Surveying"
    ],
    "Electronics & Communication Engineering": [
        "VLSI Design", "Embedded Systems", "Telecommunications", "Signal Processing",
        "Consumer Electronics", "Instrumentation", "Automation & Robotics", "Optoelectronics"
    ],
    "Chemical Engineering": [
        "Process Engineering", "Pharmaceuticals", "Petrochemicals", "Environmental",
        "Food & Beverage", "Polymers & Plastics", "Fertilizers & Agrochemicals",
        "Energy & Fuel Cells"
    ],
    "Biomedical Engineering": [
        "Medical Devices", "Biomechanics", "Medical Imaging", "Clinical Engineering",
        "Bioinformatics", "Tissue Engineering", "Neuroengineering", "Rehabilitation Engineering"
    ],
    "Aerospace Engineering": [
        "Aerodynamics", "Propulsion", "Structures", "Avionics", "Space Systems",
        "Flight Testing", "Manufacturing", "Defense Systems"
    ],
    "Industrial Engineering": [
        "Operations Research", "Quality Engineering", "Supply Chain Management",
        "Manufacturing Systems", "Human Factors", "Production Planning", "Data Analytics",
        "Cost Engineering"
    ],
    "Environmental Engineering": [
        "Water Treatment", "Air Pollution Control", "Waste Management", "Sustainability",
        "Environmental Impact Assessment", "Climate Change", "Renewable Energy",
        "Regulations & Policy"
    ]
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
    "Cybersecurity": [
        "Security Analyst", "Penetration Tester", "Security Engineer",
        "SOC Analyst", "Cybersecurity Consultant", "Threat Hunter"
    ],
    "UI/UX Design": [
        "UX Designer", "UI Designer", "Product Designer", "Interaction Designer",
        "UX Researcher", "Design Systems Engineer"
    ],
    "Cloud & Infrastructure": [
        "Cloud Engineer", "Solutions Architect", "Site Reliability Engineer",
        "Cloud Consultant", "Platform Engineer", "Infrastructure Engineer"
    ],
    "Blockchain & Web3": [
        "Smart Contract Developer", "Blockchain Engineer", "Crypto Analyst",
        "DeFi Developer", "Security Auditor", "Tokenomics Consultant"
    ],
    "Embedded Systems": [
        "Embedded Software Engineer", "Firmware Developer", "IoT Developer",
        "RTOS Specialist", "Systems Integrator", "Board Support Engineer",
        "Embedded C Developer", "RTOS Engineer", "Microcontroller Programmer",
        "Board Design Engineer", "Testing Engineer", "Firmware Engineer",
        "Embedded Developer", "Microcontroller Programmer", "RTOS Developer",
        "System on Chip (SoC) Engineer"
    ],
    "Game Development": [
        "Game Developer", "Gameplay Programmer", "Game Designer",
        "Graphics Programmer", "Level Designer", "Game Tester"
    ],
    "Automotive Engineering": [
        "Vehicle Dynamics Engineer", "Powertrain Engineer", "CAE Analyst",
        "NVH Engineer", "Design Engineer", "Test Engineer"
    ],
    "Robotics": [
        "Robotics Engineer", "Automation Engineer", "Controls Engineer",
        "Mechatronics Engineer", "System Integrator", "Simulation Engineer"
    ],
    "Manufacturing": [
        "Production Engineer", "Process Engineer", "Manufacturing Engineer",
        "Tool Designer", "CNC Programmer", "Quality Inspector",
        "Aerospace Manufacturing Engineer", "Tooling Engineer", "Production Planner",
        "Assembly Technician", "Composite Fabricator", "Quality Assurance Engineer"
    ],
    "HVAC": [
        "HVAC Engineer", "Thermal Analyst", "Refrigeration Engineer",
        "Energy Auditor", "Building Systems Engineer", "HVAC Designer"
    ],
    "Design & CAD": [
        "CAD Engineer", "Design Engineer", "Product Designer",
        "Mechanical Drafter", "Simulation Engineer", "PLM Specialist"
    ],
    "Aerospace Systems": [
        "Flight Systems Engineer", "Propulsion Engineer", "Stress Analyst",
        "CFD Engineer", "Avionics Integrator", "Aircraft Design Engineer"
    ],
    "Material Science": [
        "Materials Engineer", "Metallurgist", "Composite Engineer",
        "Failure Analyst", "Testing Technician", "Ceramics Specialist"
    ],
    "Energy Systems": [
        "Thermal Engineer", "Power Plant Engineer", "Renewable Energy Engineer",
        "Turbomachinery Specialist", "Energy Analyst", "Thermodynamics Specialist"
    ],
    "Power Systems": [
        "Power Systems Engineer", "Substation Designer", "Transmission Engineer",
        "Grid Analyst", "Load Flow Analyst", "Protection Engineer"
    ],
    "Control Systems": [
        "Control Engineer", "Automation Engineer", "Process Control Engineer",
        "PLC Programmer", "SCADA Developer", "HMI Developer"
    ],
    "Electronics Design": [
        "PCB Designer", "Circuit Design Engineer", "Analog Engineer",
        "Signal Integrity Engineer", "Component Engineer", "Test Engineer"
    ],
    "Telecommunications": [
        "Network Engineer", "RF Engineer", "Telecom Engineer",
        "Signal Processing Engineer", "5G Researcher", "Wireless Communications Analyst",
        "Network Designer", "5G Engineer", "Protocol Developer", "Switching Systems Analyst"
    ],
    "Lighting & Power": [
        "Lighting Designer", "Electrical Designer", "Building Services Engineer",
        "Energy Efficiency Consultant", "Compliance Officer", "Load Analyst"
    ],
    "Automation": [
        "Industrial Automation Engineer", "Drives Engineer", "Instrumentation Engineer",
        "Panel Designer", "Field Service Engineer", "Factory Systems Specialist"
    ],
    "Renewable Energy": [
        "Solar Design Engineer", "Wind Turbine Technician", "Energy Auditor",
        "Grid Integration Specialist", "Sustainability Consultant", "Battery Systems Engineer",
        "Solar Project Developer", "Wind Energy Planner", "Hydropower Engineer",
        "Geothermal Systems Analyst", "Bioenergy Specialist"
    ],
    "Structural Engineering": [
        "Structural Engineer", "Bridge Designer", "Seismic Analyst",
        "Steel Designer", "Concrete Specialist", "Draftsman"
    ],
    "Construction Management": [
        "Project Manager", "Site Engineer", "Planning Engineer",
        "Quantity Surveyor", "Construction Scheduler", "Procurement Manager"
    ],
    "Geotechnical Engineering": [
        "Geotechnical Engineer", "Soil Analyst", "Foundation Designer",
        "Slope Stability Analyst", "Drilling Supervisor", "Geo-Structural Engineer"
    ],
    "Transportation Engineering": [
        "Traffic Analyst", "Highway Engineer", "Railway Engineer",
        "Urban Planner", "Pavement Designer", "Transport Policy Analyst"
    ],
    "Water Resources": [
        "Hydraulic Engineer", "Irrigation Engineer", "Stormwater Manager",
        "Hydrologist", "Canal Designer", "Dam Safety Specialist"
    ],
    "Environmental Engineering": [
        "Wastewater Engineer", "Water Treatment Specialist", "Air Quality Analyst",
        "Solid Waste Manager", "Sustainability Analyst", "Climate Engineer"
    ],
    "Urban Planning": [
        "Urban Designer", "Zoning Analyst", "GIS Specialist",
        "Land Use Planner", "City Infrastructure Consultant", "Smart City Planner"
    ],
    "Surveying": [
        "Surveyor", "GIS Technician", "Mapping Analyst",
        "Remote Sensing Specialist", "Drone Survey Specialist", "Topographer"
    ],
    "VLSI Design": [
        "VLSI Engineer", "ASIC Designer", "FPGA Engineer",
        "RTL Designer", "Physical Design Engineer", "Verification Engineer"
    ],
    "Signal Processing": [
        "DSP Engineer", "Audio Signal Processor", "Image Processing Specialist",
        "Speech Processing Engineer", "RF Signal Analyst", "Waveform Developer"
    ],
    "Consumer Electronics": [
        "Product Developer", "Testing Engineer", "Hardware Engineer",
        "Quality Analyst", "Repair Specialist", "Field Support Engineer"
    ],
    "Instrumentation": [
        "Instrumentation Engineer", "Measurement Analyst", "Sensor Integration Engineer",
        "Calibration Engineer", "Control Systems Engineer", "Test Bench Developer"
    ],
    "Automation & Robotics": [
        "Robotics Developer", "PLC Programmer", "Embedded Roboticist",
        "Electronics Systems Integrator", "Mechatronics Developer", "System Designer"
    ],
    "Optoelectronics": [
        "Optical Engineer", "Laser Systems Engineer", "Photonics Specialist",
        "Fiber Optics Engineer", "Electro-Optics Technician", "Lidar Systems Engineer"
    ],
    "Process Engineering": [
        "Process Engineer", "Chemical Plant Operator", "Simulation Analyst",
        "Production Planner", "Plant Design Engineer", "Scale-up Engineer"
    ],
    "Pharmaceuticals": [
        "Formulation Chemist", "Quality Control Analyst", "Regulatory Affairs Specialist",
        "R&D Scientist", "Manufacturing Chemist", "Validation Engineer"
    ],
    "Petrochemicals": [
        "Petroleum Engineer", "Refinery Operator", "Pipeline Engineer",
        "Oil & Gas Analyst", "Downstream Process Engineer", "Reservoir Engineer"
    ],
    "Environmental": [
        "Waste Treatment Engineer", "Air Emissions Analyst", "Green Chemistry Researcher",
        "Compliance Officer", "Sustainability Engineer", "Hazardous Waste Specialist"
    ],
    "Food & Beverage": [
        "Food Process Engineer", "Quality Assurance Manager", "Production Manager",
        "Food Technologist", "Packaging Engineer", "Hygiene Specialist"
    ],
    "Polymers & Plastics": [
        "Polymer Engineer", "Plastic Processing Technician", "Material Scientist",
        "Injection Molding Engineer", "Extrusion Operator", "Composite Materials Engineer"
    ],
    "Fertilizers & Agrochemicals": [
        "Agrochemical Developer", "Process Chemist", "Fertilizer Plant Operator",
        "Soil Scientist", "Agronomist", "Field Application Engineer"
    ],
    "Energy & Fuel Cells": [
        "Fuel Cell Engineer", "Battery Chemist", "Electrochemical Engineer",
        "Energy Storage Specialist", "Hydrogen Systems Analyst", "Energy Systems Modeler"
    ],
    "Medical Devices": [
        "Device Design Engineer", "Validation Specialist", "Biomedical Technician",
        "Testing Engineer", "Clinical Engineer", "Regulatory Engineer"
    ],
    "Biomechanics": [
        "Biomechanical Engineer", "Gait Analyst", "Orthopedic Design Engineer",
        "Rehabilitation Engineer", "Ergonomics Specialist", "Motion Capture Analyst"
    ],
    "Medical Imaging": [
        "MRI Specialist", "CT Imaging Technician", "Ultrasound Engineer",
        "Radiology Technologist", "Imaging Software Developer", "Biomedical Signal Analyst"
    ],
    "Clinical Engineering": [
        "Clinical Equipment Specialist", "Maintenance Engineer", "Clinical Trials Analyst",
        "Hospital Systems Engineer", "Medical Equipment Planner", "Service Engineer"
    ],
    "Bioinformatics": [
        "Genomics Analyst", "Biomedical Data Scientist", "Biostatistician",
        "Molecular Modeler", "Database Curator", "Computational Biologist"
    ],
    "Tissue Engineering": [
        "Biomaterials Scientist", "Tissue Engineer", "Stem Cell Researcher",
        "Regenerative Medicine Specialist", "Biomedical Research Associate", "Histology Analyst"
    ],
    "Neuroengineering": [
        "Neural Interface Engineer", "EEG Specialist", "BCI Developer",
        "Neuroprosthetics Developer", "Brain Imaging Analyst", "Neurosignal Analyst"
    ],
    "Rehabilitation Engineering": [
        "Assistive Tech Developer", "Prosthetics Engineer", "Rehab Equipment Designer",
        "Mobility Solutions Specialist", "Accessibility Engineer", "Therapy Tech Innovator"
    ],
    "Aerodynamics": [
        "CFD Analyst", "Wind Tunnel Specialist", "Flight Dynamics Engineer",
        "Aircraft Performance Analyst", "Airflow Simulation Expert", "Aero Design Engineer"
    ],
    "Propulsion": [
        "Jet Engine Designer", "Rocket Propulsion Engineer", "Combustion Analyst",
        "Turbine Engineer", "Propellant Researcher", "Engine Systems Engineer"
    ],
    "Structures": [
        "Aircraft Structures Analyst", "Stress Engineer", "Fatigue Analyst",
        "Composite Materials Expert", "Crashworthiness Engineer", "Vibration Analyst"
    ],
    "Avionics": [
        "Avionics Systems Engineer", "Navigation Systems Developer", "Flight Control Software Developer",
        "Communication Systems Analyst", "Cockpit Interface Designer", "Radar Engineer"
    ],
    "Space Systems": [
        "Satellite Engineer", "Orbital Analyst", "Launch Systems Designer",
        "Spacecraft Systems Engineer", "Payload Integrator", "Ground Station Engineer"
    ],
    "Flight Testing": [
        "Flight Test Engineer", "Instrumentation Engineer", "Telemetry Analyst",
        "Flight Data Processor", "Pilot Support Engineer", "Airworthiness Analyst"
    ],
    "Defense Systems": [
        "Weapons Systems Engineer", "Missile Design Engineer", "Guidance Systems Analyst",
        "Radar Systems Engineer", "Surveillance Systems Developer", "Defense Integration Specialist"
    ],
    "Operations Research": [
        "Operations Analyst", "Optimization Specialist", "Logistics Modeler",
        "Supply Chain Analyst", "Simulation Engineer", "Systems Analyst"
    ],
    "Quality Engineering": [
        "Quality Engineer", "Six Sigma Specialist", "QA/QC Inspector",
        "Process Auditor", "Lean Manufacturing Consultant", "Standards Compliance Analyst"
    ],
    "Supply Chain Management": [
        "Supply Chain Planner", "Procurement Officer", "Inventory Manager",
        "Logistics Coordinator", "Vendor Manager", "Freight Analyst"
    ],
    "Manufacturing Systems": [
        "Plant Layout Designer", "Process Engineer", "Factory Automation Expert",
        "Industrial Systems Engineer", "Assembly Line Planner", "Maintenance Planner"
    ],
    "Human Factors": [
        "Ergonomics Analyst", "User Experience Engineer", "Workplace Safety Specialist",
        "Cognitive Systems Analyst", "Human-Machine Interface Designer", "Task Analyst"
    ],
    "Production Planning": [
        "Production Planner", "Operations Scheduler", "Material Requirement Planner",
        "Capacity Analyst", "Shop Floor Controller", "Workflow Coordinator"
    ],
    "Data Analytics": [
        "industrial Data Analyst", "Operations BI Developer", "Process Mining Analyst",
        "Predictive Maintenance Engineer", "Dashboard Developer", "Decision Support Analyst"
    ],
    "Cost Engineering": [
        "Cost Estimator", "Budget Analyst", "Value Engineer",
        "Cost Controller", "Bid Analyst", "Profitability Analyst"
    ],
    "Water Treatment": [
        "Water Treatment Engineer", "Hydrologist", "Filtration Specialist",
        "Water Quality Analyst", "Desalination Expert", "Process Design Engineer"
    ],
    "Air Pollution Control": [
        "Air Quality Engineer", "Emissions Analyst", "Stack Testing Technician",
        "Carbon Capture Researcher", "Atmospheric Modeler", "Environmental Compliance Officer"
    ],
    "Waste Management": [
        "Solid Waste Engineer", "Recycling Specialist", "Landfill Engineer",
        "Hazardous Waste Manager", "Composting Facility Planner", "E-Waste Specialist"
    ],
    "Sustainability": [
        "Sustainability Consultant", "Carbon Footprint Analyst", "Green Building Advisor",
        "Environmental Strategist", "Sustainable Energy Planner", "ESG Analyst"
    ],
    "Environmental Impact Assessment": [
        "EIA Consultant", "Biodiversity Analyst", "Ecological Surveyor",
        "Impact Modeler", "Compliance Reporter", "Remediation Planner"
    ],
    "Climate Change": [
        "Climate Data Analyst", "Carbon Credit Consultant", "Resilience Planner",
        "Adaptation Specialist", "Global Climate Modeler", "Mitigation Strategist"
    ],
    "Regulations & Policy": [
        "Environmental Policy Analyst", "Regulatory Affairs Specialist", "Compliance Auditor",
        "Public Policy Advisor", "Sustainability Reporting Officer", "Environmental Law Associate"
    ]
}

sessions = {}

def convert_webm_to_wav(webm_data, output_path):
    """Convert WebM audio to WAV using pyav and wave."""
    try:
        # Create a temporary file for WebM data
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_webm:
            temp_webm.write(webm_data)
            temp_webm_path = temp_webm.name
            logger.debug(f"Saved raw audio WebM to {temp_webm_path}, size: {os.path.getsize(temp_webm_path)} bytes")

        # Open WebM with pyav
        input_container = av.open(temp_webm_path)
        audio_stream = next((s for s in input_container.streams if s.type == 'audio'), None)
        if not audio_stream:
            logger.error("No audio stream found in WebM")
            input_container.close()
            os.remove(temp_webm_path)
            return False

        # Prepare WAV file
        with wave.open(output_path, 'wb') as wav_file:
            wav_file.setnchannels(audio_stream.channels or 1)
            wav_file.setsampwidth(2)  # 16-bit PCM
            wav_file.setframerate(audio_stream.rate or 44100)

            # Decode audio frames
            for packet in input_container.demux(audio_stream):
                for frame in packet.decode():
                    if frame:
                        samples = frame.to_ndarray()
                        # Ensure mono by averaging channels if stereo
                        if samples.shape[0] > 1:
                            samples = np.mean(samples, axis=0, keepdims=True)
                        # Convert to 16-bit PCM
                        samples = (samples * 32767).astype(np.int16)
                        wav_file.writeframes(samples.tobytes())

        input_container.close()
        os.remove(temp_webm_path)
        if os.path.getsize(output_path) > 0:
            logger.info(f"Converted WebM to WAV: {output_path} (size: {os.path.getsize(output_path)} bytes)")
            return True
        else:
            logger.warning(f"Converted WAV file is empty: {output_path}")
            return False
    except Exception as e:
        logger.error(f"Failed to convert WebM to WAV: {str(e)}")
        if 'temp_webm_path' in locals():
            os.remove(temp_webm_path)
        return False

def convert_webm_to_mp4(webm_data, output_path):
    """Convert WebM video to MP4 using pyav."""
    try:
        # Create a temporary file for WebM data
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=False) as temp_webm:
            temp_webm.write(webm_data)
            temp_webm_path = temp_webm.name
            logger.debug(f"Saved raw video WebM to {temp_webm_path}, size: {os.path.getsize(temp_webm_path)} bytes")

        # Open input WebM
        input_container = av.open(temp_webm_path)
        input_video_stream = next((s for s in input_container.streams if s.type == 'video'), None)
        input_audio_stream = next((s for s in input_container.streams if s.type == 'audio'), None)

        if not input_video_stream:
            logger.error("No video stream found in WebM")
            input_container.close()
            os.remove(temp_webm_path)
            return False

        # Open output MP4
        output_container = av.open(output_path, mode='w', format='mp4')
        output_video_stream = output_container.add_stream('h264', rate=30)
        output_video_stream.width = input_video_stream.width or 640
        output_video_stream.height = input_video_stream.height or 480
        output_video_stream.bit_rate = 500000
        output_video_stream.pix_fmt = 'yuv420p'

        output_audio_stream = None
        if input_audio_stream:
            output_audio_stream = output_container.add_stream('aac', rate=input_audio_stream.rate or 44100)
            output_audio_stream.channels = input_audio_stream.channels or 1

        # Transcode video
        for packet in input_container.demux(input_video_stream):
            for frame in packet.decode():
                if frame:
                    new_frame = frame.reformat(format='yuv420p')
                    for new_packet in output_video_stream.encode(new_frame):
                        output_container.mux(new_packet)

        # Transcode audio if present
        if input_audio_stream and output_audio_stream:
            for packet in input_container.demux(input_audio_stream):
                for frame in packet.decode():
                    if frame:
                        for new_packet in output_audio_stream.encode(frame):
                            output_container.mux(new_packet)

        # Flush encoders
        for new_packet in output_video_stream.encode(None):
            output_container.mux(new_packet)
        if output_audio_stream:
            for new_packet in output_audio_stream.encode(None):
                output_container.mux(new_packet)

        output_container.close()
        input_container.close()
        os.remove(temp_webm_path)

        if os.path.getsize(output_path) > 0:
            logger.info(f"Converted WebM to MP4: {output_path} (size: {os.path.getsize(output_path)} bytes)")
            return True
        else:
            logger.warning(f"Converted MP4 file is empty: {output_path}")
            return False
    except Exception as e:
        logger.error(f"Failed to convert WebM to MP4: {str(e)}")
        if 'temp_webm_path' in locals():
            os.remove(temp_webm_path)
        return False

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

        sanitized_name = re.sub(r'[^a-zA-Z0-9]', '_', name).lower().strip('_')
        user_folder = os.path.join(DATA_FOLDER, sanitized_name)
        os.makedirs(user_folder, exist_ok=True, mode=0o755)
        user_audio_folder = os.path.join(user_folder, 'audio')
        user_video_folder = os.path.join(user_folder, 'video')
        os.makedirs(user_audio_folder, exist_ok=True, mode=0o755)
        os.makedirs(user_video_folder, exist_ok=True, mode=0o755)

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
                    "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=AIzaSyAfDkEvsoYOROQAdwxAQ1mjfcjQMA5HM-Q",
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

        # Ensure directories exist
        os.makedirs(audio_folder, exist_ok=True, mode=0o755)
        os.makedirs(video_folder, exist_ok=True, mode=0o755)

        audio_filename = f"{sanitized_username}_{question_idx}_audio.wav"
        video_filename = f"{sanitized_username}_{question_idx}_video.mp4"
        audio_path = os.path.join(audio_folder, audio_filename)
        video_path = os.path.join(video_folder, video_filename)

        # Validate and save audio
        if audio and audio.content_length > 0 and audio.mimetype in ['audio/webm', 'audio/wav', 'application/octet-stream']:
            logger.info(f"Received audio: size={audio.content_length}, mimetype={audio.mimetype}")
            audio_data = audio.read()
            if not convert_webm_to_wav(audio_data, audio_path):
                logger.warning(f"Failed to convert audio for question {question_idx}")
                audio_filename = None
        else:
            logger.warning(f"No valid audio provided for question {question_idx} (content_length: {audio.content_length if audio else 0}, mimetype: {audio.mimetype if audio else 'None'})")
            audio_filename = None

        # Validate and save video
        if video and video.content_length > 0 and video.mimetype in ['video/webm', 'video/mp4', 'application/octet-stream']:
            logger.info(f"Received video: size={video.content_length}, mimetype={video.mimetype}")
            video_data = video.read()
            if not convert_webm_to_mp4(video_data, video_path):
                logger.warning(f"Failed to convert video for question {question_idx}")
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

@app.route('/serve_media/<session_id>/<path:filename>')
def serve_media(session_id, filename):
    try:
        if session_id not in sessions:
            logger.error(f"Session {session_id} not found")
            return jsonify({"error": "Session not found"}), 404

        session_data = sessions[session_id]
        if filename.endswith('.wav'):
            file_path = os.path.join(session_data['audio_folder'], filename)
            mimetype = 'audio/wav'
        elif filename.endswith('.mp4'):
            file_path = os.path.join(session_data['video_folder'], filename)
            mimetype = 'video/mp4'
        else:
            logger.error(f"Invalid file extension: {filename}")
            return jsonify({"error": "Invalid file extension"}), 400

        if os.path.exists(file_path):
            logger.info(f"Serving media file: {file_path}")
            return send_file(file_path, mimetype=mimetype)
        logger.error(f"Media file not found: {file_path}")
        return jsonify({"error": "File not found"}), 404
    except Exception as e:
        logger.error(f"Error serving media file {filename}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

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
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=AIzaSyAfDkEvsoYOROQAdwxAQ1mjfcjQMA5HM-Q",
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
    app.run(debug=True, port=9999)