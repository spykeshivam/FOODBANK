import re
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, timedelta
import calendar
from flask_caching import Cache
from services.dashboard_utils import parse_timestamps

# Valid UK postcode pattern (case-insensitive)
_POSTCODE_RE = re.compile(
    r'^[A-Z]{1,2}[0-9][0-9A-Z]?\s[0-9][ABD-HJLNP-UW-Z]{2}$',
    re.IGNORECASE
)

def validate_postcode(postcode):
    """Returns True if postcode matches the UK postcode format."""
    return bool(_POSTCODE_RE.match((postcode or "").strip()))

# BEST PRACTICE: Import configuration from the separate config file
import config

# Initialize Cache
cache = Cache()

# Global variable to hold the client connection
_client = None

def get_client():
    """Lazily initializes and returns the Google Sheets client."""
    global _client
    if _client is None:
        # Use config variables instead of hardcoded strings
        creds = Credentials.from_service_account_file(
            config.CREDENTIALS_FILE, 
            scopes=config.SCOPES
        )
        _client = gspread.authorize(creds)
    return _client

@cache.cached(timeout=config.CACHE_DEFAULT_TIMEOUT, key_prefix='all_data')
def get_all_data_frames():
    """
    Fetches data from Google Sheets and returns Pandas DataFrames.
    Uses get_all_values() instead of get_all_records() to avoid duplicate header errors.
    """
    client = get_client()
    
    # --- 1. Fetch User Registration Data ---
    sheet1 = client.open_by_key(config.SHEET_ID).sheet1
    # Get raw values (list of lists)
    data1 = sheet1.get_all_values()
    
    if data1:
        headers1 = data1.pop(0) # Isolate the header row
        users_df = pd.DataFrame(data1, columns=headers1)
        # Drop any columns that have no header text (empty strings)
        users_df = users_df.loc[:, users_df.columns != '']
    else:
        users_df = pd.DataFrame()

    # --- 2. Fetch Login Data ---
    sheet2 = client.open_by_key(config.LOGIN_SHEET_ID).sheet1
    # Get raw values (list of lists)
    data2 = sheet2.get_all_values()
    
    if data2:
        headers2 = data2.pop(0) # Isolate the header row
        logins_df = pd.DataFrame(data2, columns=headers2)
        # Drop any columns that have no header text
        logins_df = logins_df.loc[:, logins_df.columns != '']
    else:
        logins_df = pd.DataFrame()

    return users_df, logins_df

def get_user_details(user_id):
    """Checks if a user exists and returns their details."""
    users_df, logins_df = get_all_data_frames()
    
    user_row = users_df[users_df['Username'].str.strip() == user_id]

    if not user_row.empty:
        user_data = user_row.iloc[0]
        
        user_logins = logins_df[logins_df['Username'].str.strip() == user_id]
        last_date = "No Last Login Date Found"
        if not user_logins.empty:
            last_entry = user_logins.iloc[-1]
            last_date = f"{last_entry.get('Timestamp', 'N/A')} {last_entry.get('Day', '')}".strip()

        postcode = user_data.get("Postcode", "")
        return {
            "message": f"User ID '{user_id}' exists!",
            "exists": True,
            "postcode_valid": validate_postcode(postcode),
            "details": {
                "First Name": user_data.get("First Name", ""),
                "Last Name": user_data.get("Surname", ""),
                "Date of Birth": user_data.get("Date of Birth", ""),
                "Number of Adults in Household": user_data.get("Number of Adults in Household", ""),
                "Number of Children in Household": user_data.get("Number of Children in Household", ""),
                "Last Login Date": last_date,
            },
            "show_login_button": True
        }
    return {"message": f"User ID '{user_id}' does not exist.", "exists": False}

