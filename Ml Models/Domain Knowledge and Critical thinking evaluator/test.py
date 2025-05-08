from interview_evaluator import InterviewEvaluator


job_role = "Software Engineer (Backend)"
transcript = """
Q1: What is a REST API?
A1: It's an API that uses HTTP methods like GET and POST. It's stateless. We use it for web services.

Q2: How would you debug a failing database query in production?
A2: First, I'd check application logs for the exact error message and context. Then, I might try to reproduce the issue in a staging environment if possible. I'd examine the query plan using EXPLAIN ANALYZE to look for bottlenecks. Depending on the error, I might check database server logs, resource utilization (CPU/memory/IO), or look for recent schema changes or data migrations that could be related. Running the query manually with specific parameters identified from logs helps isolate the problem.
"""

evaluator = InterviewEvaluator(job_role, transcript)
scores = evaluator.eval()
print(scores)
