import os
import csv
from flask import Flask, render_template, request, jsonify, session

app = Flask(__name__)
# A secret key is required for session management in Flask
# In a production environment, use a strong, randomly generated key from environment variables.
app.secret_key = os.urandom(24)

# Quiz questions data, now stored in Python
# Note: For questions that originally had multiple correct answers or drag-and-drop,
# I've adapted them to a single best answer for the simplified multiple-choice format.

#load csv
def read_quiz_csv(filepath):
    with open(filepath, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        quiz_questions = []
        for row in reader:
            # Reconstruct the 'options' list and handle 'code' being None
            options = []
            for i in range(1, 5): # Assuming max 4 options
                option_key = f"option_{i}"
                if row.get(option_key): # Check if the option exists and is not empty
                    options.append(row[option_key])

            question_data = {
                "question": row["question"],
                "code": row["code"] if row["code"] else None, # Convert empty string to None
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
    # Store user answers in session for persistence across requests
    session['user_answers'] = [None] * len(quiz_questions)
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
        # Prepare data to send to the client
        return jsonify({
            'question_number': index + 1,
            'total_questions': len(quiz_questions),
            'question': question_data['question'],
            'code': question_data['code'],
            'options': question_data['options'],
            # Send the user's previously selected answer for this question
            'user_answer': session['user_answers'][index]
        })
    return jsonify({'error': 'No more questions or invalid index'}), 404

@app.route('/submit_answer', methods=['POST'])
def submit_answer():
    """
    Receives the user's selected answer, stores it in the session,
    and returns feedback (correctness and correct answer).
    """
    data = request.json
    selected_option = data.get('selected_option')
    question_index = data.get('question_index')

    if not isinstance(question_index, int) or not (0 <= question_index < len(quiz_questions)):
        return jsonify({'error': 'Invalid question index'}), 400

    current_question = quiz_questions[question_index]
    is_correct = (selected_option == current_question['answer'])

    # Store user's answer in the session
    session['user_answers'][question_index] = selected_option

    feedback = {
        'is_correct': is_correct,
        'correct_answer': current_question['answer']
    }
    return jsonify(feedback)

@app.route('/navigate_question', methods=['POST'])
def navigate_question():
    """
    Updates the current_question_index in the session based on
    'next' or 'prev' direction.
    """
    direction = request.json.get('direction')
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
    Calculates the final score based on stored user answers
    and returns it.
    """
    final_score = 0
    # Iterate through all questions and compare user's stored answers with correct answers
    for i, q in enumerate(quiz_questions):
        if session['user_answers'][i] == q['answer']:
            final_score += 1
    # Store final score in session (optional, for potential future use)
    session['score'] = final_score
    return jsonify({
        'score': final_score,
        'total_questions': len(quiz_questions)
    })

# Run the Flask application
if __name__ == '__main__':
    # Ensure the 'templates' directory exists for Flask to find templates
    os.makedirs('templates', exist_ok=True)
    app.run(debug=True) # debug=True is useful for development (auto-reloads, error messages)
