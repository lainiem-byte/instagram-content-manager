import os
import logging
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Set up dedicated error logging for sheets as requested
os.makedirs("logs", exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
sheets_logger_custom = logging.getLogger('sheets_logger')
error_handler = logging.FileHandler('logs/sheets_errors.log')
error_handler.setLevel(logging.ERROR)
sheets_logger_custom.addHandler(error_handler)

SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

class SheetsLogger:
    def __init__(self):
        self.creds = None
        self.sheets_service = None
        self.drive_service = None
        self._authenticate()

    def _authenticate(self):
        json_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        if not json_path or not os.path.exists(json_path):
            sheets_logger_custom.error(f"Service account JSON not found at: {json_path}")
            return
        try:
            self.creds = service_account.Credentials.from_service_account_file(
                json_path, scopes=SCOPES
            )
            self.sheets_service = build('sheets', 'v4', credentials=self.creds)
            self.drive_service = build('drive', 'v3', credentials=self.creds)
            
            # Log the service account email to help user verify sharing permissions
            sa_email = self.creds.service_account_email
            sheets_logger_custom.info(f"Authenticated as: {sa_email}")
            print(f"DEBUG: Authenticated with Google as: {sa_email}")
            
        except Exception as e:
            sheets_logger_custom.error(f"Failed to authenticate sheets logger: {e}")

    def get_or_create_sheet(self, parent_folder_id, sheet_name="Instagram Post Log", direct_sheet_id=None):
        if direct_sheet_id:
            sheets_logger_custom.info(f"Using direct sheet ID: {direct_sheet_id}")
            return direct_sheet_id
            
        # Locate existing
        query = f"'{parent_folder_id}' in parents and name = '{sheet_name}' and mimeType = 'application/vnd.google-apps.spreadsheet' and trashed = false"
        try:
            results = self.drive_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            files = results.get('files', [])
            if files:
                return files[0]['id']
            
            # Auto-create the sheet
            print(f"\n[ATTENTION] The Google Sheet '{sheet_name}' was not found. Creating it now...")
            
            # Create it
            sheet_metadata = {
                'properties': {'title': sheet_name}
            }
            spreadsheet = self.sheets_service.spreadsheets().create(body=sheet_metadata, fields='spreadsheetId').execute()
            sheet_id = spreadsheet.get('spreadsheetId')
            
            # Move it to the correct folder
            file = self.drive_service.files().get(fileId=sheet_id, fields='parents').execute()
            previous_parents = ",".join(file.get('parents', []))
            self.drive_service.files().update(
                fileId=sheet_id,
                addParents=parent_folder_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            
            # Write Header
            header_values = [["Date Posted", "Account", "Image Filename", "Post Type", "Caption Used", "Hashtags", "Post ID", "Status", "Notes"]]
            body = {'values': header_values}
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=sheet_id, range="A1",
                valueInputOption="RAW", body=body).execute()
                
            sheets_logger_custom.info(f"Created new sheet '{sheet_name}' and wrote headers.")
            return sheet_id
        except Exception as e:
            sheets_logger_custom.error(f"Error getting or creating sheet: {e}")
            return None

    def log_post(self, sheet_id, date_posted, account, filename, post_type, caption, hashtags, post_id, status, notes):
        if not sheet_id or not self.sheets_service:
            sheets_logger_custom.error("No sheet ID or service available to log to.")
            return
            
        values = [
            [date_posted, account, filename, post_type, caption, hashtags, post_id, status, notes]
        ]
        body = {'values': values}
        try:
            # First, try to get the spreadsheet metadata to find the first sheet's name
            spreadsheet = self.sheets_service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            sheet_name = spreadsheet['sheets'][0]['properties']['title']
            
            # Use the actual sheet name for append (quoted to handle spaces)
            target_range = f"'{sheet_name}'!A:I"
            
            result = self.sheets_service.spreadsheets().values().append(
                spreadsheetId=sheet_id, 
                range=target_range,
                valueInputOption="USER_ENTERED", 
                body=body
            ).execute()
            sheets_logger_custom.info(f"Appended log to sheet {sheet_id} (Sheet: {sheet_name}).")
        except Exception as e:
            sheets_logger_custom.error(f"Failed to append to sheet: {e}")
            # Fallback to simple range if metadata fetch fails
            try:
                self.sheets_service.spreadsheets().values().append(
                    spreadsheetId=sheet_id, 
                    range="A:I",
                    valueInputOption="USER_ENTERED", 
                    body=body
                ).execute()
            except:
                pass

if __name__ == '__main__':
    print("SheetsLogger initialized.")
