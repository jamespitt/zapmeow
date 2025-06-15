import os
from datetime import datetime, timedelta
import shared_utils # Assuming this contains your LLM and messaging functions

# Configuration specific to coaching.py
STATE_FILE_COACHING = os.path.expanduser('~/src/james_notes/tasks/coaching_state.json')

# --- Configuration ---
# Directory containing the markdown journal files
JOURNAL_DIR = os.path.expanduser('/home/james/src/james_notes/Journal/')
# Send the coaching message to yourself
TARGET_PHONE_NUMBER_JAMES = '447906616842' # Your JID

# Coaching notes from your sessions. In a real script, you might load this from a file.
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

COACHING_PROMPT_TEMPLATE = """
You are an AI assistant with deep expertise in Acceptance and Commitment Therapy (ACT) and coaching for executive function challenges (like ADHD).
You are acting as James's personal coach. Your goal is to send him a short, supportive, and actionable message to help him stay aligned with his goals and values.

Your response should be:
1.  **Grounded in ACT**: Gently weave in an ACT concept (acceptance, defusion, present moment, self-as-context, values, committed action) without using jargon.
2.  **Personalized**: Base your message on his recent journal entries and his coaching notes. Acknowledge his recent experiences.
3.  **Forward-looking and Actionable**: Provide a small, concrete suggestion for the day ahead. This should relate directly to the strategies he is working on (e.g., ABC method, scripting, protecting breaks).
4.  **Empathetic and Compassionate**: Acknowledge the difficulty and frustration inherent in this work. Encourage self-compassion.
5.  **Short and Clear**: The message should be easily readable as a text message (2-4 sentences).
6.  **Aligned with his Values**: Subtly connect the suggested action back to one of his stated values (e.g., "Taking this small step is a move toward 'Effectiveness'").

**Coaching Notes & Strategies for James:**
{coaching_notes}

**James's Journal Entries from the Past Week:**
{journal_entries}

Based on all this information, generate **one short, supportive coaching message** for James for the start of his day.

**Example of what NOT to do:**
- "You failed to take a break yesterday. You must do better." (Judgmental)
- "Just use the ABC method." (Simplistic, not empathetic)
- "According to ACT, you need to practice cognitive defusion." (Too clinical)

**Example of a possible message:**
"Hey James. I read your entry about the 'mountain' project. It's natural to feel resistance with big tasks. Today, just focus on one small, climbable step. Try scripting just the first 20 minutes. That single action is a powerful move towards your value of 'Effectiveness'."
"Good morning, James. I saw that protecting your focus time felt powerful yesterday. Let's build on that. What's one block of time you can wall off for yourself today? Remember, even small acts of commitment build momentum. Be kind to yourself through the process."

**Generated coaching message:**
"""

def get_recent_journal_entries(directory, days=7):
    """Reads all .md files from the last 'days' in the specified directory."""
    entries = []
    for i in range(days):
        date = datetime.now() - timedelta(days=i)
        filename = date.strftime('%Y-%m-%d') + '.md'
        filepath = os.path.join(directory, filename)
        
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                entries.append(f"--- Entry for {date.strftime('%Y-%m-%d')} ---\n{content}")
            except Exception as e:
                print(f"Error reading file {filepath}: {e}")
                
    # Return entries in chronological order
    return "\n\n".join(reversed(entries))

def main():
    if not shared_utils.API_KEY:
        print("Error: GEMINI_API_KEY environment variable not set. Exiting.")
        return

    state = shared_utils.load_state(STATE_FILE_COACHING)
    if state is None or 'last_timestamp' not in state:
        # Default to a recent period, e.g., 7 days, as journal entries are read from this period
        last_timestamp = datetime.now() - timedelta(days=7)
        print(f"No state found or invalid state for coaching.py, starting from {last_timestamp}")
        state = {'last_timestamp': last_timestamp.isoformat()}
    else:
        last_timestamp = datetime.fromisoformat(state['last_timestamp'])
        print(f"coaching.py: Last processed timestamp: {last_timestamp}")

    print("Reading recent journal entries...")
    journal_entries_text = get_recent_journal_entries(JOURNAL_DIR, days=7)

    if not journal_entries_text:
        print("No recent journal entries found. Exiting.")
        return
        
    print("Found journal entries. Generating coaching message...")
    
    # The new prompt doesn't need a separate chat_history placeholder.
    # We can format the final prompt directly.
    final_prompt = COACHING_PROMPT_TEMPLATE.format(
        coaching_notes=COACHING_NOTES,
        journal_entries=journal_entries_text
    )

    llm_response = shared_utils.generate_llm_response(final_prompt)

    if llm_response and llm_response.get('success'):
        coaching_message = llm_response.get('response_text')
        print("\n--- Generated Coaching Message ---")
        print(coaching_message.strip())
        print("----------------------------------\n")

        send_response = shared_utils.send_text_message(shared_utils.SEND_API_URL, TARGET_PHONE_NUMBER_JAMES, coaching_message.strip())

        if send_response and send_response.get('success'):
            # Update state with latest timestamp, LLM details, and message details
            # Note: coaching.py doesn't process chat messages, so we use current time for state timestamp
            state['last_timestamp'] = datetime.now().isoformat()
            state['last_llm_call'] = llm_response.get('api_details')
            state['last_message_sent'] = send_response.get('message_details')
            shared_utils.save_state(STATE_FILE_COACHING, state)
            print(f"coaching.py: State saved with current timestamp: {datetime.now().isoformat()}")
        else:
             print("Failed to send coaching message.")
             # Optionally save state with send failure details here
             # state['last_llm_call'] = llm_response.get('api_details')
             # state['last_message_send_attempt'] = send_response
             # shared_utils.save_state(STATE_FILE_COACHING, state)
    else:
        print("Failed to generate a coaching message.")
        # Optionally save state with LLM failure details here
        # state['last_llm_call_attempt'] = llm_response
        # shared_utils.save_state(STATE_FILE_COACHING, state)

if __name__ == "__main__":
    main()

