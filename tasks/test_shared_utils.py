
import pytest
import os
import json
from datetime import datetime, timedelta, timezone
from unittest import mock

# Import functions from the module to be tested
# Assuming shared_utils.py is in the same directory or accessible via PYTHONPATH
import shared_utils

# --- Fixtures ---

@pytest.fixture
def temp_state_file(tmp_path):
    """Creates a temporary state file path."""
    return tmp_path / "test_state.json"

@pytest.fixture
def temp_db_file(tmp_path):
    """Creates a temporary database file path."""
    return tmp_path / "test_zapmeow.db"

# --- Tests for load_state ---

def test_load_state_file_exists_valid_json(temp_state_file):
    """Test loading state from an existing file with valid JSON."""
    now = datetime.now(timezone.utc)
    state_content = {"last_timestamp": now.isoformat(), "other_data": "test"}
    with open(temp_state_file, 'w') as f:
        json.dump(state_content, f)

    loaded_state = shared_utils.load_state(str(temp_state_file))
    assert loaded_state is not None
    assert isinstance(loaded_state, dict)
    assert 'last_timestamp' in loaded_state
    assert 'other_data' in loaded_state
    assert loaded_state['other_data'] == 'test'
    
    # Check timestamp parsing within the test if needed, but load_state just returns the dict
    # The calling code is responsible for parsing the timestamp string.
    # For this test, we just confirm the dictionary structure and content.

def test_load_state_file_not_exists(temp_state_file):
    """Test loading state when the state file does not exist."""
    assert not os.path.exists(temp_state_file)
    loaded_state = shared_utils.load_state(str(temp_state_file))
    assert loaded_state is None

def test_load_state_invalid_json(temp_state_file, capsys):
    """Test loading state from a file with invalid JSON."""
    with open(temp_state_file, 'w') as f:
        f.write("this is not json")

    loaded_state = shared_utils.load_state(str(temp_state_file))
    assert loaded_state is None
    captured = capsys.readouterr()
    assert f"Error decoding state file: {temp_state_file}" in captured.out

def test_load_state_missing_key(temp_state_file):
    """Test loading state from a file with valid JSON but missing 'last_timestamp' key."""
    state_content = {"some_other_key": "some_value"}
    with open(temp_state_file, 'w') as f:
        json.dump(state_content, f)

    loaded_state = shared_utils.load_state(str(temp_state_file))
    assert loaded_state is not None
    assert isinstance(loaded_state, dict)
    assert 'last_timestamp' not in loaded_state
    assert 'some_other_key' in loaded_state

# --- Tests for save_state ---

def test_save_state_creates_file_and_loads_correctly(temp_state_file):
    """Test saving state creates the file and its content can be loaded back."""
    now = datetime.now(timezone.utc)
    state_to_save = {
        'last_timestamp': now.isoformat(),
        'some_other_key': 'some_value',
        'nested_data': {'a': 1, 'b': 2}
    }
    shared_utils.save_state(str(temp_state_file), state_to_save)

    assert os.path.exists(temp_state_file)

    with open(temp_state_file, 'r') as f:
        loaded_state = json.load(f)

    assert loaded_state == state_to_save
    assert 'last_timestamp' in loaded_state
    assert 'some_other_key' in loaded_state
    assert 'nested_data' in loaded_state

def test_save_state_creates_directory(tmp_path):
    """Test save_state creates the directory if it doesn't exist."""
    deep_dir_path = tmp_path / "deep" / "dir"
    state_file_in_deep_dir = deep_dir_path / "state.json"
    assert not os.path.exists(deep_dir_path)

    state_to_save = {'last_timestamp': datetime.now(timezone.utc).isoformat(), 'data': 'some_data'}
    shared_utils.save_state(str(state_file_in_deep_dir), state_to_save)

    assert os.path.exists(state_file_in_deep_dir)
    with open(state_file_in_deep_dir, 'r') as f:
        state_data = json.load(f)
    assert state_data == state_to_save

# --- Tests for format_messages_for_prompt ---

def test_format_messages_empty():
    """Test formatting with an empty list of messages."""
    formatted = shared_utils.format_messages_for_prompt([])
    assert formatted == "Chat History:\\n"

