
import os
from datetime import datetime, timedelta
import shared_utils

# Configuration specific to gettasks.py
STATE_FILE_GETTASKS = os.path.expanduser('~/src/james_notes/tasks/gettasks_state.json')
# For now, let's assume we are getting tasks from the same chat as saynice.py (Steph's chat with James)
# This could be made configurable or scan multiple chats if needed later.
CHAT_JID_TO_MONITOR = '447709487896'  # Steph's JID
# Send the suggested task list to James
TARGET_PHONE_NUMBER_JAMES = '447906616842'  # James's JID

GET_TASKS_PROMPT_TEMPLATE = """
You are an AI assistant. Your primary function is to meticulously review the following chat history and identify any actionable tasks, requests, or chores mentioned.

**Chat History Context:**
The chat is primarily between Steph and James. Steph is often expressing things that need to be done around the house, for the children, or by James. James is trying to be more proactive.

**Instructions for Task Extraction:**
1.  Identify explicit tasks (e.g., "Can you pick up the dry cleaning?")
2.  Identify strongly implied tasks (e.g., "The car is making a funny noise again" could imply a task to get it checked).
3.  Focus on tasks that require action from James or are related to household/family responsibilities.
4.  For each task, extract:
    *   A concise description of the task.
    *   Who is likely responsible (e.g., James, Steph, Unclear). If directed at someone, name them.
    *   Any mentioned deadline or urgency.
5.  If a task is mentioned multiple times, consolidate it into a single entry unless the context suggests a new, distinct instance.

**Output Format:**
Present the tasks as a numbered list. Each task should be on a new line.
If no actionable tasks are identified from the provided chat history, output only the phrase: "No new tasks identified."

Example Output:
1. Task: Pick up the dry cleaning. Responsible: James. Deadline: By Friday.
2. Task: Investigate the strange noise the car is making. Responsible: James. Urgency: Soon.
3. Task: Buy groceries for the week. Responsible: Unclear.

**Chat History to Analyze:**
{chat_history_text}

**Extracted Tasks:**
"""

def main():
    if not shared_utils.API_KEY:
        print("Error: GEMINI_API_KEY environment variable not set. Exiting gettasks.py.")
        return

    state = shared_utils.load_state(STATE_FILE_GETTASKS)
    if state is None or 'last_timestamp' not in state:
        # Default to a shorter period for tasks, e.g., 3 days, as tasks might be more time-sensitive
        last_timestamp = datetime.now() - timedelta(days=3)
        print(f"No state found or invalid state for gettasks.py, starting from {last_timestamp}")
        state = {'last_timestamp': last_timestamp.isoformat()}
    else:
        last_timestamp = datetime.fromisoformat(state['last_timestamp'])
        print(f"gettasks.py: Last processed timestamp: {last_timestamp}")

    # Get messages from the specified chat JID
    messages = shared_utils.get_recent_messages(shared_utils.DATABASE_PATH, CHAT_JID_TO_MONITOR, last_timestamp)

    if not messages:
        print("gettasks.py: No new messages to process.")
        return

    print(f"gettasks.py: Found {len(messages)} new messages to process for tasks.")

    latest_message_dt = shared_utils.get_latest_message_timestamp(messages)
    if not latest_message_dt:
        print("gettasks.py: Could not determine latest message timestamp. Exiting.")
        return

    # Format messages using the default JID map in shared_utils
    # (which includes Steph and James)
    chat_history_text = shared_utils.format_messages_for_prompt(messages)

    llm_response = shared_utils.generate_llm_response(GET_TASKS_PROMPT_TEMPLATE, chat_history_text)

    if llm_response and llm_response.get('success'):
        extracted_tasks_text = llm_response.get('response_text')
        print("\n--- Extracted Tasks ---")
        print(extracted_tasks_text.strip())

        send_response = shared_utils.send_text_message(shared_utils.SEND_API_URL, TARGET_PHONE_NUMBER_JAMES, extracted_tasks_text.strip())

        if send_response and send_response.get('success'):
            # Update state with latest timestamp, LLM details, and message details
            state['last_timestamp'] = latest_message_dt.isoformat()
            state['last_llm_call'] = llm_response.get('api_details')
            state['last_message_sent'] = send_response.get('message_details')
            shared_utils.save_state(STATE_FILE_GETTASKS, state)
            print(f"gettasks.py: State saved with latest timestamp: {latest_message_dt.isoformat()}")
        else:
            print("gettasks.py: Failed to send task list message.")
            # Optionally save state with send failure details here
            # state['last_llm_call'] = llm_response.get('api_details')
            # state['last_message_send_attempt'] = send_response
            # shared_utils.save_state(STATE_FILE_GETTASKS, state)
    else:
        print("gettasks.py: Failed to generate task list from LLM.")
        # Optionally save state with LLM failure details here
        # state['last_llm_call_attempt'] = llm_response
        # shared_utils.save_state(STATE_FILE_GETTASKS, state)

if __name__ == "__main__":
    main()
