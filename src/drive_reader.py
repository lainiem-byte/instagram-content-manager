import os
import io
import logging
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from dotenv import load_dotenv

load_dotenv()

# Set up logging for drive_reader
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('drive_reader')

# We use the full drive scope because we need to move files to a 'Posted' subfolder
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

class DriveReader:
    def __init__(self):
        self.creds = None
        self.drive_service = None
        self._authenticate()

    def _authenticate(self):
        json_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        if not json_path or not os.path.exists(json_path):
            logger.error(f"Service account JSON not found at: {json_path}")
            return
        
        self.creds = service_account.Credentials.from_service_account_file(
            json_path, scopes=SCOPES
        )
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        logger.info("Successfully authenticated with Google Drive")

    def get_posted_folder_id(self, parent_folder_id):
        query = f"'{parent_folder_id}' in parents and name = 'Posted' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = self.drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = results.get('files', [])
        if files:
            return files[0]['id']
        else:
            folder_metadata = {
                'name': 'Posted',
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_folder_id]
            }
            folder = self.drive_service.files().create(body=folder_metadata, fields='id').execute()
            logger.info(f"Created 'Posted' subfolder with ID: {folder.get('id')}")
            return folder.get('id')

    def get_sheet_id_by_name(self, parent_folder_id, sheet_name="Instagram Post Log"):
        query = f"'{parent_folder_id}' in parents and name = '{sheet_name}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
        results = self.drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        files = results.get('files', [])
        if files:
            logger.info(f"Found sheet '{sheet_name}' with ID: {files[0]['id']}")
            return files[0]['id']
        return None

    def fetch_unprocessed_media(self, parent_folder_id, limit=100):
        query = f"'{parent_folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder' and mimeType != 'application/vnd.google-apps.spreadsheet' and trashed = false"
        results = self.drive_service.files().list(
            q=query, 
            spaces='drive', 
            fields='files(id, name, mimeType, modifiedTime, webContentLink)', 
            orderBy='modifiedTime desc',
            pageSize=limit
        ).execute()
        files = results.get('files', [])
        
        valid_mimes = ['image/jpeg', 'image/png', 'image/webp', 'video/mp4']
        unprocessed = []
        for f in files:
            if f.get('mimeType') in valid_mimes:
                unprocessed.append(f)
                logger.info(f"Fetched unprocessed file: {f['name']} (ID: {f['id']}) at {datetime.now().isoformat()}")
        
        return unprocessed

    def download_file(self, file_id, file_name, destination_folder='downloads'):
        os.makedirs(destination_folder, exist_ok=True)
        file_path = os.path.join(destination_folder, file_name)
        
        request = self.drive_service.files().get_media(fileId=file_id)
        fh = io.FileIO(file_path, 'wb')
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        
        logger.info(f"Downloaded file {file_name} to {file_path}")
        return file_path

    def move_file_to_posted(self, file_id, parent_folder_id):
        posted_folder_id = self.get_posted_folder_id(parent_folder_id)
        file = self.drive_service.files().get(fileId=file_id, fields='parents').execute()
        previous_parents = ",".join(file.get('parents'))
        
        file = self.drive_service.files().update(
            fileId=file_id,
            addParents=posted_folder_id,
            removeParents=previous_parents,
            fields='id, parents'
        ).execute()
        logger.info(f"Moved file {file_id} to Posted folder ({posted_folder_id})")

if __name__ == '__main__':
    reader = DriveReader()
    print("DriveReader initialized. Check logs for authentication status.")
