from flask import Flask, render_template, request, jsonify
import os
import re
from fluency_predictor import AudioRatingProcessor
from voice_confidence_predictor import VoiceConfidencePredictor
from interview_evaluator import InterviewEvaluator

app = Flask(__name__)

DATA_FOLDER = 'data'
os.makedirs(DATA_FOLDER, exist_ok=True)

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
        audio_processor = AudioRatingProcessor(
            model_path="Fluency and Pronunciation Rating model.keras",
            scaler_path="mfcc_scaler.pkl"
        )

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
        confidence_score = (confidence_counts['Confident'] / total_responses * 10) if total_responses > 0 else 5.0

        # Evaluate Domain Knowledge and Critical Thinking
        domain_knowledge_score = 5.0
        critical_thinking_score = 5.0
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
            domain_knowledge_score = scores.get('domain_knowledge', 5.0)
            critical_thinking_score = scores.get('critical_thinking', 5.0)
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
            'domain': 'N/A',  # Domain not provided in this context
            'engineering': 'N/A'  # Engineering field not provided
        }

        return render_template('evaluation.html', results=evaluation_results)

    return render_template('eval_index.html')

if __name__ == '__main__':
    app.run(debug=True, port=9394)