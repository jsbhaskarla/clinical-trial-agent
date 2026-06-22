import os
import sys
import json
import anthropic
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trials_mcp import search_trials, get_trial_details, check_eligibility

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are an expert clinical trial matching assistant.
You help patients and caregivers find relevant clinical trials based on their medical situation.

You have access to three tools:
1. search_trials - Search ClinicalTrials.gov for recruiting trials
2. get_trial_details - Get full details on a specific trial
3. check_eligibility - Check if a patient profile matches a trial

IMPORTANT: Always remember details the user has already shared (age, condition, sex, location).
When a user says "check my eligibility" or similar, use the details they already provided.

When a user describes their situation:
- Extract and REMEMBER: condition, age, sex, treatment history, location
- Search for relevant trials
- Check eligibility for the most promising ones
- Explain results clearly and compassionately
- Always remind users to consult their doctor

Never provide medical advice. Only help find potentially relevant trials."""

TOOLS = [
    {
        "name": "search_trials",
        "description": "Search ClinicalTrials.gov for recruiting clinical trials",
        "input_schema": {
            "type": "object",
            "properties": {
                "condition": {"type": "string", "description": "Medical condition or disease"},
                "intervention": {"type": "string", "description": "Drug or treatment being studied"},
                "phase": {"type": "string", "description": "Trial phase: PHASE1, PHASE2, PHASE3, PHASE4"},
                "max_results": {"type": "integer", "description": "Max results (default 5)"}
            },
            "required": ["condition"]
        }
    },
    {
        "name": "get_trial_details",
        "description": "Get full details for a specific trial by NCT ID",
        "input_schema": {
            "type": "object",
            "properties": {
                "nct_id": {"type": "string", "description": "The NCT ID e.g. NCT06059469"}
            },
            "required": ["nct_id"]
        }
    },
    {
        "name": "check_eligibility",
        "description": "Check if a patient profile matches a trial's eligibility criteria",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_profile": {
                    "type": "object",
                    "properties": {
                        "age": {"type": "integer"},
                        "sex": {"type": "string"},
                        "condition": {"type": "string"}
                    }
                },
                "trial": {"type": "object"}
            },
            "required": ["patient_profile", "trial"]
        }
    }
]

def run_tool(tool_name, tool_input):
    if tool_name == "search_trials":
        return search_trials(**tool_input)
    elif tool_name == "get_trial_details":
        return get_trial_details(**tool_input)
    elif tool_name == "check_eligibility":
        return check_eligibility(**tool_input)
    return {"error": f"Unknown tool: {tool_name}"}

# Store conversation history per session
conversation_histories = {}

def ask_agent(question, session_id="default", max_iterations=8):
    # Get or create conversation history for this session
    if session_id not in conversation_histories:
        conversation_histories[session_id] = []

    # Add new user message to history
    conversation_histories[session_id].append({
        "role": "user",
        "content": question
    })

    messages = conversation_histories[session_id].copy()
    iterations = 0

    while iterations < max_iterations:
        iterations += 1
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages
        )

        if response.stop_reason == "end_turn":
            # Extract text response
            answer = ""
            for block in response.content:
                if hasattr(block, "text"):
                    answer = block.text
                    break

            # Save assistant response to history
            conversation_histories[session_id].append({
                "role": "assistant",
                "content": answer
            })

            return answer

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in response.content:
                if block.type == "tool_use":
                    print(f"  🔧 Calling {block.name}...")
                    result = run_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result)
                    })

            messages.append({"role": "user", "content": tool_results})

    return "I wasn't able to complete the search. Please try again."

def reset_session(session_id):
    if session_id in conversation_histories:
        del conversation_histories[session_id]
