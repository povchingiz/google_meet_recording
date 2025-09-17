#!/usr/bin/env python3
"""
FastAPI application for Google Meet recording
Provides API endpoints to start and manage Google Meet recordings
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, HttpUrl
from typing import Optional, Dict, Any
import subprocess
import time
import os
import re
import uuid
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv
import asyncio
import threading
import logging

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Google Meet Recording API",
    description="API for recording Google Meet sessions and uploading to Google Drive",
    version="1.0.0"
)

# Global variables to track recording sessions with thread safety
active_sessions: Dict[str, Dict[str, Any]] = {}
sessions_lock = threading.Lock()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MeetingRequest(BaseModel):
    meeting_url: str
    duration_minutes: Optional[int] = 30
    upload_to_drive: Optional[bool] = True
    folder_name: Optional[str] = "Meeting Recordings"

class MeetingResponse(BaseModel):
    session_id: str
    status: str
    message: str
    meeting_url: str
    duration_minutes: int

class SessionStatus(BaseModel):
    session_id: str
    status: str
    recording_file: Optional[str] = None
    drive_link: Optional[str] = None
    error_message: Optional[str] = None

def update_session_status(session_id: str, status: str, **kwargs):
    """Thread-safe function to update session status"""
    with sessions_lock:
        if session_id in active_sessions:
            active_sessions[session_id]["status"] = status
            for key, value in kwargs.items():
                active_sessions[session_id][key] = value
            logger.info(f"Session {session_id} status updated to: {status}")

def get_session_data(session_id: str) -> Optional[Dict[str, Any]]:
    """Thread-safe function to get session data"""
    with sessions_lock:
        return active_sessions.get(session_id, {}).copy() if session_id in active_sessions else None

def extract_meeting_id(meeting_url: str) -> str:
    """Extract meeting ID from Google Meet URL"""
    patterns = [
        r'meet\.google\.com/([a-z]{3}-[a-z]{4}-[a-z]{3})',  # meet.google.com/abc-defg-hij
        r'meetingCode=([a-z]{3}-[a-z]{4}-[a-z]{3})',        # meetingCode=abc-defg-hij
        r'meet\.google\.com/([a-zA-Z0-9-_]+)',              # Other formats
    ]
    
    for pattern in patterns:
        match = re.search(pattern, meeting_url)
        if match:
            return match.group(1)
    
    raise ValueError("Invalid Google Meet URL format")

def get_chrome_options():
    """Configure Chrome options for headless operation"""
    opt = Options()
    opt.add_argument('--disable-blink-features=AutomationControlled')
    opt.add_argument('--headless')  # Run in headless mode for API
    opt.add_argument('--no-sandbox')
    opt.add_argument('--disable-dev-shm-usage')
    opt.add_argument('--disable-gpu')
    opt.add_argument('--window-size=1920,1080')
    opt.add_experimental_option("prefs", {
        "profile.default_content_setting_values.media_stream_mic": 1,
        "profile.default_content_setting_values.media_stream_camera": 1,
        "profile.default_content_setting_values.geolocation": 0,
        "profile.default_content_setting_values.notifications": 1
    })
    return opt

def google_login(driver, mail_address: str, password: str):
    """Login to Google account"""
    try:
        driver.get('https://accounts.google.com/v3/signin/identifier?continue=https%3A%2F%2Fwww.google.com%2F&passive=true&hl=en&flowName=WebLiteSignIn&flowEntry=ServiceLogin')
        
        # Input Gmail
        email_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "identifierId"))
        )
        email_input.send_keys(mail_address)
        
        next_button = driver.find_element(By.ID, "identifierNext")
        next_button.click()
        
        # Input Password
        password_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="password"]'))
        )
        password_input.send_keys(password)
        
        password_next = driver.find_element(By.ID, "passwordNext")
        password_next.click()
        
        # Wait for login to complete
        WebDriverWait(driver, 10).until(
            lambda d: 'google.com' in d.current_url and 'signin' not in d.current_url
        )
        
        return True
    except Exception as e:
        print(f"Login failed: {e}")
        return False

def start_recording(output_file: str, duration_seconds: int, pulse_source: str = "default"):
    """Start FFmpeg recording"""
    cmd = [
        "ffmpeg",
        "-y",
        "-f", "pulse",
        "-i", pulse_source,
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        output_file
    ]
    
    print(f"Starting recording: {' '.join(cmd)}")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        time.sleep(duration_seconds)
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except:
            process.kill()
    
    return os.path.exists(output_file)

def upload_to_drive(file_path: str, folder_name: str = "Meeting Recordings"):
    """Upload file to Google Drive"""
    try:
        from google_drive_uploader import GoogleDriveUploader
        uploader = GoogleDriveUploader()
        
        # Create or get folder
        folder = uploader.create_folder(folder_name)
        
        # Generate timestamped filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        drive_filename = f"meeting_recording_{timestamp}.mp3"
        
        # Upload file
        folder_id = folder['id'] if folder else None
        result = uploader.upload_file(file_path, folder_id=folder_id, file_name=drive_filename)
        
        return result
    except Exception as e:
        print(f"Upload error: {e}")
        return None

def record_meeting_session(session_id: str, meeting_url: str, duration_minutes: int, upload_to_drive_flag: bool, folder_name: str):
    """Background task to record a meeting session"""
    try:
        logger.info(f"Starting recording session {session_id}")
        
        # Update session status
        update_session_status(session_id, "starting")
        
        # Get credentials
        mail_address = os.getenv('GMAIL_ADDRESS')
        password = os.getenv('GMAIL_PASSWORD')
        
        if not mail_address or not password:
            raise Exception("Gmail credentials not found in environment variables")
        
        # Setup Chrome driver
        opt = get_chrome_options()
        driver = webdriver.Chrome(options=opt)
        
        try:
            # Login to Google
            update_session_status(session_id, "logging_in")
            if not google_login(driver, mail_address, password):
                raise Exception("Failed to login to Google account")
            
            # Navigate to meeting
            update_session_status(session_id, "joining_meeting")
            driver.get(meeting_url)
            
            # Wait for and click join button
            join_btn = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//span[contains(text(),'Join now') or contains(text(),'Ask to join')]/ancestor::button"
                ))
            )
            join_btn.click()
            
            # Start recording
            update_session_status(session_id, "recording")
            output_file = f"recording_{session_id}.mp3"
            duration_seconds = duration_minutes * 60
            
            recording_success = start_recording(output_file, duration_seconds)
            
            if recording_success:
                update_session_status(session_id, "recording_complete", recording_file=output_file)
                
                # Upload to Drive if requested
                if upload_to_drive_flag:
                    update_session_status(session_id, "uploading")
                    upload_result = upload_to_drive(output_file, folder_name)
                    
                    if upload_result:
                        update_session_status(session_id, "completed", 
                                           drive_link=upload_result.get('webViewLink'))
                        logger.info(f"Session {session_id} completed successfully")
                    else:
                        update_session_status(session_id, "upload_failed", 
                                           error_message="Failed to upload to Google Drive")
                else:
                    update_session_status(session_id, "completed")
                    logger.info(f"Session {session_id} completed successfully")
            else:
                update_session_status(session_id, "recording_failed", 
                                   error_message="Recording failed")
                
        finally:
            driver.quit()
            
    except Exception as e:
        logger.error(f"Session {session_id} failed: {str(e)}")
        update_session_status(session_id, "error", error_message=str(e))

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Google Meet Recording API",
        "status": "running",
        "version": "1.0.0"
    }

@app.post("/start-recording", response_model=MeetingResponse)
async def start_meeting_recording(request: MeetingRequest, background_tasks: BackgroundTasks):
    """Start recording a Google Meet session"""
    try:
        # Validate meeting URL
        meeting_id = extract_meeting_id(request.meeting_url)
        
        # Handle default values for optional parameters
        duration_minutes = request.duration_minutes or 30
        upload_to_drive = request.upload_to_drive if request.upload_to_drive is not None else True
        folder_name = request.folder_name or "Meeting Recordings"
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Initialize session with thread safety
        with sessions_lock:
            active_sessions[session_id] = {
                "session_id": session_id,
                "meeting_url": request.meeting_url,
                "meeting_id": meeting_id,
                "duration_minutes": duration_minutes,
                "upload_to_drive": upload_to_drive,
                "folder_name": folder_name,
                "status": "queued",
                "created_at": datetime.now().isoformat(),
                "recording_file": None,
                "drive_link": None,
                "error_message": None
            }
        
        # Start background recording task
        background_tasks.add_task(
            record_meeting_session,
            session_id,
            request.meeting_url,
            duration_minutes,
            upload_to_drive,
            folder_name
        )
        
        return MeetingResponse(
            session_id=session_id,
            status="queued",
            message="Recording session started successfully",
            meeting_url=request.meeting_url,
            duration_minutes=duration_minutes
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid meeting URL: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to start recording: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start recording: {str(e)}")

@app.get("/status/{session_id}", response_model=SessionStatus)
async def get_session_status(session_id: str):
    """Get the status of a recording session"""
    session = get_session_data(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return SessionStatus(
        session_id=session_id,
        status=session["status"],
        recording_file=session.get("recording_file"),
        drive_link=session.get("drive_link"),
        error_message=session.get("error_message")
    )

@app.get("/sessions")
async def list_sessions():
    """List all recording sessions"""
    with sessions_lock:
        sessions_copy = list(active_sessions.values())
    return {"sessions": sessions_copy}

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a recording session"""
    session = get_session_data(session_id)
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Clean up recording file if it exists
    if session.get("recording_file") and os.path.exists(session["recording_file"]):
        try:
            os.remove(session["recording_file"])
            logger.info(f"Deleted recording file: {session['recording_file']}")
        except Exception as e:
            logger.error(f"Failed to delete recording file: {e}")
    
    # Remove from active sessions
    with sessions_lock:
        if session_id in active_sessions:
            del active_sessions[session_id]
    
    logger.info(f"Session {session_id} deleted")
    return {"message": "Session deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    