def append_login(user_id):
    """
    Appends a new login record with debug logging.
    """
    print(f"\n[DEBUG] --- Starting append_login for user: {user_id} ---")
    
    try:
        client = get_client()
        #
        login_sheet = client.open_by_key(config.LOGIN_SHEET_ID).worksheet("Form Responses 1")
        print("[DEBUG] Connected to Google Sheet successfully.")
        
        # Fetch fresh data
        existing_records = login_sheet.get_all_records()
        print(f"[DEBUG] Fetched {len(existing_records)} existing rows from sheet.")
        
        now = datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
        day_name = calendar.day_name[now.weekday()]
        
        # Debouncing Check
        user_logins = [r for r in existing_records if r['Username'] == user_id]
        if user_logins:
            last_login_record = user_logins[-1]
            last_ts_str = last_login_record['Timestamp']
            print(f"[DEBUG] Found previous login for this user at: {last_ts_str}")
            
            try:
                try:
                    last_ts = datetime.strptime(last_ts_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    last_ts = datetime.strptime(last_ts_str, "%m/%d/%Y %H:%M:%S")

                time_diff = now - last_ts
                print(f"[DEBUG] Time difference is: {time_diff}")

                if time_diff < timedelta(minutes=5):
                    print("[DEBUG] BLOCKING: Login occurred less than 5 minutes ago.")
                    print("[DEBUG] --- End append_login (Skipped) ---\n")
                    return True, "Login Successful! (Duplicate entry skipped)"
                else:
                    print("[DEBUG] PASSED: Last login was > 5 mins ago.")
            except Exception as e:
                print(f"[DEBUG] Timestamp parse error, skipping duplicate check: {e}")
        else:
            print("[DEBUG] No previous logins found for this user.")

        # Attempting to Write
        row_data = [timestamp_str, user_id, day_name]
        print(f"[DEBUG] Attempting to append row: {row_data}")
        
        # CAPTURE THE RESPONSE
        response = login_sheet.append_row(row_data) 
        
        # PRINT THE EXACT LOCATION
        updates = response.get('updates', {})
        updated_range = updates.get('updatedRange', 'Unknown Range')
        print(f"[DEBUG] SUCCESS: Data written to range: {updated_range}")
        
        cache.delete('all_data')
        print("[DEBUG] Cache cleared.")
        print("[DEBUG] --- End append_login (Success) ---\n")
        
        return True, "Login Successful!"

    except Exception as e:
        print(f"[DEBUG] CRITICAL ERROR: {str(e)}")
        print("[DEBUG] --- End append_login (Failed) ---\n")
        return False, f"Server Error: {str(e)}"

def perform_search(search_type, name="", postcode="", dob=""):
    """Searches the cached dataframe for users."""
    users_df, _ = get_all_data_frames()
    results = []

    if users_df.empty:
        return [], "No data available."

    filtered = pd.DataFrame()

    if search_type == "name" and name:
        mask = users_df["First Name"].str.contains(name, case=False, na=False) | \
               users_df["Surname"].str.contains(name, case=False, na=False)
        filtered = users_df[mask]

    elif search_type == "postcode" and postcode:
        mask = users_df["Postcode"].astype(str).str.contains(postcode, case=False, na=False)
        filtered = users_df[mask]

    elif search_type == "dob" and dob:
        mask = users_df["Date of Birth"].astype(str) == dob
        filtered = users_df[mask]
    else:
        return [], "Invalid search parameters."

    if filtered.empty:
        return [], "No results found."

    for _, row in filtered.iterrows():
        first_name = row.get('First Name', 'Unknown')
        surname = row.get('Surname', 'Unknown')
        postcode = row.get('Postcode', 'N/A')
        dob = row.get('Date of Birth', 'Unknown')
        username = row.get('Username', 'NULL Username')
        res_str = f"{first_name} {surname} - {postcode} - {dob} - Username: {username}"
        results.append(res_str)

    return results, None

def update_postcode(user_id, new_postcode):
    """
    Finds the user's row in the registrations sheet and updates their Postcode cell.
    Returns (success: bool, message: str).
    """
    if not validate_postcode(new_postcode):
        return False, "Invalid postcode format."

    normalised = new_postcode.strip().upper()
    # Ensure exactly one space between outward and inward codes
    normalised = re.sub(r'\s+', ' ', normalised)

    try:
        client = get_client()
        sheet = client.open_by_key(config.SHEET_ID).sheet1
        all_values = sheet.get_all_values()

        if not all_values:
            return False, "Registration sheet is empty."

        headers = all_values[0]

        try:
            postcode_col = headers.index('Postcode') + 1   # 1-indexed
        except ValueError:
            return False, "Postcode column not found in sheet."

        try:
            username_col = headers.index('Username') + 1
        except ValueError:
            return False, "Username column not found in sheet."

        for row_idx, row in enumerate(all_values[1:], start=2):
            if len(row) >= username_col and row[username_col - 1].strip() == user_id:
                sheet.update_cell(row_idx, postcode_col, normalised)
                cache.delete('all_data')
                return True, "Postcode updated successfully."

        return False, "User not found in registrations sheet."

    except Exception as e:
        return False, f"Server error: {str(e)}"


