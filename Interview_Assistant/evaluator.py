from flask import Flask, render_template, request, jsonify, make_response
import os
import re
from fluency_predictor import AudioRatingProcessor
from voice_confidence_predictor import VoiceConfidencePredictor
from interview_evaluator import InterviewEvaluator
import random

app = Flask(__name__)

DATA_FOLDER = 'data'
os.makedirs(DATA_FOLDER, exist_ok=True)

results_storage = {}

feedback_sets = {
    "communication_skills": {
        "low": [
            {"feedback": "Consider practicing active listening to better engage with others.", "suggestion": "Join a public speaking club like Toastmasters to improve your listening and speaking skills."},
            {"feedback": "Work on speaking more clearly and at a steady pace to improve clarity.", "suggestion": "Record yourself speaking and review the playback to identify areas for improvement."},
            {"feedback": "Try to reduce filler words like 'um' or 'uh' to sound more confident.", "suggestion": "Pause and breathe instead of using filler words during conversations."},
            {"feedback": "Focus on maintaining eye contact to build better rapport.", "suggestion": "Practice eye contact with a friend or in front of a mirror to feel more comfortable."},
            {"feedback": "Practice structuring your thoughts before speaking to avoid rambling.", "suggestion": "Use a notepad to outline your thoughts before responding in discussions."}
        ],
        "medium": [
            {"feedback": "You're doing well, but try to be more concise in your explanations.", "suggestion": "Practice summarizing your thoughts in 1-2 sentences before elaborating."},
            {"feedback": "Incorporate more examples in your responses to make them relatable.", "suggestion": "Prepare a few relevant anecdotes or examples in advance for common topics."},
            {"feedback": "Work on varying your tone to keep the listener engaged.", "suggestion": "Listen to engaging speakers and mimic their tone variations in your practice."},
            {"feedback": "Consider asking more questions to show interest and understanding.", "suggestion": "Prepare a list of open-ended questions to use in conversations."},
            {"feedback": "Try to summarize key points at the end to reinforce your message.", "suggestion": "Practice closing statements that recap your main points effectively."}
        ],
        "high": [
            {"feedback": "Great job! Your clarity and engagement are impressive.", "suggestion": "Continue honing your skills by mentoring others in communication."},
            {"feedback": "You articulate ideas effectively; keep using real-world examples.", "suggestion": "Explore storytelling techniques to make your examples even more compelling."},
            {"feedback": "Your tone and pace are excellent, making conversations engaging.", "suggestion": "Consider leading discussions or presentations to further showcase your skills."},
            {"feedback": "You connect well with others; continue building on this strength.", "suggestion": "Engage in networking events to expand your influence and connections."},
            {"feedback": "Your communication is strong; keep refining your storytelling skills.", "suggestion": "Read books on storytelling to enhance your narrative delivery."}
        ]
    },
    "confidence": {
        "low": [
            {"feedback": "Try to stand or sit up straight to project more confidence.", "suggestion": "Practice good posture daily by setting reminders to check your stance."},
            {"feedback": "Practice positive self-talk to boost your self-assurance.", "suggestion": "Write down affirmations and repeat them each morning to build confidence."},
            {"feedback": "Speak with a louder voice to convey more certainty in your ideas.", "suggestion": "Practice projecting your voice in a quiet room to get comfortable with volume."},
            {"feedback": "Prepare thoroughly to feel more secure in your responses.", "suggestion": "Create a checklist of topics to review before interviews or discussions."},
            {"feedback": "Take deep breaths before speaking to reduce nervousness.", "suggestion": "Learn breathing exercises like the 4-7-8 technique to calm your nerves."}
        ],
        "medium": [
            {"feedback": "You're showing good confidence; try to maintain it under pressure.", "suggestion": "Simulate high-pressure scenarios in practice to build resilience."},
            {"feedback": "Work on reducing hesitations to appear more self-assured.", "suggestion": "Slow down your speech to give yourself time to think and respond."},
            {"feedback": "Incorporate more assertive language to strengthen your presence.", "suggestion": "Practice using phrases like 'I believe' or 'I recommend' in discussions."},
            {"feedback": "Try to smile more to convey warmth and confidence.", "suggestion": "Practice smiling in front of a mirror to make it feel natural."},
            {"feedback": "Keep practicing; you're on the right track to building confidence.", "suggestion": "Set small confidence goals, like speaking up once in every meeting."}
        ],
        "high": [
            {"feedback": "Excellent! Your confidence shines through in your responses.", "suggestion": "Consider taking on leadership roles to further leverage your confidence."},
            {"feedback": "You project assurance effectively; keep up the great work.", "suggestion": "Share your confidence-building tips with peers to help them grow."},
            {"feedback": "Your poise is impressive; continue to lead with confidence.", "suggestion": "Volunteer for high-visibility projects to showcase your skills."},
            {"feedback": "You handle pressure well; maintain this strong presence.", "suggestion": "Explore opportunities to speak at events to expand your influence."},
            {"feedback": "Great job! Your confidence makes a strong positive impact.", "suggestion": "Continue to challenge yourself with new and diverse experiences."}
        ]
    },
    "domain_knowledge": {
        "low": [
            {"feedback": "Spend more time reviewing core concepts in your field.", "suggestion": "Dedicate 30 minutes daily to reading foundational texts or resources."},
            {"feedback": "Consider taking online courses to deepen your understanding.", "suggestion": "Enroll in a beginner course on platforms like Coursera or Udemy."},
            {"feedback": "Read industry blogs or articles to stay updated on trends.", "suggestion": "Subscribe to a few reputable industry newsletters for regular updates."},
            {"feedback": "Practice applying concepts to real-world scenarios for better retention.", "suggestion": "Work on small projects or case studies to apply what you learn."},
            {"feedback": "Seek mentorship to gain insights and improve your knowledge.", "suggestion": "Reach out to a senior colleague or join a professional community."}
        ],
        "medium": [
            {"feedback": "You have a good base; try to dive deeper into advanced topics.", "suggestion": "Pick one advanced topic each month to study in depth."},
            {"feedback": "Focus on staying updated with the latest industry developments.", "suggestion": "Set a goal to read one industry article or paper each week."},
            {"feedback": "Work on connecting concepts to practical applications.", "suggestion": "Participate in hackathons or projects to apply your knowledge."},
            {"feedback": "Consider discussing topics with peers to gain new perspectives.", "suggestion": "Join a study group or online forum to exchange ideas."},
            {"feedback": "You're on the right path; keep exploring to enhance your expertise.", "suggestion": "Attend webinars or workshops to broaden your knowledge."}
        ],
        "high": [
            {"feedback": "Impressive knowledge! You demonstrate strong expertise.", "suggestion": "Consider teaching or mentoring others to solidify your understanding."},
            {"feedback": "Your understanding of the field is excellent; keep it up.", "suggestion": "Write a blog post or article to share your insights with the community."},
            {"feedback": "You apply concepts effectively; continue to lead with your knowledge.", "suggestion": "Lead a project or initiative to apply your expertise in a new way."},
            {"feedback": "Great job! Your depth of knowledge is a key strength.", "suggestion": "Explore adjacent fields to expand your expertise even further."},
            {"feedback": "You excel in this area; keep sharing your insights with others.", "suggestion": "Present at a conference or webinar to showcase your knowledge."}
        ]
    },
    "critical_thinking": {
        "low": [
            {"feedback": "Practice breaking down problems into smaller parts to analyze them.", "suggestion": "Use a problem-solving framework like the 5 Whys to start."},
            {"feedback": "Try to question assumptions to improve your reasoning skills.", "suggestion": "Write down assumptions for each problem and challenge them."},
            {"feedback": "Work on identifying patterns or trends in data to draw conclusions.", "suggestion": "Practice with simple datasets or puzzles to spot patterns."},
            {"feedback": "Consider brainstorming multiple solutions before deciding on one.", "suggestion": "Set a timer for 5 minutes to brainstorm ideas for each problem."},
            {"feedback": "Focus on evaluating the pros and cons of decisions to think critically.", "suggestion": "Create a pros and cons list for decisions to practice this skill."}
        ],
        "medium": [
            {"feedback": "You're showing good reasoning; try to explore alternative perspectives.", "suggestion": "Role-play different viewpoints to understand other perspectives."},
            {"feedback": "Work on asking more 'why' and 'how' questions to deepen analysis.", "suggestion": "Keep a journal of questions you ask during problem-solving."},
            {"feedback": "Focus on improving your problem-solving speed with practice.", "suggestion": "Solve timed logic puzzles or brain teasers regularly."},
            {"feedback": "Consider using frameworks to structure your thought process.", "suggestion": "Learn frameworks like SWOT analysis to organize your thinking."},
            {"feedback": "You're doing well; keep refining your analytical skills.", "suggestion": "Take on more complex problems to challenge your thinking."}
        ],
        "high": [
            {"feedback": "Excellent! Your critical thinking skills are top-notch.", "suggestion": "Tackle interdisciplinary problems to further hone your skills."},
            {"feedback": "You analyze problems effectively; keep up the great work.", "suggestion": "Share your problem-solving approach with others to help them learn."},
            {"feedback": "Your reasoning is strong; continue to tackle complex challenges.", "suggestion": "Engage in strategic games like chess to keep your skills sharp."},
            {"feedback": "Great job! Your ability to think critically is impressive.", "suggestion": "Consider leading brainstorming sessions to inspire others."},
            {"feedback": "You excel in this area; keep applying your skills to new scenarios.", "suggestion": "Explore case studies in different fields to broaden your approach."}
        ]
    }
}

