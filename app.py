from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from chatbot import create_chatbot_agent
from langchain_core.messages import HumanMessage, AIMessage
import uuid

app = Flask(__name__)
CORS(app)

@app.after_request
def add_header(response):
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    response.headers['Content-Security-Policy'] = "frame-ancestors *"
    return response

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json or {}
    user_input = data.get('message')
    session_id = data.get('session_id')
    history_data = data.get('history', [])
    
    if not session_id:
        session_id = str(uuid.uuid4())
        
    # Reconstruct history from client payload
    chat_history = []
    for msg in history_data:
        role = msg.get('role')
        content = msg.get('content')
        if role == 'user':
            chat_history.append(HumanMessage(content=content))
        elif role == 'bot':
            chat_history.append(AIMessage(content=content))
    
    try:
        agent = create_chatbot_agent()
        response = agent.invoke({
            "input": user_input,
            "chat_history": chat_history
        })
        
        output = response['output']
        buttons = []
        
        import re
        button_match = re.search(r'\[\[(.*?)\]\]', output)
        if button_match:
            button_str = button_match.group(1)
            buttons = [b.strip() for b in button_str.split(',')]
            output = re.sub(r'\[\[.*?\]\]', '', output).strip()
            
        return jsonify({
            "output": output,
            "buttons": buttons,
            "session_id": session_id
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/slots', methods=['GET'])
def slots():
    """Proxy to Laravel to get booked slots for a given date."""
    import requests as req
    from config import config
    date = request.args.get('date')
    if not date:
        return jsonify({'error': 'date parameter required'}), 400
    try:
        base = config.LARAVEL_API_URL.replace('/api/chatbot/lead', '')
        resp = req.get(f"{base}/api/chatbot/slots", params={'date': date}, timeout=8)
        return jsonify(resp.json()), resp.status_code
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
