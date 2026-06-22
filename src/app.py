import os
import sys
import json
from flask import Flask, render_template, request, jsonify
from datetime import datetime
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent import ask_agent

load_dotenv()

app = Flask(__name__,
    template_folder=os.path.join(os.path.dirname(__file__), '..', 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), '..', 'static')
)

sessions = {}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/ask', methods=['POST'])
def ask():
    try:
        data = request.json
        question = data.get('question', '').strip()
        session_id = data.get('session_id', 'default')

        if not question:
            return jsonify({'success': False, 'error': 'Question required'}), 400
        if len(question) > 1000:
            return jsonify({'success': False, 'error': 'Question too long'}), 400

        answer = ask_agent(question)

        if session_id not in sessions:
            sessions[session_id] = []
        sessions[session_id].append({
            'question': question,
            'answer': answer,
            'timestamp': datetime.now().isoformat()
        })

        return jsonify({
            'success': True,
            'answer': answer,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/examples', methods=['GET'])
def examples():
    return jsonify([
        {
            "category": "Cancer",
            "question": "I'm a 52 year old woman with stage 3 breast cancer. What trials might I qualify for?"
        },
        {
            "category": "Diabetes",
            "question": "I have Type 2 diabetes and I'm 45 years old. Are there any trials for new treatments?"
        },
        {
            "category": "Cardiology",
            "question": "My father is 68 with heart failure. What clinical trials are recruiting?"
        },
        {
            "category": "Neurology",
            "question": "I'm 35 with early-onset Parkinson's disease. What Phase 2 or 3 trials exist?"
        },
        {
            "category": "Oncology",
            "question": "What Phase 3 trials are recruiting for lung cancer right now?"
        }
    ])

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'data_source': 'ClinicalTrials.gov (live)'
    })

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({'error': 'Server error'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port, debug=False)
