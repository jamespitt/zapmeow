#!.venv/bin/python
import os
import re
import datetime
import requests
import argparse
from ics import Calendar, Event

def process_ical_url(url, target_date):
    response = requests.get(url)
    response.raise_for_status()  # Raise exception if the request failed


    calendar = Calendar(response.text)

    events_on_date = []

    for event in calendar.events:
        if event.begin.date() == target_date:
            start_time = event.begin.strftime(\'%H:%M\')
            end_time = event.end.strftime(\'%H:%M\')
            events_on_date.append(f\"- [ ] {start_time}->{end_time} 📅 {target_date} {event.name}\")

    return events_on_date

# Function to find tasks from .md files
def find_tasks():
    tasks = []
    for root, _, files in os.walk("."):
        for file in files:
            if file.endswith(".md"):
                filepath = os.path.join(root, file)
                with open(filepath, 'r') as f:
                    for line in f:
                        if re.search(r'\[ \].*📅 \d{4}-\d{2}-\d{2}', line):
                            tasks.append((line.strip()))
    return tasks



# Function to print tasks based on date comparison
def print_tasks(label, tasks_list):
    if tasks_list:
        print(label)
        sorted_tasks = sorted(tasks_list)
        print("\n".join(sorted_tasks))
        print("\n")

# Get all the tasks
all_tasks = find_tasks()

parser = argparse.ArgumentParser(description='List tasks and calendar events for a specific day.')
group = parser.add_mutually_exclusive_group(required=True)
group.add_argument('--today', action='store_true', help='Show tasks and events for today')
group.add_argument('--tomorrow', action='store_true', help='Show tasks and events for tomorrow')

args = parser.parse_args()

target_date = None
label = ""
if args.today:
    target_date = datetime.date.today()
    label = "Tasks For Today"
elif args.tomorrow:
    target_date = datetime.date.today() + datetime.timedelta(days=1)
    label = "Tasks For Tomorrow"

# Filter markdown tasks for the target date
filtered_tasks = []
for line in all_tasks:
    try:
        task_date_match = re.search(r'📅 (\d{4}-\d{2}-\d{2})', line)
        if task_date_match:
            task_date = datetime.datetime.strptime(task_date_match.group(1), '%Y-%m-%d').date()
            if task_date == target_date:
                filtered_tasks.append(line)
    except:
        print("problem with " + line)

# Get calendar events for the target date
calendar_events = process_ical_url('https://calendar.google.com/calendar/ical/james.pitt%40gmail.com/private-8ce4aa85a1e8db518cd27bc72abcb6a8/basic.ics', target_date)

# Combine and print tasks and events
all_items = filtered_tasks + calendar_events
print_tasks(label, all_items)


