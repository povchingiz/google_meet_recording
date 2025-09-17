# Google Meet Recording API

A FastAPI application for recording Google Meet sessions and automatically uploading them to Google Drive.

## Features

- 🎥 Record Google Meet sessions using FFmpeg
- 📁 Automatically upload recordings to Google Drive
- 🔐 OAuth2 authentication with Google
- 📊 RESTful API with real-time status tracking
- 🚀 Asynchronous background processing
- 📝 Automatic session management

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file with your Google credentials:

```env
GMAIL_ADDRESS=your-email@gmail.com
GMAIL_PASSWORD=your-app-password
```

### 3. Google Drive Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Drive API
4. Create OAuth2 credentials (Desktop Application)
5. Download the credentials file as `credentials.json`

### 4. System Requirements

- FFmpeg installed and available in PATH
- Chrome/Chromium browser
- PulseAudio (for Linux audio recording)

## API Usage

### Start the Server

```bash
# Using Python directly
python app.py

# Or using Uvicorn
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### API Endpoints

#### 1. Start Recording

**POST** `/start-recording`

```json
{
  "meeting_url": "https://meet.google.com/abc-defg-hij",
  "duration_minutes": 30,
  "upload_to_drive": true,
  "folder_name": "Meeting Recordings"
}
```

**Response:**
```json
{
  "session_id": "uuid-string",
  "status": "queued",
  "message": "Recording session started successfully",
  "meeting_url": "https://meet.google.com/abc-defg-hij",
  "duration_minutes": 30
}
```

#### 2. Check Status

**GET** `/status/{session_id}`

**Response:**
```json
{
  "session_id": "uuid-string",
  "status": "recording",
  "recording_file": "recording_uuid.mp3",
  "drive_link": "https://drive.google.com/file/d/...",
  "error_message": null
}
```

#### 3. List Sessions

**GET** `/sessions`

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "uuid-string",
      "status": "completed",
      "meeting_url": "https://meet.google.com/abc-defg-hij",
      "created_at": "2025-09-16T10:30:00",
      ...
    }
  ]
}
```

#### 4. Delete Session

**DELETE** `/sessions/{session_id}`

### Status Values

- `queued` - Session created, waiting to start
- `starting` - Initializing recording process
- `logging_in` - Authenticating with Google
- `joining_meeting` - Joining the meeting
- `recording` - Currently recording
- `recording_complete` - Recording finished
- `uploading` - Uploading to Google Drive
- `completed` - All tasks completed successfully
- `error` - An error occurred
- `recording_failed` - Recording process failed
- `upload_failed` - Upload to Drive failed

## Client Example

```python
import requests

# Start recording
response = requests.post("http://localhost:8000/start-recording", json={
    "meeting_url": "https://meet.google.com/abc-defg-hij",
    "duration_minutes": 30,
    "upload_to_drive": True
})

session_id = response.json()["session_id"]

# Check status
status_response = requests.get(f"http://localhost:8000/status/{session_id}")
print(status_response.json())
```

## Example Usage

Run the provided client example:

```bash
python client_example.py
```

## Supported Meeting URL Formats

- `https://meet.google.com/abc-defg-hij`
- `https://meet.google.com/unsupported?meetingCode=abc-defg-hij`
- Any URL containing a valid Google Meet meeting code

## Security Notes

- Store credentials securely in environment variables
- Use HTTPS in production
- Implement proper authentication for API access
- Regular token refresh for Google Drive access

## Troubleshooting

### Common Issues

1. **FFmpeg not found**: Install FFmpeg and ensure it's in your PATH
2. **Chrome driver issues**: Make sure Chrome/Chromium is installed
3. **Audio recording fails**: Check PulseAudio configuration
4. **Google login fails**: Verify credentials and enable "Less secure app access"
5. **Drive upload fails**: Check OAuth2 credentials and API permissions

### Logs

Check the application logs for detailed error messages and debugging information.

## License

MIT License
