from flask import Flask, render_template, request
import requests
import json

app = Flask(__name__, template_folder="templates", static_folder="static")

# Function to generate questions using Gemini API
def generate_questions(domain, role):
    # Replace with your Gemini API key
    api_key = "YOUR_GEMINI_API_KEY"  

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {
        "Content-Type": "application/json"
    }
    prompt = f"Generate 2 technical interview questions for a {role} in the {domain} domain. For each question, provide a list of 3-5 keywords that should be present in a good answer. Format the response as a JSON array of objects, each with 'text' (the question) and 'keywords' (a list of keywords)."

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        result = response.json()

        # Extract the generated questions from the response
        generated_text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        questions = json.loads(generated_text)  # Assuming Gemini returns a valid JSON string

        return questions
    except Exception as e:
        # Fallback questions in case the API call fails
        return [
            {
                "text": f"What is the difference between REST and GraphQL APIs? (Generated for {role} in {domain})",
                "keywords": ["rest", "graphql", "query", "endpoint", "schema"]
            },
            {
                "text": f"How do you handle database migrations in a production environment? (Generated for {role} in {domain})",
                "keywords": ["migration", "database", "schema", "rollback", "production"]
            }
        ]

@app.route("/", methods=["GET", "POST"])
def interview():
    feedback = None
    score = None
    current_question = None
    question_index = int(request.form.get("question_index", 0))

    # Get domain and role from form (default to Software Engineering and Backend Developer)
    domain = request.form.get("domain", "Software Engineering")
    role = request.form.get("role", "Backend Developer")

    # Fetch questions using Gemini API
    questions = generate_questions(domain, role)

    if not questions:
        return render_template("index.html", error="No questions available for this domain and role.")

    # Ensure question_index is within bounds
    if question_index >= len(questions):
        question_index = 0

    current_question = questions[question_index]["text"]

    if request.method == "POST" and "answer" in request.form:
        user_answer = request.form.get("answer", "").lower()
        current_q = questions[question_index]

        # Simple keyword matching to simulate NLP
        correct_count = sum(1 for keyword in current_q["keywords"] if keyword in user_answer)

        # Simulate confidence score based on answer length
        confidence_score = 80 if len(user_answer) > 50 else 40

        # Calculate score
        correctness_score = (correct_count / len(current_q["keywords"])) * 100
        score = round((correctness_score * 0.6) + (confidence_score * 0.4))

        # Provide feedback
        feedback = ""
        if correctness_score < 50:
            feedback += f"Your answer missed some key concepts. Make sure to mention terms like {', '.join(current_q['keywords'][:3])}. "
        else:
            feedback += "Good job covering the main concepts! "

        if confidence_score < 50:
            feedback += "Try to elaborate more to show confidence. Don't be too brief!"
        else:
            feedback += "You seemed confident in your delivery—nice work!"

        # Move to the next question
        question_index += 1

    return render_template(
        "index.html",
        question=current_question,
        feedback=feedback,
        score=score,
        question_index=question_index,
        domain=domain,
        role=role
    )

if __name__ == "__main__":
    app.run(debug=True)