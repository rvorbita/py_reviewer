import os
import csv
from flask import Flask, render_template, request, jsonify, session

app = Flask(__name__)
# A secret key is required for session management in Flask
# In a production environment, use a strong, randomly generated key from environment variables.
app.secret_key = os.urandom(24)

# Load quiz questions from CSV
def read_quiz_csv(filepath):
    with open(filepath, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        quiz_questions = []
        for row in reader:
            options = []
            for i in range(1, 5): # Assuming max 4 options
                option_key = f"option_{i}"
                if row.get(option_key):
                    options.append(row[option_key])

            question_data = {
                "question": row["question"],
                "code": row["code"] if row["code"] else None,
                "options": options,
                "answer": row["answer"]
            }
            quiz_questions.append(question_data)
    return quiz_questions

quiz_questions = read_quiz_csv('quiz_questions.csv')


# Route Configuration

@app.route('/')
def index():
    """Renders the main quiz page."""
    # Initialize or reset session variables for a new quiz attempt
    session['current_question_index'] = 0
    session['user_answers'] = [None] * len(quiz_questions)
    session['score'] = 0 # Initialize score here
    return render_template('index.html')

@app.route('/get_question', methods=['GET'])
def get_question():
    """
    Returns the current question data based on the session's
    current_question_index.
    """
    index = session.get('current_question_index', 0)
    if 0 <= index < len(quiz_questions):
        question_data = quiz_questions[index]
        return jsonify({
            'question_number': index + 1,
            'total_questions': len(quiz_questions),
            'question': question_data['question'],
            'code': question_data['code'],
            'options': question_data['options'],
            'user_answer': session['user_answers'][index]
        })
    return jsonify({'error': 'No more questions or invalid index'}), 404

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    """
    Receives the user's selected answer, stores it in the session,
    updates the score, and returns feedback.
    """
    data = request.json
    selected_option = data.get('selected_option')
    question_index = data.get('question_index')

    if not isinstance(question_index, int) or not (0 <= question_index < len(quiz_questions)):
        return jsonify({'error': 'Invalid question index'}), 400

    current_question = quiz_questions[question_index]
    correct_answer = current_question['answer']
    is_correct = (selected_option == correct_answer)

    # Check if this question has been answered before in this session
    # We only want to award/deduct points once per question.
    previous_answer = session['user_answers'][question_index]

    # Update user's answer in the session
    session['user_answers'][question_index] = selected_option

    # Update score
    # Get current score, default to 0 if not set
    current_score = session.get('score', 0)

    if is_correct and previous_answer != selected_option: # Correct answer, and it's a new correct answer or changed from incorrect
        if previous_answer != correct_answer: # Only increment if it was previously incorrect or None
            current_score += 1
    elif not is_correct and previous_answer == correct_answer: # Changed from correct to incorrect
        current_score -= 1

    session['score'] = current_score # Update the session score

    feedback = {
        'is_correct': is_correct,
        'correct_answer': correct_answer
    }
    return jsonify(feedback)

@app.route('/navigate_question', methods=['POST'])
def navigate_question():
    """
    Updates the current_question_index in the session based on
    'next' or 'prev' direction.
    """
    data = request.json
    direction = data.get('direction')
    current_index = session.get('current_question_index', 0)

    if direction == 'next':
        if current_index < len(quiz_questions) - 1:
            session['current_question_index'] = current_index + 1
    elif direction == 'prev':
        if current_index > 0:
            session['current_question_index'] = current_index - 1
    else:
        return jsonify({'error': 'Invalid navigation direction'}), 400

    return jsonify({'success': True, 'new_index': session['current_question_index']})

@app.route('/get_final_score', methods=['GET'])
def get_final_score():
    """
    Returns the final score from the session, which should be updated
    incrementally by submit_answer.
    """
    # The score should already be accurate from submit_answer calls.
    # No need to recalculate here unless you want to ensure robustness.
    final_score = session.get('score', 0)

    return jsonify({
        'score': final_score,
        'total_questions': len(quiz_questions)
    })

# Run the Flask application
if __name__ == '__main__':
    app.run(debug=True)