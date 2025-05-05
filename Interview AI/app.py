from flask import Flask, render_template, request

app = Flask(__name__)

# Sample question and keywords for evaluation
questions = [
    {
        "text": "Explain the difference between a stack and a queue in data structures.",
        "keywords": ["stack", "queue", "LIFO", "FIFO", "last in first out", "first in first out"]
    }
]

# HTML template as a string
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Mock Interview</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            text-align: center;
            background-color: #f0f0f0;
            margin: 0;
            padding: 20px;
        }
        #avatar {
            width: 200px;
            height: auto;
            margin: 20px auto;
        }
        #question, #feedback {
            font-size: 18px;
            margin: 20px 0;
        }
        #userInput {
            width: 80%;
            max-width: 500px;
            padding: 10px;
            font-size: 16px;
            margin: 10px 0;
        }
        #submitBtn {
            padding: 10px 20px;
            font-size: 16px;
            background-color: #007bff;
            color: white;
            border: none;
            cursor: pointer;
        }
        #submitBtn:hover {
            background-color: #0056b3;
        }
        #score {
            font-size: 20px;
            font-weight: bold;
            margin-top: 20px;
        }
    </style>
</head>
<body>
    <h1>AI Mock Interview</h1>
    <img id="avatar" src="https://xai-artifact-1.s3.us-west-2.amazonaws.com/artifact_images/artifact_1725136188589.png" alt="AI Avatar">
    <div id="question">{{ question }}</div>
    <form method="POST" action="/">
        <textarea id="userInput" name="answer" placeholder="Type your answer here..." rows="5"></textarea>
        <br>
        <button id="submitBtn" type="submit">Submit Answer</button>
    </form>
    {% if feedback %}
        <div id="feedback">{{ feedback }}</div>
        <div id="score">Your Score: {{ score }}/100</div>
    {% endif %}
</body>
</html>
'''

@app.route("/", methods=["GET", "POST"])
def interview():
    question = questions[0]["text"]
    feedback = None
    score = None

    if request.method == "POST":
        user_answer = request.form.get("answer", "").lower()
        current_question = questions[0]

        # Simple keyword matching to simulate NLP
        correct_count = sum(1 for keyword in current_question["keywords"] if keyword in user_answer)

        # Simulate confidence score based on answer length (mocking facial recognition/expression analysis)
        confidence_score = 80 if len(user_answer) > 50 else 40

        # Calculate score based on correctness and confidence
        correctness_score = (correct_count / len(current_question["keywords"])) * 100
        score = round((correctness_score * 0.6) + (confidence_score * 0.4))

        # Provide feedback
        feedback = ""
        if correctness_score < 50:
            feedback += "Your answer missed some key concepts. Make sure to mention terms like LIFO for stacks and FIFO for queues. "
        else:
            feedback += "Good job covering the main concepts! "

        if confidence_score < 50:
            feedback += "Try to elaborate more to show confidence. Don't be too brief!"
        else:
            feedback += "You seemed confident in your delivery—nice work!"

    return render_template_string(HTML_TEMPLATE, question=question, feedback=feedback, score=score)

if __name__ == "__main__":
    app.run(debug=True)