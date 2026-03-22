import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, timedelta
import config  # Importing your config file

def clean_duplicates():
    print("Connecting to Google Sheets...")
    
    # 1. Setup Connection
    creds = Credentials.from_service_account_file(
        config.CREDENTIALS_FILE, 
        scopes=config.SCOPES
    )
    client = gspread.authorize(creds)
    
    # Open the Login Sheet
    sheet = client.open_by_key(config.LOGIN_SHEET_ID).sheet1
    
    # 2. Fetch Data
    print("Fetching existing records...")
    data = sheet.get_all_records()
    
    if not data:
        print("Sheet is empty. Nothing to clean.")
        return

    df = pd.DataFrame(data)
    original_count = len(df)
    
    # 3. Standardize Timestamp Parsing
    df['Parsed'] = pd.to_datetime(df['Timestamp'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    df['Parsed'] = df['Parsed'].fillna(pd.to_datetime(df['Timestamp'], format='%m/%d/%Y %H:%M:%S', errors='coerce'))
    
    # Drop rows where timestamp couldn't be parsed
    df = df.dropna(subset=['Parsed'])
    
    # 4. Sort Data (CHANGED)
    # strictly sort by time to keep the log chronological
    df = df.sort_values(by=['Parsed'])
    
    # 5. Filter Duplicates (The 5-Minute Rule)
    clean_rows = []
    last_seen = {} # Stores { 'username': last_kept_timestamp }

    for index, row in df.iterrows():
        user = row['Username']
        current_time = row['Parsed']
        
        if user not in last_seen:
            # First time seeing this user, keep the row
            clean_rows.append(row)
            last_seen[user] = current_time
        else:
            last_time = last_seen[user]
            time_diff = current_time - last_time
            
            # If the gap is greater than 5 minutes, it's a valid new login
            if time_diff > timedelta(minutes=5):
                clean_rows.append(row)
                last_seen[user] = current_time
            else:
                # Less than 5 mins? It's a duplicate.
                print(f"Duplicate found: User {user} at {current_time} (Diff: {time_diff}) - SKIPPING")
                continue

    # Create cleaned DataFrame
    df_clean = pd.DataFrame(clean_rows)
    
    # Remove the helper 'Parsed' column before uploading
    df_final = df_clean.drop(columns=['Parsed'])
    
    new_count = len(df_final)
    removed_count = original_count - new_count
    
    print(f"Analysis Complete.")
    print(f"Original Rows: {original_count}")
    print(f"Cleaned Rows:  {new_count}")
    print(f"Duplicates Removed: {removed_count}")

    if removed_count > 0:
        confirm = input("Are you sure you want to overwrite the sheet with this cleaned data? (yes/no): ")
        if confirm.lower() == 'yes':
            print("Updating Google Sheet...")
            
            # Prepare data for upload (Header + Values)
            df_final = df_final.fillna('')
            header = df_final.columns.tolist()
            values = df_final.values.tolist()
            
            sheet.clear()
            sheet.update(range_name='A1', values=[header] + values)
            
            print("Success! Sheet has been cleaned and sorted by Time.")
        else:
            print("Operation cancelled. No changes made.")
    else:
        print("No duplicates found. Sheet is already clean.")

if __name__ == "__main__":
    clean_duplicates()