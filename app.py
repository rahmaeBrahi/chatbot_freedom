from flask import Flask, jsonify
import traceback

app = Flask(__name__)

@app.route('/')
def test_imports():
    """Diagnostic endpoint: tests each import and reports which ones fail."""
    results = {}

    for name, stmt in [
        ("langchain_core.messages",   "from langchain_core.messages import HumanMessage, AIMessage"),
        ("langchain_core.prompts",    "from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder"),
        ("langchain_core.tools",      "from langchain_core.tools import tool"),
        ("langchain_openai",          "from langchain_openai import ChatOpenAI"),
        ("langchain.agents",          "from langchain.agents import AgentExecutor, create_tool_calling_agent"),
        ("pydantic.Field",            "from pydantic import BaseModel, Field"),
        ("pytz",                      "import pytz"),
        ("chatbot",                   "from chatbot import create_chatbot_agent"),
    ]:
        try:
            exec(stmt)
            results[name] = "OK"
        except Exception as e:
            results[name] = f"ERROR: {traceback.format_exc()}"

    return jsonify(results)