def test_format_messages_with_default_jid_map():
    """Test formatting with messages using the default JID map."""
    messages = [
        ('2023-01-01 10:00:00', '447709487896', 'Hello from Steph'),
        ('2023-01-01 10:01:00', '447906616842', 'Hi James here')
    ]
    expected = (
        "Chat History:\\n"
        "[2023-01-01 10:00:00] Steph: Hello from Steph\\n"
        "[2023-01-01 10:01:00] James: Hi James here\\n"
    )
    assert shared_utils.format_messages_for_prompt(messages) == expected

def test_format_messages_with_custom_jid_map():
    """Test formatting with messages using a custom JID map."""
    messages = [
        ('2023-01-01 10:00:00', '123', 'Msg 1'),
        ('2023-01-01 10:01:00', '456', 'Msg 2')
    ]
    custom_map = {'123': 'Alice', '456': 'Bob'}
    expected = (
        "Chat History:\\n"
        "[2023-01-01 10:00:00] Alice: Msg 1\\n"
        "[2023-01-01 10:01:00] Bob: Msg 2\\n"
    )
    assert shared_utils.format_messages_for_prompt(messages, jid_map=custom_map) == expected

def test_format_messages_jid_not_in_map():
    """Test formatting when a JID is not found in the map."""
    messages = [
        ('2023-01-01 10:00:00', 'unknown_jid', 'Message from unknown')
    ]
    expected = (
        "Chat History:\\n"
        "[2023-01-01 10:00:00] unknown_jid: Message from unknown\\n"
    )
    assert shared_utils.format_messages_for_prompt(messages) == expected

# --- Tests for get_latest_message_timestamp ---

def test_get_latest_message_timestamp_empty_list():
    """Test with an empty list of messages."""
    assert shared_utils.get_latest_message_timestamp([]) is None

def test_get_latest_message_timestamp_valid_timestamps():
    """Test with various valid timestamp formats."""
    # ISO format with Z
    messages_z = [('2023-10-26 10:00:00', 's1', 'm1'), ('2023-10-26 10:05:00Z', 's2', 'm2')]
    ts_z = shared_utils.get_latest_message_timestamp(messages_z)
    assert ts_z == datetime(2023, 10, 26, 10, 5, 0, tzinfo=timezone.utc)

    # ISO format with offset
    messages_offset = [('2023-10-26 10:00:00+01:00', 's1', 'm1'), ('2023-10-26 12:05:00+02:00', 's2', 'm2')]
    ts_offset = shared_utils.get_latest_message_timestamp(messages_offset)
    assert ts_offset == datetime(2023, 10, 26, 12, 5, 0, tzinfo=timezone(timedelta(hours=2)))
    assert ts_offset.astimezone(timezone.utc) == datetime(2023, 10, 26, 10, 5, 0, tzinfo=timezone.utc)
    
    # SQL-like timestamp (no timezone, assumed naive, then localized if needed by calling code)
    # The function itself will try to parse with timezone first, then iso.
    # If a simple 'YYYY-MM-DD HH:MM:SS' is given, fromisoformat will treat it as naive if no tz info.
    # However, the code tries strptime with %z first.
    # Let's test one that fromisoformat can handle without 'Z' or offset if strptime fails.
    # Based on the current implementation, it might favor fromisoformat for "YYYY-MM-DD HH:MM:SS"
    messages_no_tz_like_db = [
        ('2023-10-27 14:30:00', 's1', 'm1'), 
        ('2023-10-27 14:35:00', 's2', 'm2') # This is the latest
    ]
    # This test depends on how the fallback in get_latest_message_timestamp works.
    # If '%Y-%m-%d %H:%M:%S%z' fails, it tries fromisoformat.
    # datetime.fromisoformat('2023-10-27 14:35:00') creates a naive datetime.
    ts_no_tz = shared_utils.get_latest_message_timestamp(messages_no_tz_like_db)
    assert ts_no_tz == datetime(2023, 10, 27, 14, 35, 0) # Naive, as per fromisoformat without tz info

def test_get_latest_message_timestamp_invalid_timestamp(capsys):
    """Test with an invalid timestamp string."""
    messages = [('invalid_timestamp_string', 's1', 'm1')]
    ts = shared_utils.get_latest_message_timestamp(messages)
    assert ts is None
    captured = capsys.readouterr()
    assert "Error parsing timestamp 'invalid_timestamp_string'" in captured.out

