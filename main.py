
import subprocess, time, os, re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MAIL_ADDRESS = os.getenv('GMAIL_ADDRESS')
PASSWORD = os.getenv('GMAIL_PASSWORD')
OUTPUT_FILE = "meet_recording.mp3"
RECORD_DURATION = 60 * 2  # seconds
PULSE_SOURCE = "default"

def Glogin(mail_address, password):
    # Login Page
    driver.get(
        'https://accounts.google.com/v3/signin/identifier?amp%3Bcontinue=https%3A%2F%2Fwww.google.com%2F&%3Bec=GAZAAQ&%3Bpassive=true&hl=en&ifkv=AdBytiNzMMSVMISwPVG6rsx71PGx7dJrV87hLBDeaVDtzaM8UnuaBPDk18ggEViZVUfGOU3njoBF&flowName=WebLiteSignIn&flowEntry=ServiceLogin&dsh=S117544077%3A1753258186211462')

    # input Gmail
    driver.find_element(By.ID, "identifierId").send_keys(mail_address)
    driver.find_element(By.ID, "identifierNext").click()
    driver.implicitly_wait(10)

    # input Password
    driver.find_element(By.XPATH,
        '//*[@id="password"]').send_keys(password)
    driver.implicitly_wait(10)
    driver.find_element(By.ID, "passwordNext").click()
    driver.implicitly_wait(10)

    # go to google home page
    driver.get('https://www.google.com/')
    driver.implicitly_wait(100)


def turnOffMicCam():
    # turn off Microphone
    time.sleep(2)
    driver.find_element(By.XPATH,
        '//*[@id="yDmH0d"]/c-wiz/div/div/div[8]/div[3]/div/div/div[2]/div/div[1]/div[1]/div[1]/div/div[4]/div[1]/div/div/div').click()
    driver.implicitly_wait(3000)

    # turn off camera
    time.sleep(1)
    driver.find_element(By.XPATH,
        '//*[@id="yDmH0d"]/c-wiz/div/div/div[8]/div[3]/div/div/div[2]/div/div[1]/div[1]/div[1]/div/div[4]/div[2]/div/div').click()
    driver.implicitly_wait(3000)


def start_ffmpeg_record(output, duration, pulse_source=PULSE_SOURCE):
    cmd = [
        "ffmpeg",
        "-y",
        "-f", "pulse",
        "-i", pulse_source,
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        output
    ]

    print("Starting ffmpeg recording:", " ".join(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    try:
        time.sleep(duration)
    finally:
        p.terminate()
        try:
            p.wait(timeout=10)
        except Exception:
            p.kill()
    print("ffmpeg recording finished.")

def upload_to_drive(file_path):
    """
    Upload the recorded file to Google Drive using OAuth2
    
    Args:
        file_path (str): Path to the file to upload
    """
    try:
        # Initialize Google Drive uploader with OAuth2
        from google_drive_uploader import GoogleDriveUploader
        uploader = GoogleDriveUploader()
        
        # Create or get the Meeting Recordings folder
        folder_name = "Meeting Recordings"
        folder = uploader.create_folder(folder_name)
        
        # Generate a timestamped filename
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        drive_filename = f"meeting_recording_{timestamp}.mp3"
        
        # Upload the file to the folder
        folder_id = folder['id'] if folder else None
        result = uploader.upload_file(file_path, folder_id=folder_id, file_name=drive_filename)
        
        if result:
            print(f"Successfully uploaded to Google Drive: {result.get('webViewLink')}")
            return result
        else:
            print("Failed to upload to Google Drive")
            return None
            
    except Exception as e:
        print(f"Error uploading to Google Drive: {e}")
        return None


def AskToJoin():
    # Ask to Join meet
    time.sleep(5)
    # driver.implicitly_wait(2000)
    join_btn = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH,
            "//span[contains(text(),'Join now') or contains(text(),'Ask to join')]/ancestor::button"
        ))
    )
    join_btn.click()
    print('connected to meet')
    time.sleep(15)
    
    # Start recording
    start_ffmpeg_record(OUTPUT_FILE, RECORD_DURATION)
    print("Recording saved to:", OUTPUT_FILE)
    
    # Upload to Google Drive
    if os.path.exists(OUTPUT_FILE):
        print("Uploading recording to Google Drive...")
        upload_result = upload_to_drive(OUTPUT_FILE)
        if upload_result:
            print("Upload completed successfully!")
        else:
            print("Upload failed!")
    else:
        print(f"Recording file {OUTPUT_FILE} not found!")
    
    time.sleep(10)  # Wait a bit before ending



# create chrome instance
opt = Options()
opt.add_argument('--disable-blink-features=AutomationControlled')
opt.add_argument('--start-maximized')
opt.add_experimental_option("prefs", {
    "profile.default_content_setting_values.media_stream_mic": 1,
    "profile.default_content_setting_values.media_stream_camera": 1,
    "profile.default_content_setting_values.geolocation": 0,
    "profile.default_content_setting_values.notifications": 1
})
driver = webdriver.Chrome(options=opt)

# login to Google account
Glogin(MAIL_ADDRESS, PASSWORD)

# go to google meet
driver.get('https://meet.google.com/unsupported?meetingCode=fkz-humq-tus&ref=https://meet.google.com/fkz-humq-tus')
# https://meet.google.com/fkz-humq-tus

# turnOffMicCam()
AskToJoin()
# joinNow()