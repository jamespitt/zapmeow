import os
import sqlite3
from datetime import datetime
import requests
import json
import shared_utils # Import shared_utils

# Configuration
# Use the DATABASE_PATH from shared_utils
DATABASE_PATH = shared_utils.DATABASE_PATH

# Replace with the actual URL of your running ZapMeow API
# Use the SEND_API_URL from shared_utils, but adjust for the specific endpoint
# The shared_utils SEND_API_URL is for a different endpoint, so we'll define the correct one here.
ZAPMEOW_API_BASE_URL = 'http://localhost:8080/api' # Base URL for your ZapMeow API

# Replace with the instance ID you want to use to send messages
# This might need to be passed as an argument to the script or retrieved differently
# For now, using a placeholder. You'll need to update this.
WHATSAPP_INSTANCE_ID = 'my_instance_id' # <<< UPDATE THIS

# Replace with the phone number you want to send the message to (JID format: number@s.whatsapp.net)
# This might also need to be passed as an argument or retrieved.
TARGET_PHONE_NUMBER = '447906616666@s.whatsapp.net' # <<< UPDATE THIS

# Directory to save the output files
OUTPUT_DIR = os.path.expanduser('~/src/zapmeow/tasks/')

# --- LLM Prompt Templates and Notes ---
# Coaching notes from your sessions (copied from coaching.py)
COACHING_NOTES = """
- Strengths: flexibility, emotional control, stress tolerance.
- Challenges: planning, working memory, time management.
- Strategies Discussed:
  - ABC method for daily planning (A=Urgent/Important, B=Important, C=Quick).
  - "Plan and Script": Verbally state the plan for the next block of work.
  - Block booking focus time and breaks. Protecting this time is key.
  - Using a writing tablet can be more effective than a laptop for planning.
  - Self-compassion and self-praise for effort, not just outcomes.
  - Commitment is more important than motivation for starting tasks.
  - Breaking down large tasks into smaller, manageable steps.
  - On-call days are for reactive work; accept this and adjust expectations.
- Stated Values: Effectiveness/Productivity, Humor, Creativity, Wisdom/Growth, Humility/Openness/Authenticity, Connection, Play.
"""

# Coaching prompt template (adapted from coaching.py)
COACHING_PROMPT_TEMPLATE = """
You are an AI assistant with deep expertise in Acceptance and Commitment Therapy (ACT) and coaching for executive function challenges (like ADHD).
You are acting as James's personal coach. Your goal is to send him a short, supportive, and actionable message to help him stay aligned with his goals and values, based on the following transcription.

Your response should be:
1.  **Grounded in ACT**: Gently weave in an ACT concept (acceptance, defusion, present moment, self-as-context, values, committed action) without using jargon.
2.  **Personalized**: Base your message on the content of the transcription and his coaching notes.
3.  **Forward-looking and Actionable**: Provide a small, concrete suggestion related to the transcription content and his strategies.
4.  **Empathetic and Compassionate**: Acknowledge any difficulty or frustration evident in the transcription. Encourage self-compassion.
5.  **Short and Clear**: The message should be easily readable as a text message (2-4 sentences).
6.  **Aligned with his Values**: Subtly connect the suggested action back to one of his stated values.

**Coaching Notes & Strategies for James:**
{coaching_notes}

**Transcription Content:**
{transcription_text}

Based on this, generate **one short, supportive coaching message** for James.

**Generated coaching message:**
"""

# Summary prompt template
SUMMARY_PROMPT_TEMPLATE = """
You are an AI assistant. Your task is to summarize the following transcription in the first person, as if you were the person who spoke.

**Transcription Content:**
{transcription_text}

Provide the summary in the first person:
"""