# --- Mocks and Tests for functions with external dependencies ---

# Mocking os.getenv for API_KEY
@mock.patch('shared_utils.os.getenv')
@mock.patch('shared_utils.genai.GenerativeModel')
def test_generate_llm_response_success(mock_gen_model, mock_getenv):
    """Test successful LLM response generation."""
    mock_getenv.return_value = "FAKE_API_KEY" # Mock API_KEY
    
    mock_model_instance = mock.Mock()
    mock_model_instance.generate_content.return_value = mock.Mock(text="LLM says hi")
    mock_gen_model.return_value = mock_model_instance

    prompt = "Test prompt"
    history = "Test history"
    response = shared_utils.generate_llm_response(prompt, history)

    assert isinstance(response, dict)
    assert response.get('success') is True
    assert response.get('response_text') == "LLM says hi"
    assert 'api_details' in response
    assert isinstance(response.get('api_details'), dict)
    assert response.get('api_details', {}).get('model') == 'gemini-1.5-flash-latest'
    assert response.get('api_details', {}).get('prompt') == f"{prompt}\\n{history}"

    mock_getenv.assert_called_once_with("GEMINI_API_KEY")
    shared_utils.genai.configure.assert_called_once_with(api_key="FAKE_API_KEY")
    mock_gen_model.assert_called_once_with('gemini-1.5-flash-latest')
    mock_model_instance.generate_content.assert_called_once_with(contents=[f"{prompt}\\n{history}"])

@mock.patch('shared_utils.os.getenv')
def test_generate_llm_response_no_api_key(mock_getenv, capsys):
    """Test LLM response generation when API_KEY is not set."""
    mock_getenv.return_value = None # API_KEY not set
    response = shared_utils.generate_llm_response("Test prompt")
    
    assert response is None
    captured = capsys.readouterr()
    assert "Error: GEMINI_API_KEY not set. LLM generation skipped." in captured.out

@mock.patch('shared_utils.os.getenv')
@mock.patch('shared_utils.genai.GenerativeModel')
def test_generate_llm_response_api_error(mock_gen_model, mock_getenv, capsys):
    """Test LLM response generation with an API error."""
    mock_getenv.return_value = "FAKE_API_KEY"
    
    mock_model_instance = mock.Mock()
    mock_model_instance.generate_content.side_effect = Exception("Gemini Boom")
    mock_gen_model.return_value = mock_model_instance

    response = shared_utils.generate_llm_response("Test prompt")
    
    assert isinstance(response, dict)
    assert response.get('success') is False
    assert 'error' in response
    assert "Gemini Boom" in response.get('error')
    assert 'api_details' in response
    assert isinstance(response.get('api_details'), dict)
    assert response.get('api_details', {}).get('model') == 'gemini-1.5-flash-latest'

    captured = capsys.readouterr()
    assert "Gemini API error: Gemini Boom" in captured.out

@mock.patch('shared_utils.requests.post')
def test_send_text_message_success(mock_post, capsys):
    """Test successful text message sending."""
    mock_response = mock.Mock()
    mock_response.raise_for_status = mock.Mock() # Does nothing if successful
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    api_url = "http://fakeapi.com/send"
    phone = "1234567890"
    text = "Hello there"
    
    result = shared_utils.send_text_message(api_url, phone, text)
    
    assert isinstance(result, dict)
    assert result.get('success') is True
    assert 'message_details' in result
    details = result.get('message_details', {})
    assert details.get('api_url') == api_url
    assert details.get('phone_number') == phone
    assert details.get('text_sent') == text
    assert details.get('status_code') == 200

    mock_post.assert_called_once_with(api_url, json={'phone': phone, 'text': text})
    mock_response.raise_for_status.assert_called_once()
    captured = capsys.readouterr()
    assert f"Message sent successfully to {phone}." in captured.out

