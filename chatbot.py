import os
import json
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage
from config import config

@tool
def book_appointment(
    first_name: str = Field(description="User's first name"),
    last_name: str = Field(description="User's last name"),
    email: str = Field(description="Email address"),
    phone: str = Field(description="Phone number"),
    reason: str = Field(description="Reason for visit or chosen service"),
    preferred_time: str = Field(description="Preferred time (any, morning, midday, afternoon)"),
    message: str = Field(description="Message or additional information")
):
    """
    BOOK AN APPOINTMENT. Call this immediately once you have collected all 7 fields.
    """
    import requests
    import os
    import json
    from datetime import datetime
    
    data = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "reason": reason,
        "preferred_time": preferred_time,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "idempotency_key": "chatbot-" + datetime.now().strftime("%Y%m%d%H%M%S")
    }
    
    print(f"DEBUG: Attempting to submit lead details to Laravel for {first_name} {last_name}...")
    
    # Try to hit the Laravel API
    try:
        from config import config
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        print(f"DEBUG: POSTing lead data to {config.LARAVEL_API_URL}...")
        response = requests.post(config.LARAVEL_API_URL, json=data, headers=headers, timeout=15)
        if response.status_code in [200, 201]:
            print(f"DEBUG: Success! Lead submitted to Laravel API.")
        else:
            print(f"DEBUG: Laravel API failed with status {response.status_code} - {response.text}")
            return f"ERROR: The server returned an error: {response.status_code}. Please try again later."
    except Exception as e:
        print(f"DEBUG: Exception hitting Laravel API: {e}")
        return "ERROR: Unable to connect to our database. Please try again later or contact us directly."

    return f"SUCCESS: Contact details registered for {first_name}. Our team has been notified."

def load_knowledge_base():
    if not os.path.exists(config.CHATBOT_DATA_PATH):
        return "No knowledge base found."
    with open(config.CHATBOT_DATA_PATH, 'r', encoding='utf-8') as f:
        return f.read()

def create_chatbot_agent():
    knowledge_base = load_knowledge_base()
    
    llm = ChatOpenAI(
        openai_api_key=config.OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
        model_name=config.MODEL_NAME,
        temperature=config.TEMPERATURE,
        default_headers={
            "HTTP-Referer": "https://flexiboost.ie", 
            "X-Title": "Flexi Boost AI Assistant"
        }
    )
    
    tools = [book_appointment]
    
    import pytz
    dublin_tz = pytz.timezone('Europe/Dublin')
    now = datetime.now(dublin_tz)
    current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    current_day = now.strftime("%A")
    
    is_business_hours = (now.weekday() < 6) and (9 <= now.hour < 17 or (now.hour == 17 and now.minute <= 30))
    
    print(f"DEBUG: Dublin Time: {current_time_str} ({current_day})")
    print(f"DEBUG: Is Business Hours: {is_business_hours}")
    
    system_prompt = f"""
You are Freedom Dental Assistant, the AI Assistant for Freedom Dental, a Dublin-based dental clinic.
Your goal is to answer patient questions and help them book an appointment.

### CORE SERVICES:
1. Dental Implants
2. Dental Implant Crowns & Bridges
3. Dental Crowns
4. Dental Veneers
5. Professional Dental Cleaning
6. Teeth Whitening
7. Dental Braces
8. Root Canal Treatment
9. Composite Fillings
10. Inlays and Onlays

### BUSINESS RULES:
- **Scope**: We provide professional dental care in Dublin.
- **Pricing**: NEVER provide fixed prices. Explain it depends on a consultation and guide to a quote/booking.
- **Tone**: Professional, empathetic, helpful, and clear.

### CONVERSATION FLOW & APPOINTMENT BOOKING:
1. **Identify Need**: Answer any questions they have using the Knowledge Base. If they want to book, proceed to collect details.
2. **Request All Details at Once**: When the user indicates they want to book an appointment, ask them to provide all the required booking information at once in a single, friendly message. The required fields are:
   - Full Name (First and Last name)
   - Email Address
   - Phone Number
   - Reason for Visit (e.g., General Checkup, Teeth Whitening, Dental Implants, etc.)
   - Preferred Time (Any time, Morning, Midday, or Afternoon)
   - Message (Any additional notes or details)
3. **Smart Extraction & Follow-up**: If the user replies with some but not all of the information, thank them for what they provided, list the specific missing details clearly, and ask them to provide only those missing items. Do not ask for any information they have already provided.
4. **FINAL STEP**: Once you have gathered all 7 pieces of information (First Name, Last Name, Email, Phone, Reason, Preferred Time, Message), call the `book_appointment` tool immediately before saying anything else.

### APPOINTMENT STATUS TRACKING:
Internally track which of these you have:
- First Name: [ ]
- Last Name: [ ]
- Email: [ ]
- Phone: [ ]
- Reason: [ ]
- Time: [ ]
- Message: [ ]
Once all are checked, use the tool!

### TIME & AVAILABILITY:
- Current Dublin Time: {current_time_str} ({current_day})
- Business Hours: Monday to Saturday 09:00 - 17:30 (Ireland Time), Sunday Closed.
- **CURRENT STATUS**: {"TEAM IS ONLINE - You can tell the user the clinic is open" if is_business_hours else "TEAM IS OFFLINE - You MUST inform the user the clinic is closed and follow the after-hours protocol"}
- **After-Hours Protocol**: If the clinic is OFFLINE, inform the user they are currently closed and will respond during business hours. Still collect appointment details.

### BUTTON SUGGESTIONS:
To improve user experience, append suggested buttons at the end of your response using the format: `[[Button Text 1, Button Text 2, ...]]`.
- **Welcome Menu**: `[[Book Appointment, Dental Implants, Teeth Whitening, General Cleaning, Ask a Question]]`
- **Preferred Time Options**: `[[Any time, Morning, Midday, Afternoon]]`
- **Contact Methods**: `[[Phone, Email]]`

### KNOWLEDGE BASE:
{knowledge_base}
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    
    agent = create_tool_calling_agent(llm, tools, prompt)
    
    return AgentExecutor(agent=agent, tools=tools, verbose=True)

def chat_loop():
    print("Freedom Dental Assistant: Hi! I'm Freedom Dental Assistant. How can I help your smile today?")
    agent_executor = create_chatbot_agent()
    chat_history = []
    
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Freedom Dental Assistant: Goodbye! Have a great day.")
            break
            
        response = agent_executor.invoke({
            "input": user_input,
            "chat_history": chat_history
        })
        
        print(f"Freedom Dental Assistant: {response['output']}")
        
        chat_history.append(HumanMessage(content=user_input))
        chat_history.append(AIMessage(content=response['output']))
        
        if len(chat_history) > 10:
            chat_history = chat_history[-10:]

if __name__ == "__main__":
    chat_loop()

