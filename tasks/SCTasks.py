#!/home/james/src/james_notes/tasks/.venv/bin/python
import sqlite3
import json
import requests
import ollama # Import the ollama library
import os

# --- Configuration ---
DB_PATH = '/home/james/.zapmeow/zapmeow.db'
API_URL = 'http://localhost:8900/api/1/chat/send/text'
PHONE_NUMBER = '447906616842' # This is the hardcoded phone number from your curl command
OLLAMA_MODEL = 'GetTasks' # The Ollama model you want to use

def main():
    try:
        # 1. Database query and initial processing
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        query = "SELECT timestamp, sender_jid, body FROM messages WHERE timestamp >= datetime('now', '-24 hours') AND chat_jid ='447709487896'"
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        # Join rows with '¬' similar to `tr '\n' '¬'`
        raw_db_data = '\n'.join([' '.join(map(str, row)) for row in rows])

        # 2. String replacements
        processed_db_data = raw_db_data.replace('447709487896', 'Steph').replace('447906616842', 'James')

        # 3. Call Ollama using the ollama-python library, requesting JSON format
        print(f"Calling Ollama model '{OLLAMA_MODEL}' with input data (requesting JSON output)...")
        
        # Ensure ollama_input_data is defined; likely intended to be processed_db_data
        ollama_input_data = processed_db_data

        ollama_response = ollama.chat(
            model=OLLAMA_MODEL,
            messages=[
                {'role': 'user', 'content': ollama_input_data}
            ],
            format='json' # <-- This is the key addition to force JSON output
        )

        # The 'content' field should now contain a JSON string
        ollama_output_str = ollama_response['message']['content'] 

        print("Ollama model responded with JSON output. Processing...")

        # 4. Process Ollama output
        extracted_task_descriptions = []
        text_for_api = ""
        chat_summary_from_model = "No summary provided."

        try:
            # Since we requested JSON, we expect ollama_output_str to be valid JSON
            ollama_output_json = json.loads(ollama_output_str)

            if "chat_summary" in ollama_output_json:
                chat_summary_from_model = ollama_output_json["chat_summary"]
                print(f"\nChat Summary from Model: {chat_summary_from_model}")

            if "items" in ollama_output_json and isinstance(ollama_output_json["items"], list):
                for item in ollama_output_json["items"]:
                    # Check if it's a task and has a description
                    if item.get("is_task") is True and "description" in item:
                        description = item["description"]
                        # Filter out descriptions containing backticks
                        if '`' not in description:
                            extracted_task_descriptions.append(description)
            else:
                print("No 'items' array found in Ollama output or it's not a list.")

            text_for_api = '\n'.join(extracted_task_descriptions)

        except json.JSONDecodeError:
            print(f"Error: Ollama model did not return valid JSON despite 'format=\"json\"' flag.")
            print(f"Problematic output:\n{ollama_output_str[:500]}...") # Print partial output for debugging
        except Exception as e:
            print(f"Error processing Ollama output JSON: {e}")

        print("\nExtracted Tasks for API:")
        print(text_for_api if text_for_api else "(No tasks extracted or an error occurred)")

        # 5. Send POST request
        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json',
        }
        
        payload = {
            'phone': PHONE_NUMBER,
            'text': text_for_api
        }

        print(f"\nSending POST request to {API_URL} with payload: {json.dumps(payload, indent=2)}")
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        
        print(f"\nAPI Response Status: {response.status_code}")
        print(f"API Response Body: {response.json()}")

    except FileNotFoundError as e:
        print(f"Error: A required file was not found - {e}")
        print(f"Please ensure the database file exists at {DB_PATH}.")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except ollama.ResponseError as e:
        print(f"Ollama API error: {e}")
        print(f"Please ensure the Ollama server is running and '{OLLAMA_MODEL}' model is available.")
    except requests.exceptions.RequestException as e:
        print(f"HTTP request error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == '__main__':
    main()