# --- Database Functions ---
def get_latest_transcription(db_path):
    """Reads the latest transcription from the database."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT message_id, text, created_at FROM transcriptions ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            return {"message_id": row[0], "text": row[1], "created_at": row[2]}
        return None
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    finally:
        if conn:
            conn.close()

# --- Communication Functions ---
def send_whatsapp_message(api_url, instance_id, target_jid, message_text):
    """Sends a text message via the local ZapMeow WhatsApp API."""
    send_url = f"{api_url}/{instance_id}/chat/send/text"
    headers = {'Content-Type': 'application/json'}
    payload = {
        'jid': target_jid,
        'text': message_text
    }
    try:
        response = requests.post(send_url, headers=headers, data=json.dumps(payload))
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        print(f"WhatsApp message sent successfully to {target_jid}.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending WhatsApp message: {e}")
        return None

# --- File Handling Functions ---
def save_output_to_file(output_text, output_dir, filename_prefix):
    """Saves the formatted output to a date-based text file."""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    today_date_str = datetime.now().strftime('%Y-%m-%d_%H%M%S') # Add time for uniqueness
    filename = f"{filename_prefix}_{today_date_str}.txt"
    filepath = os.path.join(output_dir, filename)

    try:
        with open(filepath, 'w') as f:
            f.write(output_text)
        print(f"Output saved to {filepath}")
    except IOError as e:
        print(f"Error saving output to file {filepath}: {e}")

# --- Main Processing Logic ---
def main():
    print("Running db_info_processor.py...")

    if not shared_utils.API_KEY:
        print("Error: GEMINI_API_KEY environment variable not set. LLM features skipped.")
        # Continue with just database read and raw save if needed, or exit
        # For now, we'll exit if API key is missing as LLM is central to the request.
        return

    # 1. Read latest transcription from DB
    latest_transcription = get_latest_transcription(DATABASE_PATH)

    if not latest_transcription:
        print("No recent transcription found in the database. Exiting.")
        return

    transcription_text = latest_transcription.get("text", "")
    if not transcription_text:
        print("Latest transcription is empty. Exiting.")
        return

    print("Processing transcription...")

    # 2. Generate Summary
    summary_prompt = SUMMARY_PROMPT_TEMPLATE.format(transcription_text=transcription_text)
    summary_response = shared_utils.generate_llm_response(summary_prompt)

    summary_text = ""
    if summary_response and summary_response.get('success'):
        summary_text = summary_response.get('response_text').strip()
        print("\n--- Generated Summary ---")
        print(summary_text)
        print("-------------------------\n")
        # 3a. Save Summary to file
        save_output_to_file(summary_text, OUTPUT_DIR, "summary")
    else:
        print("Failed to generate summary.")
        # Optionally save the raw transcription if summary generation fails
        # save_output_to_file(transcription_text, OUTPUT_DIR, "raw_transcription_processing_failed")

    # 4. Generate Coaching Message
    coaching_prompt = COACHING_PROMPT_TEMPLATE.format(
        coaching_notes=COACHING_NOTES,
        transcription_text=transcription_text
    )
    coaching_response = shared_utils.generate_llm_response(coaching_prompt)

    coaching_message = ""
    if coaching_response and coaching_response.get('success'):
        coaching_message = coaching_response.get('response_text').strip()
        print("\n--- Generated Coaching Message ---")
        print(coaching_message)
        print("----------------------------------\n")

        # 5. Send Coaching Message to WhatsApp
        if WHATSAPP_INSTANCE_ID != 'my_instance_id' and TARGET_PHONE_NUMBER != 'number@s.whatsapp.net':
             send_whatsapp_message(ZAPMEOW_API_BASE_URL, WHATSAPP_INSTANCE_ID, TARGET_PHONE_NUMBER, coaching_message)
        else:
             print("WhatsApp configuration incomplete (Instance ID or Target Number). Skipping sending coaching message.")

        # 6. Save Coaching Message to file
        save_output_to_file(coaching_message, OUTPUT_DIR, "coaching_message")
    else:
        print("Failed to generate coaching message.")

    print("db_info_processor.py finished.")

if __name__ == "__main__":
    main()
