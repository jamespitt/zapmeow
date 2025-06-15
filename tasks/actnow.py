
import os
from datetime import datetime, timedelta
import shared_utils

# Configuration specific to actnow.py
STATE_FILE_ACTNOW = os.path.expanduser('~/src/james_notes/tasks/actnow_state.json')
# Monitor the same chat as saynice.py (Steph's chat with James) for context
CHAT_JID_TO_MONITOR = '447709487896'  # Steph's JID
# Send the suggested ACT message to James
TARGET_PHONE_NUMBER_JAMES = '447906616842'  # James's JID

ACT_PROMPT_TEMPLATE = """
You are an AI assistant trained in Acceptance and Commitment Therapy (ACT) principles. James wants to send a short, supportive text message to his wife, Steph. Steph is going through a very challenging time, feeling overwhelmed, stressed, and dealing with significant life changes and health issues (menopause after a hysterectomy, mental load, feeling unheard).

James wants the message to:
1.  Be very gentle and empathetic.
2.  Subtly incorporate an ACT idea without being preachy or sounding like a therapist.
3.  Focus on one of these ACT concepts:
    *   **Acceptance:** Acknowledging difficult feelings are present without trying to change them immediately ("It's okay to feel this way").
    *   **Mindfulness/Present Moment:** Gently bringing attention to the present, even if just for a moment ("Thinking of you right now").
    *   **Values:** Subtly reminding of shared values or her own strength/values ("Remember how strong you are").
    *   **Self-Compassion:** Encouraging kindness towards herself ("Be gentle with yourself today").
    *   **Defusion:** Helping to see thoughts as just thoughts, not absolute truths (more advanced, perhaps use sparingly).
4.  Be very short, suitable for a text message (1-3 sentences).
5.  Offer support and connection, not solutions unless explicitly part of an ACT technique (e.g., "I'm here with you," "I'm on your team").
6.  Avoid minimizing her feelings or sounding dismissive.
7.  The message should feel like it's coming from a loving husband who is trying to be supportive.

Optional Context from recent chat (use if provided chat history indicates specific struggles):
{chat_history_text}

Based on this, please generate **one short text message** for James to send to Steph.
If the chat history is particularly relevant to a specific struggle, try to make the message gently relevant to that. If not, a more general ACT-inspired supportive message is fine.

Example of what NOT to do:
- "You should try to accept your feelings." (Too direct, preachy)
- "Just be mindful." (Too simplistic)
- "Everything will be okay." (Potentially dismissive)

Example of a possible message:
"Hey, just thinking of you. Remember to be kind to yourself today, you're navigating so much. I'm here for you. ❤️"
"Sending you a wave of calm. It's okay for things to feel tough right now. I see you and I'm with you."
"Thinking of you and sending a little strength your way. You've got this, and I've got you."

Generated message:
"""

def main():
    if not shared_utils.API_KEY:
        print("Error: GEMINI_API_KEY environment variable not set. Exiting actnow.py.")
        return

    state = shared_utils.load_state(STATE_FILE_ACTNOW)
    if state is None or 'last_timestamp' not in state:
        # Start from a recent period, e.g., 1 day, as these messages are more about gentle reminders
        last_timestamp = datetime.now() - timedelta(days=1)
        print(f"No state found or invalid state for actnow.py, starting from {last_timestamp}")
        state = {'last_timestamp': last_timestamp.isoformat()}
    else:
        last_timestamp = datetime.fromisoformat(state['last_timestamp'])
        print(f"actnow.py: Last processed timestamp: {last_timestamp}")

    messages = shared_utils.get_recent_messages(shared_utils.DATABASE_PATH, CHAT_JID_TO_MONITOR, last_timestamp)

    chat_history_text = ""
    if messages:
        print(f"actnow.py: Found {len(messages)} new messages for context.")
        # Get the latest message timestamp for state saving, even if we don't always use the history for the prompt
        latest_message_dt = shared_utils.get_latest_message_timestamp(messages)
        if not latest_message_dt:
            print("actnow.py: Could not determine latest message timestamp from context. Using current time for next state.")
            latest_message_dt = datetime.now() # Fallback
        chat_history_text = shared_utils.format_messages_for_prompt(messages)
    else:
        print("actnow.py: No new messages for context. Will generate a general ACT message.")
        # If no messages, we still want to generate a general message and update the timestamp to now
        latest_message_dt = datetime.now()


    llm_response = shared_utils.generate_llm_response(ACT_PROMPT_TEMPLATE, chat_history_text)

    if llm_response and llm_response.get('success'):
        act_message_suggestion = llm_response.get('response_text')
        print("actnow.py: Generated ACT Message Suggestion:")
        print(act_message_suggestion)

        send_response = shared_utils.send_text_message(shared_utils.SEND_API_URL, TARGET_PHONE_NUMBER_JAMES, act_message_suggestion.strip())

        if send_response and send_response.get('success'):
            # Update state with latest timestamp, LLM details, and message details
            state['last_timestamp'] = latest_message_dt.isoformat()
            state['last_llm_call'] = llm_response.get('api_details')
            state['last_message_sent'] = send_response.get('message_details')
            shared_utils.save_state(STATE_FILE_ACTNOW, state)
            print(f"actnow.py: State saved with latest timestamp: {latest_message_dt.isoformat()}")
        else:
            print("actnow.py: Failed to send ACT message.")
            # Optionally save state with send failure details here if needed for debugging
            # state['last_llm_call'] = llm_response.get('api_details') # Still save LLM details
            # state['last_message_send_attempt'] = send_response # Save send attempt details
            # shared_utils.save_state(STATE_FILE_ACTNOW, state)
    else:
        print("actnow.py: Failed to generate an ACT message suggestion.")
        # Optionally save state with LLM failure details here if needed for debugging
        # state['last_llm_call_attempt'] = llm_response # Save LLM attempt details
        # shared_utils.save_state(STATE_FILE_ACTNOW, state)

if __name__ == "__main__":
    main()
