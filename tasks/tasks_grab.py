#!.venv/bin/python
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
# 'https://www.googleapis.com/auth/tasks.readonly' is for viewing tasks.
# If you want to modify/add tasks, use 'https://www.googleapis.com/auth/tasks'.
SCOPES = ["https://www.googleapis.com/auth/tasks.readonly"]

def main():
    """Shows basic usage of the Google Tasks API.
    Lists the user's task lists and the tasks within each list.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Make sure you have 'credentials.json' in the same directory.
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("tasks", "v1", credentials=creds)

        # Call the Tasks API to list task lists
        print("Listing your Google Task Lists:")
        results = service.tasklists().list().execute()
        task_lists = results.get("items", [])

        if not task_lists:
            print("No task lists found.")
            return

        for task_list in task_lists:
            list_title = task_list["title"]
            list_id = task_list["id"]
            print(f"\n--- Task List: {list_title} (ID: {list_id}) ---")

            # Now, list tasks within this task list
            tasks_results = service.tasks().list(
                tasklist=list_id,
                showCompleted=False, # Set to True to see completed tasks
                showDeleted=False    # Set to True to see deleted tasks
            ).execute()
            tasks = tasks_results.get("items", [])

            if not tasks:
                print("  No tasks in this list.")
            else:
                for task in tasks:
                    status = "[COMPLETED]" if task.get("status") == "completed" else "[PENDING]"
                    due_date = task.get("due")
                    notes = task.get("notes")
                    
                    print(f"  {status} {task['title']}")
                    if due_date:
                        print(f"    Due: {due_date}")
                    if notes:
                        # Indent notes for readability
                        indented_notes = "\n".join(["    " + line for line in notes.splitlines()])
                        print(f"    Notes:\n{indented_notes}")


    except HttpError as err:
        print(f"An HTTP error occurred: {err}")
    except FileNotFoundError:
        print("Error: 'credentials.json' not found. Please ensure you've downloaded it "
              "from the Google Cloud Console and placed it in the same directory as this script.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
