#!../.venv/bin/python
import os.path
import argparse
from datetime import datetime, timedelta, timezone
import pytz # Added for timezone support
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Define the London timezone
LONDON_TZ = pytz.timezone('Europe/London')


# If modifying these scopes, delete the corresponding token_ACCOUNTNAME.json file.
SCOPES = [
    "https://www.googleapis.com/auth/tasks.readonly",
    "https://www.googleapis.com/auth/calendar.readonly"
]

# Configuration for filtering calendars and events
FILTER_CONFIG = {
    "james@ultro.co.uk": {
        "exclude_calendar": True,
    },
    "c_5t2luvnntili56cr8u63gdd770@group.calendar.google.com": {
        "exclude_calendar": True,
    },
    "jamespitt@google.com": {
        "show_today_tomorrow_only": True,
    },
    "google.com_61gbl7o40d6lqo2e2n7hktkkas@group.calendar.google.com": {
        "show_today_tomorrow_only": True,
    } # Mindmeld Prod oncall
}

# List of event summaries to exclude globally
EXCLUDE_EVENT_SUMMARIES = [
    "Break",
    "Create daily sheet",
    "Ryanair check-in now!!"
]

# List of task list IDs to exclude globally
EXCLUDE_TASK_LIST_IDS = [
    "aU02cjZvUzROaEdZYkdjVw", # Later task list
    "aktJQ3YwNXhxYzZ4VVU0RA" # Old Interesting Stuff
]

def parse_api_datetime(dt_str):
    """
    Parses a datetime string from the API (expected to be ISO format/UTC or date-only)
    and returns a datetime object localized to LONDON_TZ.
    Returns None if parsing fails.
    """
    if not dt_str:
        return None
    try:
        # Handle full datetime strings (e.g., "2023-10-26T10:00:00Z" or "2023-10-26T10:00:00+01:00")
        if 'T' in dt_str:
            parsed_dt_aware = None
            # datetime.fromisoformat handles 'Z' and offsets like +01:00 correctly in Python 3.7+
            # For 'Z', it's interpreted as UTC.
            if dt_str.endswith('Z'):
                # Ensure it's treated as UTC, fromisoformat should handle this.
                # Adding +00:00 for older Pythons or for explicit clarity if needed.
                parsed_dt_aware = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            else:
                parsed_dt_aware = datetime.fromisoformat(dt_str)

            if parsed_dt_aware.tzinfo is None:
                # If parsed_dt_aware is naive (e.g. from "YYYY-MM-DDTHH:MM:SS" without Z or offset)
                # we assume it's intended to be UTC as per common API practice.
                parsed_dt_aware = parsed_dt_aware.replace(tzinfo=timezone.utc)

            return parsed_dt_aware.astimezone(LONDON_TZ)
        else:
            # Handle date-only strings (e.g., "2023-10-26")
            # Interpret as midnight naive, then localize to LONDON_TZ
            dt_naive = datetime.strptime(dt_str, '%Y-%m-%d')
            return LONDON_TZ.localize(dt_naive)
    except ValueError:
        # print(f"Warning: Could not parse datetime string '{dt_str}' with expected formats. Returning None.")
        return None
    except Exception as e:
        # print(f"Error parsing or converting datetime string '{dt_str}': {e}. Returning None.")
        return None

