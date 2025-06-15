import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
import sys
import io

# Import functions from the script
from calender_and_tasks_grab import (
    get_week_start_end,
    get_today_start_end,
    parse_api_datetime,
    get_tomorrow_start_end,
    get_specific_date_start_end,
    display_tasks,
    display_events,
    display_tasks_and_events_today,
    display_obsidian_format,
    display_data, # For testing the main display logic
    parse_arguments, # To mock command line arguments
    authenticate_and_build_services,
    fetch_tasks,
    fetch_calendars,
    fetch_calendar_events,
    process_account_data, # To mock data fetching
    FILTER_CONFIG,
    EXCLUDE_EVENT_SUMMARIES,
    EXCLUDE_TASK_LIST_IDS,
)

class TestCalendarAndTasksGrab(unittest.TestCase):

    def setUp(self):
        # Store real datetime and timezone for use in mocks
        self.real_datetime = datetime
        self.real_timezone = timezone
        self.real_timedelta = timedelta

        # Mock datetime module
        self.mock_datetime_patcher = patch('calender_and_tasks_grab.datetime')
        self.mock_datetime = self.mock_datetime_patcher.start()

        # Configure the mock_datetime object to behave like the real one for most operations
        self.mock_datetime.now = MagicMock(return_value=self.real_datetime(2025, 6, 4, 10, 0, 0, tzinfo=self.real_timezone.utc)) # Wednesday
        self.mock_datetime.fromisoformat = self.real_datetime.fromisoformat
        self.mock_datetime.strptime = self.real_datetime.strptime
        self.mock_datetime.combine = self.real_datetime.combine
        self.mock_datetime.min = self.real_datetime.min
        self.mock_datetime.max = self.real_datetime.max
        self.mock_datetime.timedelta = self.real_timedelta # Use real timedelta
        self.mock_datetime.timezone = self.real_timezone # Use real timezone
        self.addCleanup(self.mock_datetime_patcher.stop)

        # Mock sys.stdout
        self.mock_stdout_patcher = patch('sys.stdout', new_callable=io.StringIO)
        self.mock_stdout = self.mock_stdout_patcher.start()
        self.addCleanup(self.mock_stdout_patcher.stop)

    def test_get_week_start_end(self):
        # self.mock_datetime.now is already mocked in setUp to June 4, 2025 (Wednesday)
        start, end = get_week_start_end()

        expected_start = self.real_datetime(2025, 6, 2, 0, 0, 0, 0, tzinfo=self.real_timezone.utc) # Monday
        expected_end = self.real_datetime(2025, 6, 8, 23, 59, 59, 999999, tzinfo=self.real_timezone.utc) # Sunday

        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)

    def test_get_today_start_end(self):
        start, end = get_today_start_end()
        expected_start = self.real_datetime(2025, 6, 4, 0, 0, 0, 0, tzinfo=self.real_timezone.utc)
        expected_end = self.real_datetime(2025, 6, 4, 23, 59, 59, 999999, tzinfo=self.real_timezone.utc)
        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)

    def test_get_tomorrow_start_end(self):
        start, end = get_tomorrow_start_end()
        expected_start = self.real_datetime(2025, 6, 5, 0, 0, 0, 0, tzinfo=self.real_timezone.utc)
        expected_end = self.real_datetime(2025, 6, 5, 23, 59, 59, 999999, tzinfo=self.real_timezone.utc)
        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)

    def test_get_specific_date_start_end(self):
        target_date_obj = self.real_datetime(2025, 7, 15).date()
        start, end = get_specific_date_start_end(target_date_obj)
        expected_start = self.real_datetime(2025, 7, 15, 0, 0, 0, 0, tzinfo=self.real_timezone.utc)
        expected_end = self.real_datetime(2025, 7, 15, 23, 59, 59, 999999, tzinfo=self.real_timezone.utc)
        self.assertEqual(start, expected_start)
        self.assertEqual(end, expected_end)

    def test_parse_api_datetime_datetime(self):
        dt_str = "2025-06-04T10:00:00Z"
        # astimezone() without args converts to system's local time.
        # For test consistency, let's assume we want to see it as UTC if it was Z.
        expected_dt = self.real_datetime(2025, 6, 4, 10, 0, 0, tzinfo=self.real_timezone.utc)
        self.assertEqual(parse_api_datetime(dt_str), expected_dt)

    def test_parse_api_datetime_date_only(self):
        date_str = "2025-06-04"
        expected_dt = self.real_datetime(2025, 6, 4, 0, 0, 0, tzinfo=self.real_timezone.utc)
        self.assertEqual(parse_api_datetime(date_str), expected_dt)

    def test_parse_api_datetime_invalid_format(self):
        invalid_str = "invalid-date"
        self.assertIsNone(parse_api_datetime(invalid_str))
        self.assertIn("Warning: Could not parse datetime string", self.mock_stdout.getvalue())

    def test_display_tasks(self):
        mock_tasks_data = [
            {
                "title": "Task List 1",
                "id": "id1",
                "items": [
                    {"title": "Task 1", "status": "needsAction", "due": "2025-06-05T10:00:00Z"},
                    {"title": "Task 2", "status": "completed"},
                    {"title": "Task 3", "due": "invalid-date"},
                    {"title": "Task 4"},
                ]
            },
            {
                "title": "Task List 2",
                "id": "id2",
                "items": []
            }
        ]
        display_tasks(mock_tasks_data)
        output = self.mock_stdout.getvalue()
        self.assertIn("Task List: Task List 1", output)
        self.assertIn("[PENDING] Task 1", output)
        # Due: "2025-06-05T10:00:00Z". Output format: '%a %Y-%m-%d %H:%M'
        # Assuming astimezone() converts to UTC for test consistency if not otherwise mocked.
        # datetime(2025, 6, 5, 10, 0, 0, tzinfo=timezone.utc).strftime('%a %Y-%m-%d %H:%M') -> 'Thu 2025-06-05 10:00'
        self.assertIn("(Due: Thu 2025-06-05 10:00)", output)
        self.assertIn("[COMPLETED] Task 2", output)
        self.assertIn("(Malformed due date: invalid-date)", output)
        self.assertIn("[PENDING] Task 4", output)
        self.assertIn("Task List: Task List 2", output)
        self.assertIn("No tasks in this list.", output)

    def test_display_tasks_no_tasks(self):
        display_tasks([])
        self.assertIn("No tasks found.", self.mock_stdout.getvalue())

    def test_display_events(self):
        mock_calendars_with_events = [
            {
                "calendar": {"summary": "Calendar 1"},
                "events": [
                    {"summary": "Timed Event", "start": {"dateTime": "2025-06-04T11:00:00Z"}, "end": {"dateTime": "2025-06-04T12:00:00Z"}},
                    {"summary": "All Day Event", "start": {"date": "2025-06-05"}, "end": {"date": "2025-06-06"}},
                    {"summary": "Malformed Event", "start": {"dateTime": "invalid-date"}}
                ]
            },
             {
                "calendar": {"summary": "Calendar 2"},
                "events": []
            }
        ]
        display_events(mock_calendars_with_events)
        output = self.mock_stdout.getvalue()
        self.assertIn("Calendar: Calendar 1", output)
        # Timed Event: '2025-06-04T11:00:00Z' -> 'Wed 2025-06-04 11:00'
        self.assertIn("• Timed Event (Wed 2025-06-04 11:00 to Wed 2025-06-04 12:00)", output)
        # All Day Event: '2025-06-05' -> 'Thu 2025-06-05 (All Day)'
        self.assertIn("• All Day Event (Thu 2025-06-05 (All Day))", output)
        self.assertIn("Malformed date/time: invalid-date", output)
        self.assertIn("Calendar: Calendar 2", output)

    def test_display_events_no_events(self):
        display_events([])
        self.assertIn("No events found.", self.mock_stdout.getvalue())

    def test_display_tasks_and_events_today(self):
        mock_tasks = [
             {
                "title": "Task List 1",
                "id": "id1",
                "items": [
                    {"id": "task1", "title": "Today Task", "status": "needsAction", "due": "2025-06-04T15:00:00Z"},
                ]
            }
        ]
        mock_events = [
            {"id": "event1", "summary": "Today Event", "start": {"dateTime": "2025-06-04T16:00:00Z"}, "end": {"dateTime": "2025-06-04T17:00:00Z"}},
            {"id": "event2", "summary": "All Day Today Event", "start": {"date": "2025-06-04"}, "end": {"date": "2025-06-05"}},
        ]
        display_tasks_and_events_today(mock_tasks, mock_events)
        output = self.mock_stdout.getvalue()
        # Check for items and their order (all day events treated as midnight UTC)
        # Expected order: All Day Event (00:00), Task (15:00), Event (16:00)
        expected_order_regex = r".*All Day Today Event.*\[PENDING\] Today Task.*• Today Event.*"
        self.assertRegex(output, expected_order_regex, "Items are not in the expected order or are missing.")

    def test_display_tasks_and_events_today_no_items(self):
        display_tasks_and_events_today([], [])
        self.assertIn("No events or tasks found for today.", self.mock_stdout.getvalue())

    # TODO: Add tests for functions interacting with Google API and filesystem using mocking.
    # This will involve mocking os.path.exists, open, google.auth, googleapiclient.discovery, etc.
    # Due to the complexity of mocking the entire API interaction flow, these tests are not included in this initial response.
    # Example structure for mocking API calls:
    # @patch(\'calender_and_tasks_grab.build\')
    # @patch(\'calender_and_tasks_grab.authenticate_and_build_services\')
    # def test_process_account_data(self, mock_auth_and_build, mock_build):
    #     mock_auth_and_build.return_value = (MagicMock(), MagicMock(), True)
    #     mock_tasks_service = mock_auth_and_build.return_value[0]
    #     mock_calendar_service = mock_auth_and_build.return_value[1]
    #     mock_tasks_service.tasklists().list().execute.return_value = {...}
    #     mock_calendar_service.calendarList().list().execute.return_value = {...}
    #     mock_calendar_service.events().list().execute.return_value = {...}
    #     # Call the function and assert results
    #     ...

if __name__ == '__main__':
    unittest.main()
