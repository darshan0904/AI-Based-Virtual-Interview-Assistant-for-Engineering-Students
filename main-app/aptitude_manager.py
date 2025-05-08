import csv
import random
import json
import sys
import google.generativeai as genai

class AptitudeTestManager:
    def __init__(self, general_csv='clean_general_aptitude_dataset.csv', logical_csv='logical_reasoning_questions.csv', api_key=None):
        self.general_csv = general_csv
        self.logical_csv = logical_csv
        self.supported_domains = ['CSE', 'MECHANICAL', 'CIVIL', 'ECE', 'ELECTRICAL', 
                                 'CHEMICAL', 'AEROSPACE', 'BIOTECHNOLOGY', 'INDUSTRIAL', 'ENVIRONMENTAL']
        self.fallback_verbal_questions = [
            {"question": "What is the synonym of 'big'?", "options": ["Small", "Large", "Tiny", "Short"], "answer": "B", "topic": "Verbal Communication"},
            {"question": "Which word is misspelled?", "options": ["Receive", "Belive", "Achieve", "Deceive"], "answer": "B", "topic": "Verbal Communication"},
            {"question": "What is the antonym of 'happy'?", "options": ["Sad", "Joyful", "Excited", "Pleased"], "answer": "A", "topic": "Verbal Communication"},
            {"question": "Complete the analogy: Big is to small as tall is to ?", "options": ["High", "Short", "Long", "Wide"], "answer": "B", "topic": "Verbal Communication"},
            {"question": "Choose the correct sentence:", "options": ["He go to school.", "He goes to school.", "He going to school.", "He gone to school."], "answer": "B", "topic": "Verbal Communication"}
        ]
        self.fallback_domain_questions = {
            'CSE': [
                {"question": "What is the time complexity of binary search?", "options": ["O(n)", "O(log n)", "O(n log n)", "O(1)"], "answer": "B", "topic": "CSE"},
                {"question": "Which data structure uses LIFO?", "options": ["Queue", "Stack", "Array", "Linked List"], "answer": "B", "topic": "CSE"},
                {"question": "What does CPU stand for?", "options": ["Central Processing Unit", "Computer Power Unit", "Control Process Utility", "Central Power Utility"], "answer": "A", "topic": "CSE"},
                {"question": "What is the purpose of an operating system?", "options": ["Gaming", "Manage hardware", "Word processing", "Web browsing"], "answer": "B", "topic": "CSE"},
                {"question": "Which is a high-level programming language?", "options": ["Assembly", "Machine Code", "Python", "Binary"], "answer": "C", "topic": "CSE"}
            ],
            'MECHANICAL': [
                {"question": "What is the first law of thermodynamics?", "options": ["Energy conservation", "Entropy increase", "Heat transfer", "Work done"], "answer": "A", "topic": "MECHANICAL"},
                {"question": "What is the unit of force?", "options": ["Newton", "Joule", "Watt", "Pascal"], "answer": "A", "topic": "MECHANICAL"},
                {"question": "What is a lever?", "options": ["Simple machine", "Complex engine", "Electrical device", "Hydraulic pump"], "answer": "A", "topic": "MECHANICAL"},
                {"question": "What does RPM stand for?", "options": ["Rotations Per Minute", "Revolutions Per Meter", "Radians Per Minute", "Rate Per Motion"], "answer": "A", "topic": "MECHANICAL"},
                {"question": "What is shear stress?", "options": ["Force per unit area", "Thermal expansion", "Volume change", "Pressure drop"], "answer": "A", "topic": "MECHANICAL"}
            ],
            'CIVIL': [
                {"question": "What is the primary material in concrete?", "options": ["Cement", "Steel", "Wood", "Glass"], "answer": "A", "topic": "CIVIL"},
                {"question": "What is a beam?", "options": ["Structural element", "Decorative piece", "Electrical conduit", "Plumbing pipe"], "answer": "A", "topic": "CIVIL"},
                {"question": "What does RCC stand for?", "options": ["Reinforced Concrete Cement", "Rapid Construction Code", "Residential Civil Contract", "Road Construction Crew"], "answer": "A", "topic": "CIVIL"},
                {"question": "What is the purpose of a foundation?", "options": ["Support structure", "Aesthetic design", "Insulation", "Ventilation"], "answer": "A", "topic": "CIVIL"},
                {"question": "What is a retaining wall?", "options": ["Soil support", "Decorative barrier", "Roof structure", "Window frame"], "answer": "A", "topic": "CIVIL"}
            ],
            'ECE': [
                {"question": "What does LED stand for?", "options": ["Light Emitting Diode", "Low Energy Device", "Linear Electric Diode", "Light Energy Detector"], "answer": "A", "topic": "ECE"},
                {"question": "What is an amplifier used for?", "options": ["Increase signal strength", "Reduce noise", "Store energy", "Filter light"], "answer": "A", "topic": "ECE"},
                {"question": "What is the unit of resistance?", "options": ["Ohm", "Volt", "Ampere", "Watt"], "answer": "A", "topic": "ECE"},
                {"question": "What is a transistor?", "options": ["Switching device", "Power supply", "Cooling fan", "Display unit"], "answer": "A", "topic": "ECE"},
                {"question": "What does AC stand for?", "options": ["Alternating Current", "Active Circuit", "Analog Control", "Amplified Current"], "answer": "A", "topic": "ECE"}
            ],
            'ELECTRICAL': [
                {"question": "What is Ohm's Law?", "options": ["V=IR", "P=VI", "E=mc²", "F=ma"], "answer": "A", "topic": "ELECTRICAL"},
                {"question": "What is a conductor?", "options": ["Material that allows current", "Insulating material", "Magnetic field", "Thermal barrier"], "answer": "A", "topic": "ELECTRICAL"},
                {"question": "What is the unit of power?", "options": ["Watt", "Joule", "Volt", "Ampere"], "answer": "A", "topic": "ELECTRICAL"},
                {"question": "What is a fuse?", "options": ["Safety device", "Power generator", "Signal amplifier", "Light source"], "answer": "A", "topic": "ELECTRICAL"},
                {"question": "What does DC stand for?", "options": ["Direct Current", "Dynamic Circuit", "Digital Control", "Distributed Current"], "answer": "A", "topic": "ELECTRICAL"}
            ],
            'CHEMICAL': [
                {"question": "What is H2O?", "options": ["Water", "Hydrogen gas", "Oxygen gas", "Carbon dioxide"], "answer": "A", "topic": "CHEMICAL"},
                {"question": "What is a catalyst?", "options": ["Speeds up reaction", "Slows down reaction", "Stops reaction", "Heats solution"], "answer": "A", "topic": "CHEMICAL"},
                {"question": "What is pH a measure of?", "options": ["Acidity", "Temperature", "Pressure", "Density"], "answer": "A", "topic": "CHEMICAL"},
                {"question": "What is an element?", "options": ["Pure substance", "Mixture", "Compound", "Solution"], "answer": "A", "topic": "CHEMICAL"},
                {"question": "What gas do plants use?", "options": ["Carbon dioxide", "Oxygen", "Nitrogen", "Helium"], "answer": "A", "topic": "CHEMICAL"}
            ],
            'AEROSPACE': [
                {"question": "What is lift in aviation?", "options": ["Upward force", "Downward force", "Side thrust", "Drag"], "answer": "A", "topic": "AEROSPACE"},
                {"question": "What powers most aircraft?", "options": ["Jet engines", "Solar panels", "Wind turbines", "Electric motors"], "answer": "A", "topic": "AEROSPACE"},
                {"question": "What is the speed of sound called?", "options": ["Mach", "Warp", "Sonic", "Pulse"], "answer": "A", "topic": "AEROSPACE"},
                {"question": "What is an airfoil?", "options": ["Wing shape", "Engine type", "Fuel tank", "Landing gear"], "answer": "A", "topic": "AEROSPACE"},
                {"question": "What does NASA stand for?", "options": ["National Aeronautics and Space Administration", "North American Science Agency", "New Aerospace Standards Authority", "National Aviation Systems Alliance"], "answer": "A", "topic": "AEROSPACE"}
            ],
            'BIOTECHNOLOGY': [
                {"question": "What is DNA?", "options": ["Genetic material", "Protein", "Enzyme", "Hormone"], "answer": "A", "topic": "BIOTECHNOLOGY"},
                {"question": "What is cloning?", "options": ["Copying organisms", "Editing genes", "Synthesizing proteins", "Growing plants"], "answer": "A", "topic": "BIOTECHNOLOGY"},
                {"question": "What is a gene?", "options": ["DNA segment", "Cell organelle", "Blood type", "Virus"], "answer": "A", "topic": "BIOTECHNOLOGY"},
                {"question": "What is PCR used for?", "options": ["Amplify DNA", "Sequence proteins", "Grow cells", "Measure pH"], "answer": "A", "topic": "BIOTECHNOLOGY"},
                {"question": "What is an enzyme?", "options": ["Biological catalyst", "Structural protein", "Energy source", "Transport molecule"], "answer": "A", "topic": "BIOTECHNOLOGY"}
            ],
            'INDUSTRIAL': [
                {"question": "What is lean manufacturing?", "options": ["Waste reduction", "Mass production", "High inventory", "Slow processing"], "answer": "A", "topic": "INDUSTRIAL"},
                {"question": "What is a supply chain?", "options": ["Product flow", "Employee roster", "Machine maintenance", "Financial audit"], "answer": "A", "topic": "INDUSTRIAL"},
                {"question": "What is quality control?", "options": ["Product standards", "Marketing strategy", "Cost reduction", "Staff training"], "answer": "A", "topic": "INDUSTRIAL"},
                {"question": "What is automation?", "options": ["Machine operation", "Manual labor", "Design phase", "Sales pitch"], "answer": "A", "topic": "INDUSTRIAL"},
                {"question": "What is an assembly line?", "options": ["Production sequence", "Storage unit", "Shipping dock", "Office layout"], "answer": "A", "topic": "INDUSTRIAL"}
            ],
            'ENVIRONMENTAL': [
                {"question": "What is renewable energy?", "options": ["Sustainable source", "Fossil fuel", "Nuclear power", "Coal energy"], "answer": "A", "topic": "ENVIRONMENTAL"},
                {"question": "What is global warming?", "options": ["Temperature rise", "Ozone depletion", "Soil erosion", "Water scarcity"], "answer": "A", "topic": "ENVIRONMENTAL"},
                {"question": "What is recycling?", "options": ["Reusing materials", "Burning waste", "Landfilling", "Mining"], "answer": "A", "topic": "ENVIRONMENTAL"},
                {"question": "What is gas causes the greenhouse effect?", "options": ["Carbon dioxide", "Oxygen", "Nitrogen", "Helium"], "answer": "A", "topic": "ENVIRONMENTAL"},
                {"question": "What is biodiversity?", "options": ["Species variety", "Air purity", "Water depth", "Soil type"], "answer": "A", "topic": "ENVIRONMENTAL"}
            ]
        }
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
            print(f"Failed to initialize Gemini API: {e}. Using fallbacks only.")
            self.model = None

    def load_questions_from_csv(self, filename, topic):
        questions = []
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file, delimiter=';')
                for row in reader:
                    options = [row['Option A'], row['Option B'], row['Option C'], row['Option D']]
                    question = {
                        'question': row['Question'],
                        'options': options,
                        'answer': row['Answer'],
                        'topic': topic
                    }
                    if self.is_valid_question(question):
                        questions.append(question)
        except FileNotFoundError:
            print(f"Error: File {filename} not found.")
            return []
        return questions

    def is_valid_option(self, option):
        if not isinstance(option, str) or option.strip() == '':
            return False
        invalid_options = ['A', 'B', 'C', 'D', 'a', 'b', 'c', 'd']
        return option.strip().upper() not in invalid_options

    def is_valid_question(self, question):
        if not all(key in question for key in ['question', 'options', 'answer']):
            return False
        if not isinstance(question['options'], list) or len(question['options']) != 4:
            return False
        if question['answer'] not in ['A', 'B', 'C', 'D']:
            return False
        for opt in question['options']:
            if not self.is_valid_option(opt):
                return False
        return True

    def generate_verbal_questions(self, num_questions=5):
        prompt = f"""
        Generate {num_questions} multiple-choice questions with 4 options each for Verbal Communication aptitude test.
        Questions should test vocabulary, grammar, analogies, sentence correction, or comprehension skills.
        Each question must:
        - Be clear and concise.
        - Provide four distinct, meaningful options (not placeholders like 'A', 'B', 'C', 'D').
        - Label options as A, B, C, D in the answer field.
        - Include the correct answer as 'A', 'B', 'C', or 'D'.
        Return the result as a JSON string containing a list of {num_questions} dictionaries with keys: 'question' (string), 'options' (list of 4 strings), 'answer' (string: 'A', 'B', 'C', or 'D').
        Example:
        [
            {{
                "question": "What is the synonym of 'big'?",
                "options": ["Small", "Large", "Tiny", "Short"],
                "answer": "B"
            }}
        ]
        """
        if not self.model:
            print("No Gemini model available. Using fallback verbal questions.")
            return random.sample(self.fallback_verbal_questions, min(num_questions, len(self.fallback_verbal_questions)))
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip().replace("```json", "").replace("```", "")
            questions = json.loads(text)
            parsed_questions = []
            for q in questions:
                if self.is_valid_question(q):
                    parsed_questions.append({
                        'question': q['question'],
                        'options': q['options'],
                        'answer': q['answer'],
                        'topic': 'Verbal Communication'
                    })
            if len(parsed_questions) >= num_questions:
                return parsed_questions[:num_questions]
            else:
                print(f"Generated only {len(parsed_questions)} valid verbal questions. Using fallback.")
                shortfall = num_questions - len(parsed_questions)
                fallback_questions = random.sample(self.fallback_verbal_questions, min(shortfall, len(self.fallback_verbal_questions)))
                return parsed_questions + fallback_questions[:shortfall]
        except Exception as e:
            print(f"Failed to generate Verbal Communication questions: {e}. Using fallback.")
            return random.sample(self.fallback_verbal_questions, min(num_questions, len(self.fallback_verbal_questions)))

    def generate_domain_questions(self, domain, num_questions=5):
        is_supported_domain = domain in self.supported_domains
        prompt = f"""
        Generate {num_questions} multiple-choice questions with 4 options each for {domain} engineering aptitude test.
        Each question must:
        - Be relevant to {domain} engineering or the specified field.
        - Have a clear, concise question.
        - Provide four distinct, meaningful options (not placeholders like 'A', 'B', 'C', 'D').
        - Label options as A, B, C, D in the answer field.
        - Include the correct answer as 'A', 'B', 'C', or 'D'.
        Return the result as a JSON string containing a list of {num_questions} dictionaries with keys: 'question' (string), 'options' (list of 4 strings), 'answer' (string: 'A', 'B', 'C', or 'D').
        Example:
        [
            {{
                "question": "What is the time complexity of binary search?",
                "options": ["O(n)", "O(log n)", "O(n log n)", "O(1)"],
                "answer": "B"
            }}
        ]
        """
        if not self.model:
            print(f"No Gemini model available. Using fallback for {domain} questions.")
            if is_supported_domain:
                return random.sample(self.fallback_domain_questions[domain], min(num_questions, len(self.fallback_domain_questions[domain])))
            return []
        try:
            response = self.model.generate_content(prompt)
            text = response.text.strip().replace("```json", "").replace("```", "")
            questions = json.loads(text)
            parsed_questions = []
            for q in questions:
                if self.is_valid_question(q):
                    parsed_questions.append({
                        'question': q['question'],
                        'options': q['options'],
                        'answer': q['answer'],
                        'topic': domain
                    })
            if len(parsed_questions) >= num_questions:
                return parsed_questions[:num_questions]
            else:
                print(f"Generated only {len(parsed_questions)} valid domain questions for {domain}.")
                if is_supported_domain:
                    print("Using fallback questions.")
                    shortfall = num_questions - len(parsed_questions)
                    fallback_questions = random.sample(self.fallback_domain_questions[domain], min(shortfall, len(self.fallback_domain_questions[domain])))
                    return parsed_questions + fallback_questions[:shortfall]
                else:
                    print("No fallback available for unsupported domain. Returning available questions.")
                    return parsed_questions
        except Exception as e:
            print(f"Failed to generate domain-specific questions for {domain}: {e}.")
            if is_supported_domain:
                print("Using fallback questions.")
                return random.sample(self.fallback_domain_questions[domain], min(num_questions, len(self.fallback_domain_questions[domain])))
            else:
                print("No fallback available for unsupported domain. Returning empty list.")
                return []

    def start_test(self, domain, session):
        if not domain:
            return {'error': 'Please select or enter a valid domain (e.g., ISE)'}, 400
        
        session['domain'] = domain
        
        general_questions = self.load_questions_from_csv(self.general_csv, 'General Aptitude')
        logical_questions = self.load_questions_from_csv(self.logical_csv, 'Logical Reasoning')
        
        print(f"Loaded {len(general_questions)} General Aptitude questions")
        print(f"Loaded {len(logical_questions)} Logical Reasoning questions")
        
        general_questions = random.sample(general_questions, 10) if len(general_questions) >= 10 else general_questions
        logical_questions = random.sample(logical_questions, 5) if len(logical_questions) >= 5 else logical_questions
        verbal_questions = self.generate_verbal_questions(5)
        domain_questions = self.generate_domain_questions(domain, 5)
        
        all_questions = general_questions + logical_questions + verbal_questions + domain_questions
        random.shuffle(all_questions)
        
        print(f"Total questions generated: {len(all_questions)}")
        
        session['questions'] = all_questions
        session['user_answers'] = [''] * len(all_questions)
        
        return {'status': 'success', 'questions': all_questions}

    def submit_test(self, answers, session):
        questions = session.get('questions', [])
        domain = session.get('domain', '')
        
        print(f"Received {len(answers)} answers, expected {len(questions)} questions")
        
        if not questions or len(answers) != len(questions):
            print("Invalid submission: question-answer mismatch")
            return {'error': 'Invalid submission'}, 400
        
        scores = {'General Aptitude': 0, 'Logical Reasoning': 0, 'Verbal Communication': 0, domain: 0}
        incorrect_questions = []
        
        for i, (q, ans) in enumerate(zip(questions, answers)):
            if ans and ans in ['A', 'B', 'C', 'D']:
                session['user_answers'][i] = ans
                if ans == q['answer']:
                    scores[q['topic']] += 1
                else:
                    incorrect_questions.append({
                        'question': q['question'],
                        'user_answer': q['options'][ord(ans) - ord('A')] if ans else 'None',
                        'correct_answer': q['options'][ord(q['answer']) - ord('A')],
                        'topic': q['topic']
                    })
            else:
                print(f"Invalid answer for question {i+1}: {ans}")
        
        session['scores'] = scores
        session['incorrect_questions'] = incorrect_questions
        session['total_score'] = sum(scores.values())
        
        print(f"Test scores: {scores}, Total: {session['total_score']}")
        
        return {
            'scores': scores,
            'total_score': session['total_score'],
            'incorrect_questions': incorrect_questions
        }