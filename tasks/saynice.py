
import os
from datetime import datetime, timedelta
import shared_utils

# Configuration specific to saynice.py
STATE_FILE = os.path.expanduser('~/src/james_notes/tasks/saynice_state.json')
CHAT_JID_STEPH = '447709487896'  # Steph's JID
TARGET_PHONE_NUMBER_JAMES = '447906616842'  # James's JID

SAYNICE_PROMPT_TEMPLATE = """
As a CBT marriage counselor, you'd want to set the stage for the AI's persona and purpose.
"I need help crafting messages and affirmations to make my wife, Steph, feel genuinely appreciated and seen. We're going through a challenging time, and I want to ensure my words reflect my understanding of her struggles and my gratitude for everything she is and does.
Here's some background on our situation:
 * Steph's Feelings & Burdens:
   * She feels incredibly overwhelmed by the mental load of a full-time job, managing our two young children, and running the household. This is especially hard as I work away from home Monday to Wednesday nights.
   * She feels like she's carrying more than her share of household responsibilities and is tired of always having to delegate tasks or create lists for me.
   * She often feels unheard, and when she expresses her feelings, she feels I sometimes dismiss them or don't truly internalize what she's saying.
   * She had a hysterectomy last year, which brought on menopause. She's struggling with hormonal imbalances, constant tiredness, poor sleep, and significant impacts on her mental health. She feels she's lost her sense of purpose and sometimes feels like a 'maid and a servant' to the family.
   * She desires more 'me time' but finds it hard to relax even when I take the children because she often has to ask for it, and she can still hear them if they cry.
   * She feels I spend too much time on screens and am not always present, missing what's happening with the children or what needs doing.
   * She feels resentful about having to praise me for doing basic adult tasks.
   * She has tried to offer suggestions and help in the past (like sending articles on cleaning for ADHD), but feels these efforts were dismissed, making her hesitant to try again.
   * Her goal is for our relationship to be more equal, with me doing my 50% of household and childcare responsibilities without needing to be asked or given a list. She feels 'incredibly ragey and snappy' due to everything.
 * My Perspective & Goals:
   * I was recently diagnosed with ADHD, and I know some of its traits can be frustrating for Steph. I struggle with keeping up with tasks and the mental load, which definitely puts more stress on her.
   * Our arguments often involve her expressing anger, and I find it hard to cope with this, sometimes leading me to avoid conflict. I often feel like I'm just being told what I've done wrong, which leaves me demotivated and feeling like I can't do anything right.
   * I feel that even when I try to improve or take on more, Steph doesn't always acknowledge the effort or improvement, making it hard for me to know if I'm on the right track.
   * My main goal right now is to make Steph feel truly appreciated, loved, and understood. I want to improve our communication so we can both feel heard and work together better. I want to stop feeling like I'm going to fail her.
What I need from you:
Please generate examples of things I can write in a note, send as a text message, or say directly to Steph to help her feel more appreciated. These should:
 * Acknowledge her specific burdens: Show I see how much she's juggling (work, kids, house, her health).
 * Validate her feelings: Let her know that her feelings of being overwhelmed, tired, and unheard are valid.
 * Express genuine gratitude for specific things: Not just a general 'thanks,' but appreciation for particular efforts, like managing the kids while I'm away, her work ethic, or specific household tasks she handles. Also, acknowledge the 'unseen' mental load she carries.
 * Show I'm listening and want to understand: Reference things she's said or her general state of being.
 * Express appreciation for her, not just what she does: Acknowledge her strength, resilience, or other qualities you admire in her as a person, especially during this tough time with her health.
 * Convey my commitment to change (without making empty promises): Hint at my desire to be a more equal partner and to take on more responsibility proactively, without her having to ask.
 * Be sincere, empathetic, and loving.
Examples of formats:
 * Short, heartfelt notes left where she'll find them.
 * Text messages during the day.
 * Things I can say in a quiet moment.
Things to avoid:
 * Sounding like I'm making excuses for myself (e.g., blaming my ADHD).
 * Making it about how I feel (e.g., \"It makes me sad when you're upset\").
 * Phrases that could sound like I'm expecting praise for simply noticing or saying something.
 * Generic compliments.
Optional: Beyond Words
If you have suggestions for small, tangible actions I could take that would directly reinforce these words of appreciation (keeping in mind her desire for me to take initiative with household/childcare tasks without being asked), please include a few.
I really want to make a positive difference and help her feel the love and appreciation she deeply deserves."

please note this recent chat on whatsapp to give your more ideas. please keep the text quite short and suitable for a text message.
"""

def main():
    if not shared_utils.API_KEY:
        print("Error: GEMINI_API_KEY environment variable not set. Exiting.")
        return

    state = shared_utils.load_state(STATE_FILE)
    if state is None or 'last_timestamp' not in state:
        last_timestamp = datetime.now() - timedelta(days=7)
        print(f"No state found or invalid state for saynice.py, starting from {last_timestamp}")
        state = {'last_timestamp': last_timestamp.isoformat()}
    else:
        last_timestamp = datetime.fromisoformat(state['last_timestamp'])
        print(f"saynice.py: Last processed timestamp: {last_timestamp}")

    messages = shared_utils.get_recent_messages(shared_utils.DATABASE_PATH, CHAT_JID_STEPH, last_timestamp)

    if not messages:
        print("saynice.py: No new messages to process.")
        return

    print(f"saynice.py: Found {len(messages)} new messages.")

    latest_message_dt = shared_utils.get_latest_message_timestamp(messages)
    if not latest_message_dt:
        print("saynice.py: Could not determine latest message timestamp. Exiting.")
        return

    chat_history_text = shared_utils.format_messages_for_prompt(messages) # Uses default JID map in shared_utils

    llm_response = shared_utils.generate_llm_response(SAYNICE_PROMPT_TEMPLATE, chat_history_text)

    if llm_response and llm_response.get('success'):
        nice_message = llm_response.get('response_text')
        print("saynice.py: Generated Message:")
        print(nice_message)

        send_response = shared_utils.send_text_message(shared_utils.SEND_API_URL, TARGET_PHONE_NUMBER_JAMES, nice_message.strip())

        if send_response and send_response.get('success'):
            # Update state with latest timestamp, LLM details, and message details
            state['last_timestamp'] = latest_message_dt.isoformat()
            state['last_llm_call'] = llm_response.get('api_details')
            state['last_message_sent'] = send_response.get('message_details')
            shared_utils.save_state(STATE_FILE, state)
            print(f"saynice.py: State saved with latest timestamp: {latest_message_dt.isoformat()}")
        else:
            print("saynice.py: Failed to send nice message.")
            # Optionally save state with send failure details here
            # state['last_llm_call'] = llm_response.get('api_details')
            # state['last_message_send_attempt'] = send_response
            # shared_utils.save_state(STATE_FILE, state)
    else:
        print("saynice.py: Failed to generate a nice message.")
        # Optionally save state with LLM failure details here
        # state['last_llm_call_attempt'] = llm_response
        # shared_utils.save_state(STATE_FILE, state)

if __name__ == "__main__":
    main()
