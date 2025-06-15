
import sqlite3
import json
import os
from datetime import datetime, timedelta
import requests # Keep requests import
import google.generativeai as genai # Corrected import for Gemini API
# from google.genai import types # Not strictly needed for basic generation

# Configure Gemini API - User needs to set the GEMINI_API_KEY environment variable
API_KEY = os.getenv("GEMINI_API_KEY")
# It's better for individual scripts to check API_KEY and exit if necessary,
# rather than a shared library exiting.

DATABASE_PATH = os.path.expanduser('~/.zapmeow/zapmeow.db')
SEND_API_URL = 'http://192.168.0.151:8900/api/3/chat/send/text'

# Default JID Map - can be extended or overridden by scripts
DEFAULT_JID_MAP = {
    '447709487896': 'Steph',
    '447906616842': 'James'
}

def load_state(state_file):
    """Loads the last processed timestamp from the state file."""
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            try:
                state = json.load(f)
                if 'last_timestamp' in state:
                    return datetime.fromisoformat(state['last_timestamp'])
            except json.JSONDecodeError:
                print(f"Error decoding state file: {state_file}")
                return None
    \
    return None

def save_state(state_file, state_data):
    """Saves the state data dictionary to the state file."""
    os.makedirs(os.path.dirname(state_file), exist_ok=True) # Ensure directory exists
    with open(state_file, 'w') as f:
        json.dump(state_data, f, indent=4) # Use indent for readability

def get_recent_messages(db_path, chat_jid, since_timestamp):
    """Fetches recent messages from the database since a given timestamp."""
    conn = None
    messages = []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        since_timestamp_str = since_timestamp.strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute(
            "SELECT timestamp, sender_jid, body FROM messages WHERE chat_jid = ? AND timestamp > ? ORDER BY timestamp ASC",
            (chat_jid, since_timestamp_str)
        )
        messages = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        print(f"Database path: {db_path}")
    finally:
        if conn:
            conn.close()
    return messages

def format_messages_for_prompt(messages, jid_map=None):
    """Formats messages for the LLM prompt, replacing JIDs with names."""
    current_jid_map = jid_map if jid_map is not None else DEFAULT_JID_MAP
    formatted_text = "Chat History:\\n"
    for timestamp, sender_jid, body in messages:
        sender_name = current_jid_map.get(sender_jid, sender_jid) # Use JID if name not found
        formatted_text += f"[{timestamp}] {sender_name}: {body}\\n"
    return formatted_text

def generate_llm_response(prompt_template, chat_history_text=""):
    """Uses Gemini to generate a response based on the provided prompt and chat history."""
    if not API_KEY:
        print("Error: GEMINI_API_KEY not set. LLM generation skipped.")
        return None

    genai.configure(api_key=API_KEY) # Ensure API key is configured for the client

    full_prompt = f"{prompt_template}\\n{chat_history_text}"
    model = genai.GenerativeModel('gemini-1.5-flash-latest') # Specify the model

    try:
        # For gemini-1.5-flash, the direct method is generate_content
        response = model.generate_content(
            contents=[full_prompt],
            # generation_config=genai.types.GenerationConfig( # if using specific config
            #     max_output_tokens=500,
            #     temperature=0.7
            # )
        )
        # Return a dictionary with details
        return {
            'success': True,
            'response_text': response.text,
            'api_details': {
                'model': 'gemini-1.5-flash-latest',
                'prompt': full_prompt, # Include prompt for context
                # Add other relevant details from response object if needed
                # e.g., 'usage_metadata': response.usage_metadata
            }
        }
    except Exception as e:
        print(f"Gemini API error: {e}")
        return {
            'success': False,
            'error': str(e),
            'api_details': {
                'model': 'gemini-1.5-flash-latest',
                'prompt': full_prompt
            }
        }

def send_text_message(api_url, phone_number, text):
    """Sends the text message via a POST request."""
    payload = {
        'phone': phone_number,
        'text': text
    }
    try:
        response = requests.post(api_url, json=payload)
        response.raise_for_status()
        print(f"Message sent successfully to {phone_number}.")
        return {
            'success': True,
            'message_details': {
                'api_url': api_url,
                'phone_number': phone_number,
                'text_sent': text,
                'status_code': response.status_code
            }
        }
    except requests.exceptions.RequestException as e:
        print(f"Error sending message to {phone_number}: {e}")
        return {
            'success': False,
            'error': str(e),
            'message_details': {
                'api_url': api_url,
                'phone_number': phone_number,
                'text_sent': text # Still include text for context even on failure
            }
        }

def get_latest_message_timestamp(messages):
    """Extracts and parses the timestamp of the latest message."""
    if not messages:
        return None
    latest_message_timestamp_str = messages[-1][0] # (timestamp, sender_jid, body)
    try:
        # Attempt to parse with timezone (e.g., +01:00)
        dt_object = datetime.strptime(latest_message_timestamp_str, '%Y-%m-%d %H:%M:%S%z')
    except ValueError:
        # Fallback if no timezone or different format (e.g., 'Z' or no offset)
        try:
            dt_object = datetime.fromisoformat(latest_message_timestamp_str.replace('Z', '+00:00'))
        except ValueError as e_iso:
            print(f"Error parsing timestamp '{latest_message_timestamp_str}': {e_iso}")
            return None
    return dt_object
