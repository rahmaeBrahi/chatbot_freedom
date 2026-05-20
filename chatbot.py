import os
import json
from datetime import datetime
from typing import Optional
from pydantic import Field
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from config import config


@tool
def book_appointment(
    full_name: str = Field(description="User's full name (first and last name together)"),
    email: str = Field(description="Email address"),
    phone: str = Field(description="Phone number"),
    reason: str = Field(description="Reason for visit or chosen service"),
    appointment_date: str = Field(description="Chosen appointment date in YYYY-MM-DD format (from the calendar picker)"),
    preferred_time: str = Field(description="Chosen appointment time slot e.g. 9:00 AM"),
    message: str = Field(default="", description="Optional message or additional information. Default to empty string if not provided.")
):
    """
    BOOK AN APPOINTMENT. Call this immediately once you have collected the 6 required fields.
    """
    import requests

    name_parts = full_name.strip().split()
    first_name = name_parts[0] if name_parts else full_name
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

    data = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone": phone,
        "reason": reason,
        "appointment_date": appointment_date,
        "preferred_time": preferred_time,
        "message": message or "",
        "timestamp": datetime.now().isoformat(),
        "idempotency_key": "chatbot-" + datetime.now().strftime("%Y%m%d%H%M%S")
    }

    print(f"DEBUG: Submitting lead for {first_name} {last_name}...")

    try:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        print(f"DEBUG: POSTing to {config.LARAVEL_API_URL}...")
        response = requests.post(config.LARAVEL_API_URL, json=data, headers=headers, timeout=15)
        if response.status_code in [200, 201]:
            print("DEBUG: Success!")
        else:
            print(f"DEBUG: API error {response.status_code} - {response.text}")
            return f"ERROR: Server returned {response.status_code}. Please try again later."
    except Exception as e:
        print(f"DEBUG: Exception: {e}")
        return "ERROR: Unable to connect to our database. Please try again or contact us directly."

    return f"SUCCESS: Contact details registered for {first_name}. Our team has been notified."


def load_knowledge_base():
    if not os.path.exists(config.CHATBOT_DATA_PATH):
        return "No knowledge base found."
    with open(config.CHATBOT_DATA_PATH, 'r', encoding='utf-8') as f:
        return f.read()


