#!.venv/bin/python
import requests
import icalendar
from datetime import date, datetime, timedelta
from dateutil.rrule import rruleset, rrule
from oauth2client.service_account import ServiceAccountCredentials

# --- Google Calendar API Setup (replace placeholders) ---
CALENDAR_ID = 'james.pitt%40gmail.com@group.calendar.google.com'
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
SERVICE_ACCOUNT_FILE = 'client_secret.json'  # Your credentials file

# --- Authentication ---
credentials = ServiceAccountCredentials.from_json_keyfile_name(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)
http = credentials.authorize(httplib2.Http())
service = discovery.build('calendar', 'v3', http=http)

# --- Download the ICS file ---
url = f'https://www.googleapis.com/calendar/v3/calendars/{CALENDAR_ID}/events/ical'
response = requests.get(url)

if response.status_code == 200:
    ics_content = response.text
else:
    print("Failed to download ICS file.")
    exit()

# --- Parse the ICS file ---
gcal = icalendar.Calendar.from_ical(ics_content)

# --- Get events for today ---
today = date.today()
today_start = datetime.combine(today, datetime.min.time())
today_end = datetime.combine(today, datetime.max.time())

todays_events = []
for component in gcal.walk():
    if component.name == "VEVENT":
        dtstart = component.get('DTSTART').dt
        dtend = component.get('DTEND').dt
        summary = component.get('SUMMARY')

        # Check for recurring events 
        if component.get('RRULE'):
            # Create a set of dates based on the recurrence rule
            rset = rruleset()
            rset.rrule(component.get('RRULE')) 
            event_dates = rset.between(today_start - timedelta(days=30), today_end) 

            # If any date matches today, add the event
            if any(event_date.date() == today for event_date in event_dates):
                todays_events.append({
                    'start': dtstart,
                    'end': dtend,
                    'summary': summary
                })
        # Handle non-recurring events
        elif today_start <= dtstart < today_end:
            todays_events.append({
                'start': dtstart,
                'end': dtend,
                'summary': summary
            })
            
# --- Print today's events ---
if todays_events:
    print("Today's Events:")
    for event in todays_events:
        print(f"- {event['summary']} ({event['start'].astimezone().strftime('%H:%M')} - {event['end'].astimezone().strftime('%H:%M')})")
else:
    print("No events found for today.")
