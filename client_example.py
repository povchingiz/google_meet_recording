#!/usr/bin/env python3
"""
Example client for the Google Meet Recording API
Shows how to start a recording and check its status
"""

import requests
import time
import json

# API base URL
BASE_URL = "http://localhost:8000"

def start_recording(meeting_url: str, duration_minutes: int = 30, upload_to_drive: bool = True):
    """Start a meeting recording"""
    endpoint = f"{BASE_URL}/start-recording"
    
    payload = {
        "meeting_url": meeting_url,
        "duration_minutes": duration_minutes,
        "upload_to_drive": upload_to_drive,
        "folder_name": "Meeting Recordings"
    }
    
    try:
        response = requests.post(endpoint, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error starting recording: {e}")
        return None

def check_status(session_id: str):
    """Check the status of a recording session"""
    endpoint = f"{BASE_URL}/status/{session_id}"
    
    try:
        response = requests.get(endpoint)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error checking status: {e}")
        return None

def list_sessions():
    """List all recording sessions"""
    endpoint = f"{BASE_URL}/sessions"
    
    try:
        response = requests.get(endpoint)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error listing sessions: {e}")
        return None

def main():
    """Example usage"""
    print("Google Meet Recording API Client")
    print("=" * 40)
    
    # Example meeting URL (replace with actual meeting URL)
    meeting_url = "https://meet.google.com/fkz-humq-tus"
    
    print(f"Starting recording for: {meeting_url}")
    
    # Start recording
    result = start_recording(meeting_url, duration_minutes=2)  # Short duration for testing
    
    if result:
        session_id = result["session_id"]
        print(f"Recording started! Session ID: {session_id}")
        print(f"Status: {result['status']}")
        
        # Monitor progress
        print("\nMonitoring progress...")
        while True:
            status = check_status(session_id)
            if status:
                print(f"Status: {status['status']}")
                
                if status['status'] in ['completed', 'error', 'recording_failed', 'upload_failed']:
                    if status['status'] == 'completed':
                        print("✅ Recording completed successfully!")
                        if status.get('drive_link'):
                            print(f"Drive Link: {status['drive_link']}")
                        if status.get('recording_file'):
                            print(f"Local File: {status['recording_file']}")
                    else:
                        print(f"❌ Recording failed: {status.get('error_message', 'Unknown error')}")
                    break
                
                # Wait before checking again
                time.sleep(10)
            else:
                print("Failed to check status")
                break
    else:
        print("Failed to start recording")

def test_api_health():
    """Test if the API is running"""
    try:
        response = requests.get(BASE_URL)
        response.raise_for_status()
        result = response.json()
        print(f"API Status: {result['status']}")
        print(f"Version: {result['version']}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"API not available: {e}")
        return False

if __name__ == "__main__":
    print("Testing API connection...")
    if test_api_health():
        print("API is running!")
        main()
    else:
        print("Please start the API server first:")
        print("python app.py")
        print("\nOr using uvicorn:")
        print("uvicorn app:app --reload --host 0.0.0.0 --port 8000")