def get_week_start_end():
    """Calculates the start (Monday) and end (Sunday) of the current week in LONDON_TZ."""
    today_london = datetime.now(LONDON_TZ)
    start_of_week = today_london - timedelta(days=today_london.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    return start_of_week.replace(hour=0, minute=0, second=0, microsecond=0), \
           end_of_week.replace(hour=23, minute=59, second=59, microsecond=999999)

def get_today_start_end():
    """Calculates the start and end of the current day in LONDON_TZ."""
    today_london = datetime.now(LONDON_TZ)
    return today_london.replace(hour=0, minute=0, second=0, microsecond=0), \
           today_london.replace(hour=23, minute=59, second=59, microsecond=999999)

def get_tomorrow_start_end():
    """Calculates the start and end of tomorrow in LONDON_TZ."""
    tomorrow_london = datetime.now(LONDON_TZ) + timedelta(days=1)
    return tomorrow_london.replace(hour=0, minute=0, second=0, microsecond=0), \
           tomorrow_london.replace(hour=23, minute=59, second=59, microsecond=999999)

def authenticate_and_build_services(account_name):
    """Handles authentication and builds Google API services for a given account."""
    token_file = f"token_{account_name}.json"
    creds = None

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            print(f"\n--- Authenticating for {account_name} account ---")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)
            except FileNotFoundError:
                print("Error: 'credentials.json' not found. Please ensure you've downloaded it "
                      "from the Google Cloud Console and placed it in the same directory as this script.")
                return None, None, False # Indicate failure
            except Exception as e:
                print(f"Error during authentication for {account_name}: {e}")
                return None, None, False # Indicate failure
        
        with open(token_file, "w") as token:
            token.write(creds.to_json())
            print(f"Authentication token saved to {token_file}")

    if creds:
        try:
            tasks_service = build("tasks", "v1", credentials=creds)
            calendar_service = build("calendar", "v3", credentials=creds)
            return tasks_service, calendar_service, True # Indicate success
        except Exception as e:
            print(f"Error building services for {account_name}: {e}")
            return None, None, False # Indicate failure
    return None, None, False # Should not be reached if creds are valid

def fetch_tasks(tasks_service, time_min=None, time_max=None, apply_filter=False):
    """Fetches tasks, applying filters and date range."""
    filtered_task_lists = []
    try:
        task_lists_results = tasks_service.tasklists().list().execute()
        task_lists = task_lists_results.get("items", [])

        if task_lists:
            for task_list in task_lists:
                list_id = task_list["id"]

                # Filter out task lists if apply_filter is True and list_id is in EXCLUDE_TASK_LIST_IDS
                if apply_filter and list_id in EXCLUDE_TASK_LIST_IDS:
                    continue # Skip this task list

                tasks_results = tasks_service.tasks().list(
                    tasklist=list_id,
                    showCompleted=False,
                    showDeleted=False
                ).execute()
                tasks = tasks_results.get("items", [])

                # Filter tasks by due date if time_min and time_max are provided
                if time_min and time_max:
                    filtered_tasks = []
                    for task in tasks:
                        due_date_str = task.get("due")
                        task_due_london = parse_api_datetime(due_date_str) if due_date_str else None
                        if task_due_london and time_min <= task_due_london <= time_max:
                            filtered_tasks.append(task)
                        elif not due_date_str: # Include tasks without a due date if no time filter or they fit other criteria
                            filtered_tasks.append(task) # This line might need adjustment based on desired behavior for tasks without due dates when filtering
                    tasks = filtered_tasks

                if tasks:
                    filtered_task_lists.append({
                        "title": task_list["title"],
                        "id": list_id,
                        "items": tasks
                    })
    except HttpError as err:
        print(f"  Error fetching tasks: {err}")
    except Exception as e:
        print(f"  An unexpected error occurred fetching tasks: {e}")

    return filtered_task_lists

def fetch_calendars(calendar_service, account_name, apply_filter=False, personal_only=False):
    """Fetches calendars, applying filters."""
    filtered_calendars = []
    try:
        calendar_list_results = calendar_service.calendarList().list().execute()
        calendars = calendar_list_results.get('items', [])

        for calendar in calendars:
            calendar_id = calendar['id']
            access_role = calendar.get('accessRole')

            if access_role in ['owner', 'writer', 'reader']:
                # Calendar exclusion filter
                calendar_filter_config = FILTER_CONFIG.get(calendar_id, {})
                if apply_filter and calendar_filter_config.get("exclude_calendar"):
                    continue # Skip excluded calendars

                # Personal only filter (based on account name)
                if personal_only and account_name != "personal":
                     continue

                filtered_calendars.append(calendar)

    except HttpError as err:
        print(f"  Error fetching calendar list for {account_name}: {err}")
    except Exception as e:
        print(f"  An unexpected error occurred fetching calendar data for {account_name}: {e}")

    return filtered_calendars