# Function to determine the level and select random feedback and suggestion
def get_feedback_and_suggestion(score, parameter):
    if score <= 3.3:
        level = "low"
    elif score <= 6.6:
        level = "medium"
    else:
        level = "high"
    feedback_list = feedback_sets[parameter][level]
    selected = random.choice(feedback_list)
    return selected["feedback"], selected["suggestion"]

import requests
import logging

logger = logging.getLogger(__name__)

def analyze_skills_with_gemini(name, role, transcript_content):
    skills_analysis = {}
    try:
        prompt = (
            f"Analyze the following interview transcript for a candidate named {name} applying for the role of {role}. "
            f"Provide a detailed analysis in the following sections:\n"
            f"1. *Current Skills Demonstrated*: List the skills the candidate demonstrated based on their answers.\n"
            f"2. *Knowledge Level for the Role*: Evaluate the candidate's knowledge level for the role (e.g., beginner, intermediate, advanced) and explain why.\n"
            f"3. *Skills to Improve for the Role*: Suggest specific skills the candidate should improve to excel in the role, with actionable advice.\n"
            f"4. *General Transcript Analysis*: Summarize the candidate's strengths and weaknesses based on the transcript, including communication style, clarity, and technical depth.\n"
            f"5. *Suggested Courses*: Suggest some courses that user can watch to grain knowledge in those missing skills.\n"
            f"Format the response with clear section headers (e.g., ## Current Skills Demonstrated) and concise paragraphs.\n\n"
            f"Transcript:\n{transcript_content}"
        )
        api_key = "AIzaSyC5NmF0ckTVDTv9RVgpC6SuKnpnWQ0IFyw"
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        if 'candidates' in result and result['candidates']:
            gemini_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
            sections = {
                'current_skills': '',
                'knowledge_level': '',
                'skills_to_improve': '',
                'general_analysis': '',
                'suggested_courses': ''
            }
            current_section = None
            for line in gemini_text.split('\n'):
                line = line.strip().replace('*','')
                if line.startswith('## Current Skills Demonstrated'):
                    current_section = 'current_skills'
                elif line.startswith('## Knowledge Level for the Role'):
                    current_section = 'knowledge_level'
                elif line.startswith('## Skills to Improve for the Role'):
                    current_section = 'skills_to_improve'
                elif line.startswith('## General Transcript Analysis'):
                    current_section = 'general_analysis'
                elif line.startswith('## Suggested Courses'):
                    current_section = 'suggested_courses'
                elif current_section and line:
                    sections[current_section] += line + '\n'
            skills_analysis = {k: v.strip() for k, v in sections.items()}
        else:
            logger.error("Gemini API returned no candidates")
            skills_analysis = {
                'current_skills': 'Unable to analyze skills due to API error.',
                'knowledge_level': 'Unable to assess knowledge level due to API error.',
                'skills_to_improve': 'Unable to suggest improvements due to API error.',
                'general_analysis': 'Unable to analyze transcript due to API error.',
                'suggested_courses': 'Unable to analyze transcript due to API error.'
            }
    except Exception as e:
        logger.error(f"Gemini API request failed: {str(e)}")
        skills_analysis = {
            'current_skills': 'Error analyzing skills.',
            'knowledge_level': 'Error assessing knowledge level.',
            'skills_to_improve': 'Error suggesting improvements.',
            'general_analysis': 'Error analyzing transcript.',
            'suggested_courses': 'Error analyzing transcript.'
        }

    return skills_analysis


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form.get('name')
        if not name:
            return jsonify({"error": "Name is required"}), 400

        sanitized_name = re.sub(r'[^a-zA-Z0-9]', '_', name)
        user_folder = os.path.join(DATA_FOLDER, sanitized_name)
        audio_folder = os.path.join(user_folder, 'audio')
        transcript_path = os.path.join(user_folder, 'transcript.txt')

        if not os.path.exists(audio_folder) or not os.path.exists(transcript_path):
            return jsonify({"error": "Interview data not found for this user"}), 404

        # Initialize evaluators
        audio_processor = AudioRatingProcessor()

        # Evaluate Communication Skills
        communication_scores = []
        audio_files = [f for f in os.listdir(audio_folder) if f.endswith('.wav')]
        for audio_file in audio_files:
            audio_path = os.path.join(audio_folder, audio_file)
            try:
                result = audio_processor.predict_audio_rating(audio_path)
                if isinstance(result, dict):
                    avg_score = (result['Pronunciation Score'] + result['Fluency Score']) / 2
                    communication_scores.append(avg_score)
            except Exception as e:
                app.logger.error(f"Error processing audio {audio_file}: {str(e)}")
                continue

        communication_score = sum(communication_scores) / len(communication_scores) if communication_scores else 5.0

        # Evaluate Confidence
        confidence_counts = {'Confident': 0, 'Not Confident': 0}
        for audio_file in audio_files:
            audio_path = os.path.join(audio_folder, audio_file)
            try:
                predictor = VoiceConfidencePredictor(audio_path)
                result = predictor.predict()
                if result["label"] is not None:
                    label = 'Confident' if result['label'] == 'Confident' else 'Not Confident'
                    confidence_counts[label] += 1
            except Exception as e:
                app.logger.error(f"Error predicting confidence for {audio_file}: {str(e)}")
                continue

        total_responses = sum(confidence_counts.values())
        confidence_score = (confidence_counts['Confident'] / total_responses * 10) if total_responses > 0 else 2.0

        # Evaluate Domain Knowledge and Critical Thinking
        domain_knowledge_score = 2.0
        critical_thinking_score = 2.0
        role = "Software Engineer"  # Default role
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript_content = f.read()
            # Attempt to extract role from transcript (assuming it may contain "Role: <role>")
            role_match = re.search(r'Role: (.+?)\n', transcript_content)
            if role_match:
                role = role_match.group(1).strip()
            evaluator = InterviewEvaluator(role, transcript_content)
            scores = evaluator.eval()
            domain_knowledge_score = scores.get('domain_knowledge', 2.0)
            critical_thinking_score = scores.get('critical_thinking', 2.0)
        except Exception as e:
            app.logger.error(f"Error evaluating transcript: {str(e)}")

        # Prepare evaluation results
        evaluation_results = {
            'communication_skills': round(communication_score, 2),
            'confidence': round(confidence_score, 2),
            'domain_knowledge': round(domain_knowledge_score, 2),
            'critical_thinking': round(critical_thinking_score, 2),
            'name': name,
            'role': role,
        }
        evaluation_results['communication_feedback'], evaluation_results['communication_suggestion'] = get_feedback_and_suggestion(evaluation_results['communication_skills'], 'communication_skills')
        evaluation_results['confidence_feedback'], evaluation_results['confidence_suggestion'] = get_feedback_and_suggestion(evaluation_results['confidence'], 'confidence')
        evaluation_results['domain_knowledge_feedback'], evaluation_results['domain_knowledge_suggestion'] = get_feedback_and_suggestion(evaluation_results['domain_knowledge'], 'domain_knowledge')
        evaluation_results['critical_thinking_feedback'], evaluation_results['critical_thinking_suggestion'] = get_feedback_and_suggestion(evaluation_results['critical_thinking'], 'critical_thinking')
        
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_content = f.read()
        
        feedbaack = analyze_skills_with_gemini(name, role, transcript_content)
        
        return render_template('evaluation.html', results=evaluation_results, feedback = feedbaack)

    return render_template('eval_index.html')

if __name__ == '__main__':
    app.run(debug=False, port=9394)