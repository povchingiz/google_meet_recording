#!/usr/bin/env python3
"""
Test script for Google Drive upload functionality
This script will test the OAuth2 authentication and upload a test file
"""

import os
import tempfile
from google_drive_uploader import GoogleDriveOAuth

def test_drive_upload():
    """Test the Google Drive upload functionality"""
    
    print("Testing Google Drive upload functionality...")
    test_file_path = None

    try:
        # Create a test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as test_file:
            test_file.write("This is a test file for Google Drive upload.\n")
            test_file.write(f"Created at: {os.popen('date').read().strip()}\n")
            test_file_path = test_file.name 
        
        print(f"Created test file: {test_file_path}")
        
        # Initialize the Google Drive uploader
        print("Initializing Google Drive OAuth...")
        uploader = GoogleDriveOAuth()
        
        # Create or get the test folder
        print("Creating/getting test folder...")
        folder_name = "Test Uploads"
        folder = uploader.create_folder(folder_name)
        
        if folder:
            print(f"Folder ready: {folder['name']} (ID: {folder['id']})")
            
            # Upload the test file
            print("Uploading test file...")
            result = uploader.upload_file(
                test_file_path, 
                folder_id=folder['id'], 
                file_name="test_upload.txt"
            )
            
            if result:
                print("✅ Upload successful!")
                print(f"File ID: {result.get('id')}")
                print(f"File Name: {result.get('name')}")
                print(f"View Link: {result.get('webViewLink')}")
                
                # List files in the folder to verify
                print("\nFiles in the test folder:")
                files = uploader.list_files(folder_id=folder['id'])
                for file in files:
                    print(f"  - {file['name']} (ID: {file['id']})")
                
                return True
            else:
                print("❌ Upload failed!")
                return False
        else:
            print("❌ Failed to create/get folder!")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False
    
    finally:
        # Clean up test file
        if test_file_path is not None and os.path.exists(test_file_path):
            os.unlink(test_file_path)
            print(f"Cleaned up test file: {test_file_path}")

def main():
    """Main function"""
    print("Google Drive Upload Test")
    print("=" * 40)
    
    # Check if credentials file exists
    if not os.path.exists('credentials.json'):
        print("❌ Error: credentials.json not found!")
        print("Please make sure you have downloaded your OAuth2 credentials")
        print("from the Google Cloud Console and saved them as 'credentials.json'")
        return
    
    success = test_drive_upload()
    
    print("\n" + "=" * 40)
    if success:
        print("✅ All tests passed! Google Drive upload is working correctly.")
    else:
        print("❌ Tests failed. Please check the error messages above.")

if __name__ == "__main__":
    main()