def fetch_calendar_events(calendar_service, calendar_id, time_min, time_max, apply_filter=False):
    """Fetches events for a single calendar within a date range, applying summary filters."""
    # API expects UTC time strings
    time_min_utc = time_min.astimezone(timezone.utc)
    time_max_utc = time_max.astimezone(timezone.utc)

    try:
        events_result = calendar_service.events().list(
            calendarId=calendar_id,
            timeMin=time_min_utc.isoformat(),
            timeMax=time_max_utc.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        # Filter events by summary
        if apply_filter and EXCLUDE_EVENT_SUMMARIES:
            events = [event for event in events if event.get('summary') not in EXCLUDE_EVENT_SUMMARIES]

        return events

    except HttpError as err:
        print(f"    Error fetching events for calendar {calendar_id}: {err}")
        return []
    except Exception as e:
        print(f"  An unexpected error occurred fetching calendar data for {calendar_id}: {e}")
        return []

def display_tasks(tasks_data):
    """Displays tasks."""
    if tasks_data:
        print("\nTasks:")
        for task_list in tasks_data:
            print(f"  Task List: {task_list['title']}")
            if task_list.get('items'):
                for task in task_list['items']:
                    status = "[COMPLETED]" if task.get("status") == "completed" else "[PENDING]"
                    task_title = task['title']
                    due_date_str = task.get('due')
                    due_date_display = ""
                    task_due_london = parse_api_datetime(due_date_str) if due_date_str else None
                    if task_due_london:
                        due_date_display = f" (Due: {task_due_london.strftime('%a %Y-%m-%d %H:%M')})"
                    elif due_date_str: # If parsing failed but string existed
                            due_date_display = f" (Malformed due date: {due_date_str})"
                    print(f"    {status} {task_title}{due_date_display}")
            else:
                print("      No tasks in this list.")
    else:
        print("\nNo tasks found.")

def display_events(calendars_with_events):
    """Displays events grouped by calendar."""
    if calendars_with_events:
        print("\nEvents:")
        for calendar_data in calendars_with_events:
            calendar = calendar_data['calendar']
            events = calendar_data['events']
            print(f"  Calendar: {calendar.get('summary', 'No Title')}")
            for event in events:
                summary = event.get('summary', 'No Title')
                start_str = event['start'].get('dateTime', event['start'].get('date'))
                end_str = event['end'].get('dateTime', event['end'].get('date'))
                time_str = ""
                start_dt_london = parse_api_datetime(start_str)
                end_dt_london = parse_api_datetime(end_str)

                if start_dt_london:
                    if 'T' in start_str: # Timed event
                        time_str = f"{start_dt_london.strftime('%a %Y-%m-%d %H:%M')} to {end_dt_london.strftime('%H:%M') if end_dt_london else '?'}"
                    else: # All-day event
                        time_str = f"{start_dt_london.strftime('%a %Y-%m-%d')} (All Day)"
                else:
                    time_str = f"Malformed date/time: {start_str}"
                print(f"    • {summary} ({time_str})")
    else:
        print("\nNo events found.")

def display_tasks_and_events_today(tasks_data, events_data):
    """Displays today's tasks and events, sorted by time, removing duplicates."""
    combined_items = []
    seen_ids = set()

    for task_list in tasks_data:
        for task in task_list.get('items', []):
            task_id = task.get('id')
            if task_id and task_id in seen_ids:
                continue
            seen_ids.add(task_id)

            task_due_london = parse_api_datetime(task.get('due'))
            if task_due_london:
                combined_items.append((task_due_london, task, "task"))
            else:
                # Sort tasks with no due date or malformed dates at the end, using London TZ for consistency
                combined_items.append((datetime.max.replace(tzinfo=LONDON_TZ), task, "task"))

    for event in events_data:
        event_id = event.get('id')
        if event_id and event_id in seen_ids:
            continue
        seen_ids.add(event_id)

        start_str = event['start'].get('dateTime', event['start'].get('date'))
        event_start_london = parse_api_datetime(start_str)
        if event_start_london:
            combined_items.append((event_start_london, event, "event"))
        else:
            combined_items.append((datetime.max.replace(tzinfo=LONDON_TZ), event, "event"))

    combined_items.sort(key=lambda x: x[0])

    if combined_items:
        for item_time, item, item_type in combined_items:
            if item_type == "task":
                status = "[COMPLETED]" if item.get("status") == "completed" else "[PENDING]"
                task_title = item['title']
                due_date_str = item.get('due')
                due_date_display = ""
                # item_time is already the parsed London time for tasks with valid due dates
                if item_time != datetime.max.replace(tzinfo=LONDON_TZ) and due_date_str: # Check it's not the fallback
                    due_date_display = f" (Due: {item_time.strftime('%a %Y-%m-%d %H:%M')})"
                elif due_date_str: # Malformed original date string
                        due_date_display = f" (Malformed due date: {due_date_str})"
                print(f"    {status} {task_title}{due_date_display}")

            elif item_type == "event":
                summary = item.get('summary', 'No Title')
                start_str = item['start'].get('dateTime', item['start'].get('date'))
                end_str = item['end'].get('dateTime', item['end'].get('date'))
                time_str = ""
                # item_time is already the parsed London start time for events
                if item_time != datetime.max.replace(tzinfo=LONDON_TZ) and start_str:
                    end_dt_london = parse_api_datetime(end_str)
                    if 'T' in start_str: # Timed event
                        time_str = f"{item_time.strftime('%a %Y-%m-%d %H:%M')} to {end_dt_london.strftime('%H:%M') if end_dt_london else '?'}"
                    else: # All-day event
                        time_str = f"{item_time.strftime('%a %Y-%m-%d')} (All Day)"
                else: # Malformed original date string
                    time_str = f"Malformed date/time: {start_str}"
                print(f"    • {summary} ({time_str})")
    else:
        print("No events or tasks found for today.")


def display_combined_items(tasks_data, events_data):
    """Displays tasks and events, sorted by time, removing duplicates."""
    combined_items = []
    seen_ids = set()

    for task_list in tasks_data:
        for task in task_list.get('items', []):
            task_id = task.get('id')
            if task_id and task_id in seen_ids:
                continue
            seen_ids.add(task_id)

            task_due_london = parse_api_datetime(task.get('due'))
            if task_due_london:
                combined_items.append((task_due_london, task, "task"))
            else:
                # Sort tasks with no due date or malformed dates at the end
                combined_items.append((datetime.max.replace(tzinfo=LONDON_TZ), task, "task"))

    for event in events_data:
        event_id = event.get('id')
        if event_id and event_id in seen_ids:
            continue
        seen_ids.add(event_id)

        start_str = event['start'].get('dateTime', event['start'].get('date'))
        event_start_london = parse_api_datetime(start_str)
        if event_start_london:
            combined_items.append((event_start_london, event, "event"))
        else:
            combined_items.append((datetime.max.replace(tzinfo=LONDON_TZ), event, "event"))

    combined_items.sort(key=lambda x: x[0])

    if combined_items:
        for item_time, item, item_type in combined_items:
            if item_type == "task":
                status = "[COMPLETED]" if item.get("status") == "completed" else "[PENDING]"
                task_title = item['title']
                due_date_str = item.get('due')
                due_date_display = ""
                if item_time != datetime.max.replace(tzinfo=LONDON_TZ) and due_date_str:
                    due_date_display = f" (Due: {item_time.strftime('%a %Y-%m-%d %H:%M')})"
                elif due_date_str:
                        due_date_display = f" (Malformed due date: {due_date_str})"
                print(f"    {status} {task_title}{due_date_display}")

            elif item_type == "event":
                summary = item.get('summary', 'No Title')
                start_str = item['start'].get('dateTime', item['start'].get('date'))
                end_str = item['end'].get('dateTime', item['end'].get('date'))
                time_str = ""
                if item_time != datetime.max.replace(tzinfo=LONDON_TZ) and start_str:
                    end_dt_london = parse_api_datetime(end_str)
                    if 'T' in start_str: # Timed event
                        time_str = f"{item_time.strftime('%a %Y-%m-%d %H:%M')} to {end_dt_london.strftime('%H:%M') if end_dt_london else '?'}"
                    else: # All-day event
                        time_str = f"{item_time.strftime('%a %Y-%m-%d')} (All Day)"
                else:
                    time_str = f"Malformed date/time: {start_str}"
                print(f"    • {summary} ({time_str})")
    else:
        print("No events or tasks found.")

def display_obsidian_format(tasks_data, events_data):
    """Displays tasks and events in Obsidian table format for a given period."""
    combined_items = []
    seen_ids = set()

    # Combine tasks and events, similar to display_tasks_and_events_today
    for task_list in tasks_data:
        for task in task_list.get('items', []):
            task_id = task.get('id')
            if task_id and task_id in seen_ids:
                continue
            seen_ids.add(task_id)

            task_due_london = parse_api_datetime(task.get('due'))
            if task_due_london:
                combined_items.append((task_due_london, task, "task"))
            else:
                combined_items.append((datetime.max.replace(tzinfo=LONDON_TZ), task, "task"))

    for event in events_data:
        event_id = event.get('id')
        if event_id and event_id in seen_ids:
            continue
        seen_ids.add(event_id)
        start_str = event['start'].get('dateTime', event['start'].get('date'))
        event_start_london = parse_api_datetime(start_str)
        if event_start_london:
            combined_items.append((event_start_london, event, "event"))
        else:
            combined_items.append((datetime.max.replace(tzinfo=LONDON_TZ), event, "event"))

    combined_items.sort(key=lambda x: x[0])

    print("| Time | Type | Title | Status |")
    print("|---|---|---|---|")

    if combined_items:
        for item_time_london, item, item_type in combined_items: # item_time_london is already parsed London time
            time_str = ""
            title = ""
            status = ""

            if item_type == "task":
                status = "[COMPLETED]" if item.get("status") == "completed" else "[PENDING]"
                title = item['title']
                # Default time_str for tasks that don't meet other conditions
                time_str = "No Due Date"

                if item_time_london != datetime.max.replace(tzinfo=LONDON_TZ) and item.get('due'):
                    # Valid due date string was parsed successfully
                    time_str = item_time_london.strftime('%H:%M') # Just time for tasks with due time
                elif item.get('due'): # Original due date string exists but wasn't parsed into item_time_london (i.e., it was malformed)
                    time_str = "Malformed Date"
                # else: time_str remains "No Due Date" (task has no 'due' field or it was empty/unparseable to a specific time)

                if time_str == "No Due Date":
                    continue # Skip printing this task
            elif item_type == "event":
                title = item.get('summary', 'No Title')
                start_str = item['start'].get('dateTime', item['start'].get('date'))
                end_str = item['end'].get('dateTime', item['end'].get('date'))
                if item_time_london != datetime.max.replace(tzinfo=LONDON_TZ) and start_str:
                    end_dt_london = parse_api_datetime(end_str)
                    if 'T' in start_str: # Timed event
                        time_str = f"{item_time_london.strftime('%H:%M')} - {end_dt_london.strftime('%H:%M') if end_dt_london else '?'}"
                    else: # All-day event
                        time_str = "All Day"
                elif start_str: # Malformed original date
                    time_str = "Malformed Time"

            print(f"| {time_str} | {item_type.capitalize()} | {title} | {status} |")
    else:
        print("| No events or tasks found for today. |||")


def parse_arguments():
    """Parses command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch and display Google Tasks and Calendar events for specified accounts."
    )
    parser.add_argument(
        "--personal", action="store_true", help="Process data for the personal account."
    )
    parser.add_argument(
        "--work", action="store_true", help="Process data for the work account."
    )
    parser.add_argument(
        "--all", action="store_true", help="Process data for all accounts (personal and work)."
    )
    parser.add_argument(
        "--all-with-filter", action="store_true", help="Process data for all accounts with filtering applied."
    )
    parser.add_argument(
        "--today", action="store_true", help="Show only today's events and tasks."
    )
    parser.add_argument(
        "--personal-week", action="store_true", help="Show only personal events and tasks for the week."
    )
    \
    parser.add_argument(
        "--tomorrow", action="store_true", help="Show only tomorrow\'s events and tasks."
    )
    # parser.add_argument(
    #     "--obsidian-today", action="store_true", help="Produce an overview of the day in Obsidian table format."
    # )
    parser.add_argument(
        "--obsidian", action="store_true", help="Produce an overview in Obsidian table format for the specified or default date (today)."
    )
    parser.add_argument("--date", type=str, help="Specify the date for data retrieval in YYYY-MM-DD format. Overrides --today, --tomorrow for data fetching range.")
    return parser.parse_args()

def get_specific_date_start_end(target_date_obj):
    """Calculates the start and end of a specific date in LONDON_TZ.
    target_date_obj is a datetime.date object.
    """
    start_of_day_naive = datetime.combine(target_date_obj, datetime.min.time())
    end_of_day_naive = datetime.combine(target_date_obj, datetime.max.time())
    return LONDON_TZ.localize(start_of_day_naive), LONDON_TZ.localize(end_of_day_naive)

def process_account_data(account_name, args, fetch_time_min_overall, fetch_time_max_overall):
    """Authenticates and fetches data for a single account."""
    tasks_service, calendar_service, auth_success = authenticate_and_build_services(account_name)

    if not auth_success:
        print(f"\nSkipping {account_name} account due to authentication/service build error.")
        return None, None # Return None for both tasks and events data

    account_tasks = []
    account_calendars_with_events = []

    apply_filter = args.all_with_filter or args.today or args.personal_week or args.tomorrow or bool(args.date) or args.obsidian

    # Determine time range based on arguments
    # The primary time range is now passed directly as fetch_time_min_overall, fetch_time_max_overall
    time_min_for_tasks = fetch_time_min_overall
    time_max_for_tasks = fetch_time_max_overall


    # Fetch tasks
    account_tasks = fetch_tasks(tasks_service, time_min=time_min_for_tasks, time_max=time_max_for_tasks, apply_filter=apply_filter)

    # Fetch calendars and events
    personal_only = args.personal_week and account_name == "personal"
    account_calendars = fetch_calendars(calendar_service, account_name, apply_filter=apply_filter, personal_only=personal_only)

    for calendar in account_calendars:
        calendar_id = calendar['id']
        calendar_filter_config = FILTER_CONFIG.get(calendar_id, {})

        # Determine the event fetch window for this specific calendar
        event_fetch_min_for_calendar = fetch_time_min_overall
        event_fetch_max_for_calendar = fetch_time_max_overall

        if apply_filter and calendar_filter_config.get("show_today_tomorrow_only"):
            # This filter means "for this calendar, only show today/tomorrow events"
            # We need today's and tomorrow's actual start/end.
            _today_start_cal, _ = get_today_start_end()
            _, _tomorrow_end_cal = get_tomorrow_start_end() # tomorrow_start_end returns start and end of tomorrow

            # The desired range for this calendar due to the filter is today_start to tomorrow_end
            filter_specific_min = _today_start_cal
            filter_specific_max = _tomorrow_end_cal

            # The actual fetch range is the intersection of the overall fetch range
            # and this filter-specific range.
            event_fetch_min_for_calendar = max(fetch_time_min_overall, filter_specific_min)
            event_fetch_max_for_calendar = min(fetch_time_max_overall, filter_specific_max)

        # If the resulting range is invalid (min > max), no events will be fetched.
        if event_fetch_min_for_calendar <= event_fetch_max_for_calendar:
            events = fetch_calendar_events(calendar_service, calendar_id, event_fetch_min_for_calendar, event_fetch_max_for_calendar, apply_filter=apply_filter)
        else:
            events = [] # No valid time range to fetch

        if events:
            account_calendars_with_events.append({"calendar": calendar, "events": events})

    return account_tasks, account_calendars_with_events

def display_data(args, personal_data, work_data, fetch_date_start, fetch_date_end, display_label_date_str):
    """Displays the fetched data based on command-line arguments."""
    all_tasks = personal_data.get("tasks", []) + work_data.get("tasks", [])
    is_single_day_view = (fetch_date_start.date() == fetch_date_end.date())

    all_events_flat = []
    if is_single_day_view:
        # For single day views, events are already flattened per account
        all_events_flat = personal_data.get("events", []) + work_data.get("events", [])
    else:
        # For multi-day views (like week), flatten events from all calendars
        for cal_data in personal_data.get("calendars_with_events", []) + work_data.get("calendars_with_events", []):
            all_events_flat.extend(cal_data.get("events", []))

    if args.obsidian:
        print(f"\n========================================================")
        print(f"  Obsidian Overview for {display_label_date_str}")
        print(f"========================================================")
        display_obsidian_format(all_tasks, all_events_flat)

    elif is_single_day_view: # Handles --date, --today, --tomorrow without --obsidian
        print(f"\n========================================================")
        print(f"  Overview for {display_label_date_str}")
        print(f"========================================================")
        display_tasks_and_events_today(all_tasks, all_events_flat) # This function combines and sorts

    elif args.personal_week:
        print(f"\n========================================================")
        print(f"  Displaying Personal Data for {display_label_date_str}")
        print(f"========================================================")
        # For personal_week, we expect data to be filtered to personal account already if only --personal-week
        # If used with --all, it will show all. The display_combined_items is for sorted view.
        # If we want separate display_tasks and display_events:
        if personal_data: # Assuming personal_week implies focusing on personal_data if available
            display_tasks(personal_data.get("tasks", []))
            display_events(personal_data.get("calendars_with_events", []))
        else: # Fallback if personal_data is empty but personal_week was with e.g. --all
            display_tasks(all_tasks) # all_tasks would be from both if --all was also used
            all_calendars_with_events = personal_data.get("calendars_with_events", []) + work_data.get("calendars_with_events", [])
            display_events(all_calendars_with_events)

    elif args.all_with_filter:
        print(f"\n========================================================")
        print(f"  Displaying Filtered Data")
        print(f"========================================================")
        print(f"Data for {display_label_date_str}")
        all_calendars_with_events = personal_data.get("calendars_with_events", []) + work_data.get("calendars_with_events", [])
        display_tasks(all_tasks)
        display_events(all_calendars_with_events)


    elif args.all:
         print(f"\n========================================================")
         print(f"  Displaying All Data")
         print(f"========================================================")
         print(f"Data for {display_label_date_str}")
         all_calendars_with_events = personal_data.get("calendars_with_events", []) + work_data.get("calendars_with_events", [])
         display_tasks(all_tasks)
         display_events(all_calendars_with_events)

    elif args.personal:
        print(f"\n========================================================")
        print(f"  Displaying Personal Data")
        print(f"========================================================")
        print(f"Data for {display_label_date_str}")
        if personal_data:
            display_tasks(personal_data.get("tasks", []))
            display_events(personal_data.get("calendars_with_events", []))
        else:
            print("Personal account data not available.")

    elif args.work:
        print(f"\n========================================================")
        print(f"  Displaying Work Data")
        print(f"========================================================")
        print(f"Data for {display_label_date_str}")
        if work_data:
            display_tasks(work_data.get("tasks", []))
            display_events(work_data.get("calendars_with_events", []))
        else:
            print("Work account data not available.")


if __name__ == "__main__":
    args = parse_arguments()
    parser_for_help = argparse.ArgumentParser() # Keep a parser instance for help

    # Determine the primary date range for fetching data and a display label
    fetch_date_start, fetch_date_end = None, None
    display_label_date_str = ""

    if args.date:
        try:
            target_date_obj = datetime.strptime(args.date, "%Y-%m-%d").date()
            fetch_date_start, fetch_date_end = get_specific_date_start_end(target_date_obj)
            display_label_date_str = f"Date: {args.date}"
        except ValueError:
            print(f"Error: Invalid date format for --date: '{args.date}'. Please use YYYY-MM-DD.")
            # Recreate parser to print its help, as the original script does for no args
            temp_parser = parse_arguments.__globals__['argparse'].ArgumentParser(description="Fetch and display Google Tasks and Calendar events...")
            # Manually add arguments to temp_parser if needed for full help, or use a global parser instance
            # For simplicity, just print a message and exit.
            print("Use --help for more information.")
            exit(1)
    elif args.today:
        fetch_date_start, fetch_date_end = get_today_start_end()
        display_label_date_str = f"Today: {fetch_date_start.strftime('%Y-%m-%d')}"
    elif args.tomorrow:
        fetch_date_start, fetch_date_end = get_tomorrow_start_end()
        display_label_date_str = f"Tomorrow: {fetch_date_start.strftime('%Y-%m-%d')}"
    elif args.obsidian: # If --obsidian is present and no other specific date is set, default to today
        fetch_date_start, fetch_date_end = get_today_start_end()
        display_label_date_str = f"Today (for Obsidian): {fetch_date_start.strftime('%Y-%m-%d')}"
    elif args.personal_week:
        fetch_date_start, fetch_date_end = get_week_start_end()
        display_label_date_str = f"Week: {fetch_date_start.strftime('%Y-%m-%d')} to {fetch_date_end.strftime('%Y-%m-%d')}"
    else: # Default for --all, --personal, --work if no specific date/day/week is given
        fetch_date_start, fetch_date_end = get_week_start_end()
        display_label_date_str = f"Week: {fetch_date_start.strftime('%Y-%m-%d')} to {fetch_date_end.strftime('%Y-%m-%d')}"

    # Determine if any processing should occur
    should_process_any = args.personal or args.work or args.all or \
                         args.all_with_filter or args.today or \
                         args.personal_week or args.obsidian or args.date or args.tomorrow

    if not should_process_any:
        # Recreate parser to print its help, as the original script does
        # This is a bit of a workaround. Ideally, parse_arguments() would return the parser.
        temp_parser_desc = "Fetch and display Google Tasks and Calendar events for specified accounts."
        temp_parser = argparse.ArgumentParser(description=temp_parser_desc)
        # Re-add arguments to this temporary parser to get full help text
        # This is cumbersome. A better approach is to have parse_arguments return the parser object.
        # For now, let's just print a generic message.
        print("Please specify at least one processing option (e.g., --personal, --work, --all, --today, --date YYYY-MM-DD, --obsidian).")
        print("Use --help for more information.")
        exit(1)

    process_personal = args.personal or args.all or args.all_with_filter or args.today or args.personal_week or args.obsidian or bool(args.date) or args.tomorrow
    process_work = args.work or args.all or args.all_with_filter or args.today or args.obsidian or bool(args.date) or args.tomorrow

    personal_data = {}
    work_data = {}

    if process_personal:
        personal_tasks, personal_calendars_with_events = process_account_data("personal", args, fetch_date_start, fetch_date_end)
        if personal_tasks is not None: # Check if processing was successful
            personal_data["tasks"] = personal_tasks
            personal_data["calendars_with_events"] = personal_calendars_with_events
            if fetch_date_start.date() == fetch_date_end.date(): # Single day view
                 personal_data["events"] = [event for cal_data in personal_calendars_with_events for event in cal_data.get("events", [])]


    if process_work:
        work_tasks, work_calendars_with_events = process_account_data("work", args, fetch_date_start, fetch_date_end)
        if work_tasks is not None: # Check if processing was successful
            work_data["tasks"] = work_tasks
            work_data["calendars_with_events"] = work_calendars_with_events
            if fetch_date_start.date() == fetch_date_end.date(): # Single day view
                 work_data["events"] = [event for cal_data in work_calendars_with_events for event in cal_data.get("events", [])]

    display_data(args, personal_data, work_data, fetch_date_start, fetch_date_end, display_label_date_str)