def build_system_prompt(knowledge_base: str) -> str:
    import pytz
    dublin_tz = pytz.timezone('Europe/Dublin')
    now = datetime.now(dublin_tz)
    current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    current_day = now.strftime("%A")
    is_business_hours = (now.weekday() < 6) and (9 <= now.hour < 17 or (now.hour == 17 and now.minute <= 30))

    print(f"DEBUG: Dublin Time: {current_time_str} ({current_day}), Business Hours: {is_business_hours}")

    return f"""
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
- **Tone**: Professional, empathetic, helpful, and clear.
- **Already Booked Check**: Carefully review the chat history before replying. If the `book_appointment` tool has already been called successfully in the conversation, then the user has ALREADY booked an appointment.
  - DO NOT ask them to book or suggest booking again.
  - DO NOT show them buttons like "Book Appointment".
- **Pricing & Quotes**:
  - NEVER provide fixed prices.
  - **If the user has ALREADY booked an appointment**: Remind them that since they already have a consultation booked, the dentist will examine their case and provide the exact pricing and treatment plan during their visit. Do not invite them to book.
  - **If they have NOT booked yet**: Explain that prices vary based on the individual case and invite them to book a consultation to get an accurate quote.
- **Phone Number Validation**: Do NOT validate or check the format of the phone number. Accept whatever phone number the user provides as-is (e.g., international numbers, local numbers, digits only, etc.) without claiming there is a formatting issue.

### CONVERSATION FLOW & APPOINTMENT BOOKING:
1. **Identify Need**: Answer any questions they have using the Knowledge Base. If they want to book, proceed.
2. **Request All Details at Once**: When the user wants to book, the UI shows a calendar. Once they select date/time, ask for:
   - Full Name (e.g., "Rahma Ebrahim") — treat this as ONE field
   - Email Address
   - Phone Number
   - Reason for Visit (e.g., General Checkup, Teeth Whitening, Dental Implants, etc.)
   - Message (Optional, any additional notes they want to add)
   NOTE: The appointment_date and preferred_time come from the calendar — DO NOT ask for them separately.
3. **Smart Extraction & Follow-up**: If the user provides some but not all info, thank them and ask only for what's missing. Do NOT ask for date/time or first/last name separately. Do NOT ask for the Message if they didn't provide one, as it is optional.
   - **Extract Robustly**: Be highly lenient when extracting user details:
     - Treat any name (like "rahma ebrahim" or "rahma ebrahim .") as the `full_name`. Do NOT ask to confirm it or complain that it's combined with another line/email.
     - Extract the email and phone number immediately even if they are written next to each other or contain punctuation.
     - Treat any dental service (like "Teeth Whitening" or "Implant") as the `reason`.
   - **No Confirmation Pedantry**: Do NOT ask the user to confirm their name, email, phone, or reason if they have provided them.
   - **No Message Delay**: The `message` field is optional. If they did not specify any extra message, do NOT ask "if they have any additional message to add". Leave it empty in the tool call and call the tool immediately.
4. **FINAL STEP**: Once you have all 6 required fields (Full Name, Email, Phone, Reason, appointment_date, preferred_time), call the `book_appointment` tool immediately. Do not ask for additional messages or confirmations before calling the tool.

### APPOINTMENT STATUS TRACKING:
- Full Name: [ ] (Required)
- Email: [ ] (Required)
- Phone: [ ] (Required)
- Reason: [ ] (Required)
- Appointment Date: [ ] (Required, from calendar)
- Preferred Time: [ ] (Required, from calendar)
- Message: [ ] (Optional)
Once all 6 required fields are filled, call the tool immediately!

### TIME & AVAILABILITY:
- Current Dublin Time: {current_time_str} ({current_day})
- Business Hours: Monday to Saturday 09:00 - 17:30 (Ireland Time), Sunday Closed.
- **CURRENT STATUS**: {"TEAM IS ONLINE - You can tell the user the clinic is open" if is_business_hours else "TEAM IS OFFLINE - You MUST inform the user the clinic is closed and follow the after-hours protocol"}
- **After-Hours Protocol**: Even when the team is OFFLINE, the booking system is fully operational. You MUST still call the `book_appointment` tool to register their details. Once booked, explain that we have successfully registered their booking request, and since the clinic is closed, our team will review and confirm it with them when we reopen. Never say "there was an issue" or tell them "to try booking again later" if the tool runs successfully!

### BUTTON SUGGESTIONS:
Append suggested buttons at the end of your response using: `[[Button Text 1, Button Text 2, ...]]`
- **Welcome Menu**: `[[Book Appointment, Dental Implants, Teeth Whitening, General Cleaning, Ask a Question]]`
- **Contact Methods**: `[[Phone, Email]]`

### KNOWLEDGE BASE:
{knowledge_base}
"""


def create_chatbot_agent():
    """Creates and returns a simple tool-calling agent using langchain_core only."""
    knowledge_base = load_knowledge_base()
    system_prompt = build_system_prompt(knowledge_base)

    llm = ChatOpenAI(
        openai_api_key=config.OPENROUTER_API_KEY,
        openai_api_base="https://openrouter.ai/api/v1",
        model_name=config.MODEL_NAME,
        temperature=config.TEMPERATURE,
        default_headers={
            "HTTP-Referer": "https://freedomdental.ie",
            "X-Title": "Freedom Dental Assistant"
        }
    )

    tools = [book_appointment]
    llm_with_tools = llm.bind_tools(tools)
    tools_by_name = {t.name: t for t in tools}

    class SimpleAgent:
        def invoke(self, input_data: dict) -> dict:
            # Build message list
            messages = [SystemMessage(content=system_prompt)]
            for msg in input_data.get("chat_history", []):
                messages.append(msg)
            messages.append(HumanMessage(content=input_data["input"]))

            last_response = None
            # Agent loop — max 5 iterations to avoid infinite loops
            for _ in range(5):
                response = llm_with_tools.invoke(messages)
                messages.append(response)
                last_response = response

                # No tool calls → final answer
                if not getattr(response, "tool_calls", None):
                    break

                # Execute each tool call
                for tc in response.tool_calls:
                    tool_name = tc["name"]
                    tool_args = tc["args"]
                    print(f"DEBUG: Calling tool '{tool_name}' with args: {tool_args}")
                    if tool_name in tools_by_name:
                        result = tools_by_name[tool_name].invoke(tool_args)
                    else:
                        result = f"ERROR: Unknown tool '{tool_name}'"
                    messages.append(ToolMessage(
                        content=str(result),
                        tool_call_id=tc["id"]
                    ))

            return {"output": last_response.content if last_response else "Sorry, I couldn't process that."}

    return SimpleAgent()
