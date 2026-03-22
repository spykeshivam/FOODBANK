import gspread
from google.oauth2.service_account import Credentials
import config

def check_connection():
    print("--- DIAGNOSTIC CHECK ---")
    
    # Connect
    creds = Credentials.from_service_account_file(
        config.CREDENTIALS_FILE, 
        scopes=config.SCOPES
    )
    client = gspread.authorize(creds)
    
    # Open the sheet defined in your config
    try:
        spreadsheet = client.open_by_key(config.LOGIN_SHEET_ID)
        worksheet = spreadsheet.sheet1
        
        print(f"1. TARGET SPREADSHEET:  '{spreadsheet.title}'")
        print(f"2. TARGET TAB NAME:     '{worksheet.title}'")
        print(f"3. CURRENT ROW COUNT:   {len(worksheet.get_all_values())}")
        print(f"4. SPREADSHEET ID:      {config.LOGIN_SHEET_ID}")
        
        print("\nACTION: Please check if the name above matches the file open in your browser.")
        
    except Exception as e:
        print(f"ERROR: Could not connect. Reason: {e}")

if __name__ == "__main__":
    check_connection()