@mock.patch('shared_utils.requests.post')
def test_send_text_message_failure(mock_post, capsys):
    """Test failed text message sending (e.g., network error or bad status)."""
    mock_post.side_effect = shared_utils.requests.exceptions.RequestException("Network Error")

    api_url = "http://fakeapi.com/send"
    phone = "1234567890"
    text = "Hello there"

    result = shared_utils.send_text_message(api_url, phone, text)
    
    assert isinstance(result, dict)
    assert result.get('success') is False
    assert 'error' in result
    assert "Network Error" in result.get('error')
    assert 'message_details' in result
    details = result.get('message_details', {})
    assert details.get('api_url') == api_url
    assert details.get('phone_number') == phone
    assert details.get('text_sent') == text
    # status_code might not be present on network error, so don't assert it

    captured = capsys.readouterr()
    assert f"Error sending message to {phone}: Network Error" in captured.out

@mock.patch('shared_utils.requests.post')
def test_send_text_message_http_error(mock_post, capsys):
    """Test failed text message sending due to HTTP error status."""
    mock_response = mock.Mock()
    # Configure raise_for_status to simulate an HTTP error
    http_error = shared_utils.requests.exceptions.HTTPError("400 Client Error")
    mock_response.raise_for_status.side_effect = http_error
    mock_post.return_value = mock_response

    api_url = "http://fakeapi.com/send"
    phone = "1234567890"
    text = "Hello there"

    result = shared_utils.send_text_message(api_url, phone, text)
    assert result is False
    captured = capsys.readouterr()
    assert f"Error sending message to {phone}: 400 Client Error" in captured.out


# --- Tests for get_recent_messages (requires mocking sqlite3) ---

@mock.patch('shared_utils.sqlite3.connect')
def test_get_recent_messages_success(mock_sqlite_connect, temp_db_file):
    """Test fetching recent messages successfully."""
    mock_conn = mock.Mock()
    mock_cursor = mock.Mock()
    mock_sqlite_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    expected_messages = [
        ('2023-01-01 10:00:00', 'jid1', 'Hello'),
        ('2023-01-01 10:05:00', 'jid2', 'Hi there')
    ]
    mock_cursor.fetchall.return_value = expected_messages

    chat_jid = "test_chat_jid"
    since_timestamp = datetime(2023, 1, 1, 9, 0, 0)
    
    messages = shared_utils.get_recent_messages(str(temp_db_file), chat_jid, since_timestamp)

    assert messages == expected_messages
    mock_sqlite_connect.assert_called_once_with(str(temp_db_file))
    mock_conn.cursor.assert_called_once()
    since_timestamp_str = since_timestamp.strftime('%Y-%m-%d %H:%M:%S')
    mock_cursor.execute.assert_called_once_with(
        "SELECT timestamp, sender_jid, body FROM messages WHERE chat_jid = ? AND timestamp > ? ORDER BY timestamp ASC",
        (chat_jid, since_timestamp_str)
    )
    mock_conn.close.assert_called_once()

@mock.patch('shared_utils.sqlite3.connect')
def test_get_recent_messages_db_error(mock_sqlite_connect, temp_db_file, capsys):
    """Test database error during fetching messages."""
    mock_sqlite_connect.side_effect = shared_utils.sqlite3.Error("Test DB Error")

    chat_jid = "test_chat_jid"
    since_timestamp = datetime(2023, 1, 1, 9, 0, 0)

    messages = shared_utils.get_recent_messages(str(temp_db_file), chat_jid, since_timestamp)
    
    assert messages == []
    mock_sqlite_connect.assert_called_once_with(str(temp_db_file))
    captured = capsys.readouterr()
    assert "Database error: Test DB Error" in captured.out
    assert f"Database path: {str(temp_db_file)}" in captured.out
    # Check that conn.close() is not called if conn was never successfully assigned
    # This is tricky because the mock_conn itself is not created if connect() fails.
    # The finally block in the original code will try to close `conn` if it's not None.
    # If `sqlite3.connect` raises an error, `conn` remains at its initial `None` value, so `close` isn't called.

@mock.patch('shared_utils.sqlite3.connect')
def test_get_recent_messages_no_messages_found(mock_sqlite_connect, temp_db_file):
    """Test fetching when no messages meet the criteria."""
    mock_conn = mock.Mock()
    mock_cursor = mock.Mock()
    mock_sqlite_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [] # No messages found

    chat_jid = "test_chat_jid"
    since_timestamp = datetime(2023, 1, 1, 9, 0, 0)
    
    messages = shared_utils.get_recent_messages(str(temp_db_file), chat_jid, since_timestamp)

    assert messages == []
    mock_conn.close.assert_called_once()

