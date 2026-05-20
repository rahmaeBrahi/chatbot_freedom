# Temp app.py to diagnose import issue
from flask import Flask, jsonify
app = Flask(__name__)

@app.route('/')
def hello():
    return jsonify({
        "status": "success",
        "message": "Flask is running successfully on Vercel!"
    })

# Comment out other code temporarily
"""
from chatbot import create_chatbot_agent
from langchain_core.messages import HumanMessage, AIMessage
import uuid
# ...
"""
