import gspread
from google.oauth2.service_account import Credentials
from flask import Flask, request, render_template, jsonify, send_file
from datetime import datetime
import calendar
import io
import base64
import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages



#Use non interactive backend - may cause problems otherwise
matplotlib.use('Agg')


app = Flask(__name__)

#Google Sheets Setup
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
CREDS = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
CLIENT = gspread.authorize(CREDS)

#Registration Google Sheet ID and Initialization
SHEET_ID = ""
SHEET = CLIENT.open_by_key(SHEET_ID)
ROWS = SHEET.sheet1.get_all_records()  #Retrieve all rows as dictionaries
USERNAME_VALUES = {row["Username"].strip(): row for row in ROWS}  
USERNAME_COUNT = len(USERNAME_VALUES)

print(f"Total unique usernames: {USERNAME_COUNT}")

#Initialize Login Sheet 
LOGIN_SHEET_ID = ""
SECOND_SHEET = CLIENT.open_by_key(LOGIN_SHEET_ID)
LOGIN_ROWS = SECOND_SHEET.sheet1.get_all_records()

#Flask Routes
@app.route("/login")
def index():
    return render_template("index.html") 

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/check_user", methods=["POST"])
def check_user():
    global ROWS, LOGIN_ROWS
    ROWS = CLIENT.open_by_key(SHEET_ID).sheet1.get_all_records()
    LOGIN_ROWS = CLIENT.open_by_key(LOGIN_SHEET_ID).sheet1.get_all_records()
    
    graphs = {}
    SHEET = CLIENT.open_by_key(SHEET_ID)
    ROWS = SHEET.sheet1.get_all_records()  #Retrieve all rows as dictionaries
    USERNAME_VALUES = {row["Username"].strip(): row for row in ROWS}
    SECOND_SHEET = CLIENT.open_by_key(LOGIN_SHEET_ID)
    LOGIN_ROWS = SECOND_SHEET.sheet1.get_all_records()

    user_id = request.form.get("user_id").strip()  
    if user_id in USERNAME_VALUES:
        user_details = USERNAME_VALUES[user_id]

        
        last_date = "No Last Login Date Found"
        """print(LOGIN_ROWS)"""

        #Find the last login date for the user in the LOGIN_SHEET_ID
        matching_rows = [row for row in LOGIN_ROWS if row["Username"].strip() == user_id]
        if matching_rows:
            last_entry = matching_rows[-1]  # Get the last occurrence (from the bottom)
            last_date = f"{last_entry['Timestamp']} {last_entry['Day']}"

        response = {
            "message": f"User ID '{user_id}' exists!",
            "exists": True,
            "details": {
                "First Name": user_details["First Name"],
                "Last Name": user_details["Surname"],
                "Date of Birth": user_details["Date of Birth"],
                "Number of Adults in Household": user_details["Number of Adults in Household"],
                "Number of Children in Household": user_details["Number of Children in Household"],
                "Last Login Date": last_date,
            },
            "show_login_button": True  
        }
    else:
        response = {"message": f"User ID '{user_id}' does not exist.", "exists": False}
    return jsonify(response)

@app.route("/log_login", methods=["POST"])
def log_login():
    global ROWS, LOGIN_ROWS
    ROWS = CLIENT.open_by_key(SHEET_ID).sheet1.get_all_records()
    LOGIN_ROWS = CLIENT.open_by_key(LOGIN_SHEET_ID).sheet1.get_all_records()
    
    graphs = {}
    user_id = request.form.get("user_id").strip()
    if user_id:
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        day_name = calendar.day_name[now.weekday()]

        #Append new login record 
        SECOND_SHEET.sheet1.append_row([timestamp, user_id, day_name])

        return jsonify({"message": "Login Successful!", "success": True})
    else:
        return jsonify({"message": "Login Error Occurred", "success": False})


@app.route("/search")
def search():
    return render_template("search.html")

@app.route("/search_user", methods=["POST"])
def search_user():
    global ROWS, LOGIN_ROWS
    ROWS = CLIENT.open_by_key(SHEET_ID).sheet1.get_all_records()
    LOGIN_ROWS = CLIENT.open_by_key(LOGIN_SHEET_ID).sheet1.get_all_records()
    
    graphs = {}
    search_type = request.form.get("search_type")
    results = []
    message = None

    if search_type == "name":
        query = request.form.get("name", "").strip()
        if query:
            results = [
                f"{row['First Name']} {row['Surname']} - {row.get('Postcode', 'N/A')} - {row['Date of Birth']} - Username: {row.get('Username', 'NULL Username')}"
                for row in ROWS
                if query.lower() in row["First Name"].lower() or query.lower() in row["Surname"].lower()
            ]
        else:
            message = "Please enter a name to search."

    elif search_type == "postcode":
        query = request.form.get("postcode", "").strip()
        if query:
            results = [
                f"{row['First Name']} {row['Surname']} - {row.get('Postcode', 'N/A')} - {row['Date of Birth']} - Username: {row.get('Username', 'NULL Username')}"
                for row in ROWS
                if query.lower() in str(row.get("Postcode", "")).lower()  # Convert Postcode to string safely
            ]
        else:
            message = "Please enter a postcode to search."

    elif search_type == "dob":
        query = request.form.get("dob", "").strip()
        if query:
            results = [
                f"{row['First Name']} {row['Surname']} - {row.get('Postcode', 'N/A')} - {row['Date of Birth']} - Username: {row.get('Username', 'NULL Username')}"
                for row in ROWS
                if query == row["Date of Birth"]
            ]
        else:
            message = "Please enter a date of birth to search."

    if not results and not message:
        message = "No results found."

    return render_template("search.html", results=results, message=message)



@app.route("/dashboard")
def dashboard():
    global ROWS, LOGIN_ROWS
    ROWS = CLIENT.open_by_key(SHEET_ID).sheet1.get_all_records()
    LOGIN_ROWS = CLIENT.open_by_key(LOGIN_SHEET_ID).sheet1.get_all_records()
    
    graphs = {}

    #Gender Distribution
    gender_counts = pd.Series([row['Sex'] for row in ROWS]).value_counts()
    fig, ax = plt.subplots(figsize=(6, 6))
    gender_counts.plot.pie(autopct='%1.1f%%', startangle=90, colors=['lightblue', 'pink'], ax=ax)
    ax.set_title('Gender Distribution')
    ax.set_ylabel('')
    gender_img = io.BytesIO()
    plt.savefig(gender_img, format='png')
    plt.close(fig)
    gender_img.seek(0)
    graphs['gender_data'] = base64.b64encode(gender_img.getvalue()).decode()



    # Convert timestamps to a DataFrame and extract dates
    df_login = pd.DataFrame(LOGIN_ROWS)
    df_login['Timestamp'] = pd.to_datetime(df_login['Timestamp'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    df_login['Timestamp'] = df_login['Timestamp'].fillna(pd.to_datetime(df_login['Timestamp'], format='%m/%d/%Y %H:%M:%S', errors='coerce'))

    # Find the last 3 unique login dates
    df_login['Date'] = df_login['Timestamp'].dt.date  # Extract only the date
    last_3_dates = df_login['Date'].drop_duplicates().sort_values(ascending=False).head(3)

    # Group by date and count logins for the last 3 unique dates
    login_counts = df_login[df_login['Date'].isin(last_3_dates)].groupby('Date').size()

    # Plot the login activity
    fig, ax = plt.subplots(figsize=(8, 6))
    bars = login_counts.sort_index().plot(kind='bar', color='dodgerblue', edgecolor='black', ax=ax)
    ax.set_title('Login Activity (Last 3 Active Days)')
    ax.set_xlabel('Date')
    ax.set_ylabel('Login Count')
    ax.set_xticklabels(login_counts.index, rotation=45)

    # Add count as text on top of each bar
    for i, bar in enumerate(bars.patches):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., height,
                f'{int(height)}',  # Display the count as text
                ha='center', va='bottom', fontsize=10)

    plt.tight_layout()

    # Save the plot as an image
    login_img = io.BytesIO()
    plt.savefig(login_img, format='png', bbox_inches='tight')
    plt.close(fig)
    login_img.seek(0)
    graphs['login_data'] = base64.b64encode(login_img.getvalue()).decode()
    #Age Distribution
    df = pd.DataFrame(ROWS)
    df['Date of Birth'] = pd.to_datetime(df['Date of Birth'], errors='coerce')
    df = df.dropna(subset=['Date of Birth'])
    df['Age'] = (pd.Timestamp.now() - df['Date of Birth']).dt.days // 365
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.hist(df['Age'].dropna(), bins=10, color='skyblue', edgecolor='black')
    ax.set_title('Age Distribution')
    ax.set_xlabel('Age')
    ax.set_ylabel('Number of Users')
    age_img = io.BytesIO()
    plt.savefig(age_img, format='png')
    plt.close(fig)
    age_img.seek(0)
    graphs['age_data'] = base64.b64encode(age_img.getvalue()).decode()

   

    #English Speaking Ability
    english_speaking_counts = pd.Series(
        [row['How would you rate your ability in speaking English?'] for row in ROWS if 'How would you rate your ability in speaking English?' in row]
    ).value_counts()
    fig, ax = plt.subplots(figsize=(8, 6))
    english_speaking_counts.sort_index().plot.bar(color='lightgreen', edgecolor='black', ax=ax)
    ax.set_title('English Speaking Ability')
    ax.set_xlabel('Rating')
    ax.set_ylabel('Number of Users')
    english_img = io.BytesIO()
    plt.savefig(english_img, format='png')
    plt.close(fig)
    english_img.seek(0)
    graphs['english_data'] = base64.b64encode(english_img.getvalue()).decode()
    plt.tight_layout()

    #Ethnicity Distribution
    ethnicity_counts = pd.Series([row['Ethnicity'] for row in ROWS if 'Ethnicity' in row]).value_counts()
    fig, ax = plt.subplots(figsize=(12, 14)) 
    ethnicity_counts.plot.bar(color='lightcoral', edgecolor='black', ax=ax)
    ax.set_title('Ethnicity Distribution')
    ax.set_xlabel('Ethnicity')
    ax.set_ylabel('Number of Users')
    ethnicity_img = io.BytesIO()
    plt.savefig(ethnicity_img, format='png')
    plt.close(fig)
    ethnicity_img.seek(0)
    graphs['ethnicity_data'] = base64.b64encode(ethnicity_img.getvalue()).decode()
    plt.tight_layout()

    #Right to Work Status
    right_to_work_counts = pd.Series(
        [row['Right to work in the UK for yourself'] for row in ROWS if 'Right to work in the UK for yourself' in row]
    ).value_counts()
    fig, ax = plt.subplots(figsize=(12, 8)) 
    right_to_work_counts.plot.pie(autopct='%1.1f%%', startangle=90, colors=['gold', 'lightgreen', 'lightblue'], ax=ax)
    ax.set_title('Right to Work Status')
    ax.set_ylabel('')
    work_img = io.BytesIO()
    plt.savefig(work_img, format='png')
    plt.close(fig)
    work_img.seek(0)
    graphs['work_data'] = base64.b64encode(work_img.getvalue()).decode()
    plt.tight_layout()

    # Convert timestamps to a DataFrame and extract dates
    df_registration = pd.DataFrame(ROWS)  # Assuming ROWS contains registration data
    df_registration['Timestamp'] = pd.to_datetime(df_registration['Timestamp'], format='%m/%d/%Y %H:%M:%S', errors='coerce')
    df_registration['Timestamp'] = df_registration['Timestamp'].fillna(pd.to_datetime(df_registration['Timestamp'], format='%m/%d/%Y %H:%M:%S', errors='coerce'))

    # Find the last 3 unique registration dates
    df_registration['Date'] = df_registration['Timestamp'].dt.date  # Extract only the date
    last_3_dates = df_registration['Date'].drop_duplicates().sort_values(ascending=False).head(3)
    print(last_3_dates)
    # Group by date and count registrations for the last 3 unique dates
    registration_counts = df_registration[df_registration['Date'].isin(last_3_dates)].groupby('Date').size()

    # Plot the registration activity
    fig, ax = plt.subplots(figsize=(8, 6))
    bars = registration_counts.sort_index().plot(kind='bar', color='dodgerblue', edgecolor='black', ax=ax)
    ax.set_title('Registration Activity (Last 3 Active Days)')
    ax.set_xlabel('Date')
    ax.set_ylabel('Registration Count')
    ax.set_xticklabels(registration_counts.index, rotation=45)

    # Add count as text on top of each bar
    for i, bar in enumerate(bars.patches):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2., height,
                f'{int(height)}',  # Display the count as text
                ha='center', va='bottom', fontsize=10)

    plt.tight_layout()

    # Save the plot as an image
    registration_img = io.BytesIO()
    plt.savefig(registration_img, format='png', bbox_inches='tight')
    plt.close(fig)
    registration_img.seek(0)
    graphs['registration_data'] = base64.b64encode(registration_img.getvalue()).decode()
    

    #Referral Sources
    referral_sources_counts = pd.Series([row['How did you hear about us?'] for row in ROWS if 'How did you hear about us?' in row]).value_counts()
    fig, ax = plt.subplots(figsize=(12, 14))
    referral_sources_counts.plot.bar(color='plum', edgecolor='black', ax=ax)
    ax.set_title('Referral Sources')
    ax.set_xlabel('Source')
    ax.set_ylabel('Number of Users')
    referral_img = io.BytesIO()
    plt.savefig(referral_img, format='png')
    plt.close(fig)
    referral_img.seek(0)
    graphs['referral_data'] = base64.b64encode(referral_img.getvalue()).decode()
    plt.tight_layout()

    #Contact Agreement
    contact_agreement_counts = pd.Series(
        [row['Are you happy for us to contact you via email/WhatsApp about other services?'] for row in ROWS if 'Are you happy for us to contact you via email/WhatsApp about other services?' in row]
    ).value_counts()
    fig, ax = plt.subplots(figsize=(8, 6))
    contact_agreement_counts.plot.pie(autopct='%1.1f%%', startangle=90, colors=['lightgreen', 'lightcoral'], ax=ax)
    ax.set_title('Contact Agreement')
    ax.set_ylabel('')
    contact_img = io.BytesIO()
    plt.savefig(contact_img, format='png')
    plt.close(fig)
    contact_img.seek(0)
    graphs['contact_data'] = base64.b64encode(contact_img.getvalue()).decode()
    plt.tight_layout()

    return render_template("dashboard.html", **graphs)



@app.route("/download_dashboard", methods=["GET"])
def download_dashboard():
    global ROWS, LOGIN_ROWS
    ROWS = CLIENT.open_by_key(SHEET_ID).sheet1.get_all_records()
    LOGIN_ROWS = CLIENT.open_by_key(LOGIN_SHEET_ID).sheet1.get_all_records()
    
    graphs = {}
    pdf_buffer = io.BytesIO()

    with PdfPages(pdf_buffer) as pdf:
        # Gender Distribution
        gender_counts = pd.Series([row['Sex'] for row in ROWS]).value_counts()
        fig, ax = plt.subplots(figsize=(6, 6))
        gender_counts.plot.pie(autopct='%1.1f%%', startangle=90, colors=['lightblue', 'pink'], ax=ax)
        ax.set_title('Gender Distribution')
        ax.set_ylabel('')
        pdf.savefig(fig)
        plt.close(fig)

        # Age Distribution
        df = pd.DataFrame(ROWS)
        df['Date of Birth'] = pd.to_datetime(df['Date of Birth'], errors='coerce')
        df['Age'] = (pd.Timestamp.now() - df['Date of Birth']).dt.days // 365
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.hist(df['Age'].dropna(), bins=10, color='skyblue', edgecolor='black')
        ax.set_title('Age Distribution')
        ax.set_xlabel('Age')
        ax.set_ylabel('Number of Users')
        pdf.savefig(fig)
        plt.close(fig)

        # English Speaking Ability
        english_speaking_counts = pd.Series(
            [row['How would you rate your ability in speaking English?'] for row in ROWS if 'How would you rate your ability in speaking English?' in row]
        ).value_counts()
        fig, ax = plt.subplots(figsize=(8, 6))
        english_speaking_counts.sort_index().plot.bar(color='lightgreen', edgecolor='black', ax=ax)
        ax.set_title('English Speaking Ability')
        ax.set_xlabel('Rating')
        ax.set_ylabel('Number of Users')
        pdf.savefig(fig)
        plt.close(fig)

        # Ethnicity Distribution
        ethnicity_counts = pd.Series([row['Ethnicity'] for row in ROWS if 'Ethnicity' in row]).value_counts()
        fig, ax = plt.subplots(figsize=(12, 8))
        ethnicity_counts.plot.bar(color='lightcoral', edgecolor='black', ax=ax)
        ax.set_title('Ethnicity Distribution')
        ax.set_xlabel('Ethnicity')
        ax.set_ylabel('Number of Users')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # Right to Work Status
        right_to_work_counts = pd.Series(
            [row['Right to work in the UK for yourself'] for row in ROWS if 'Right to work in the UK for yourself' in row]
        ).value_counts()
        fig, ax = plt.subplots(figsize=(8, 6))
        right_to_work_counts.plot.pie(autopct='%1.1f%%', startangle=90, colors=['gold', 'lightgreen', 'lightblue'], ax=ax)
        ax.set_title('Right to Work Status')
        ax.set_ylabel('')
        pdf.savefig(fig)
        plt.close(fig)

        # Referral Sources
        referral_sources_counts = pd.Series([row['How did you hear about us?'] for row in ROWS if 'How did you hear about us?' in row]).value_counts()
        fig, ax = plt.subplots(figsize=(12, 8))
        referral_sources_counts.plot.bar(color='plum', edgecolor='black', ax=ax)
        ax.set_title('Referral Sources')
        ax.set_xlabel('Source')
        ax.set_ylabel('Number of Users')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # Contact Agreement
        contact_agreement_counts = pd.Series(
            [row['Are you happy for us to contact you via email/WhatsApp about other services?'] for row in ROWS if 'Are you happy for us to contact you via email/WhatsApp about other services?' in row]
        ).value_counts()
        fig, ax = plt.subplots(figsize=(8, 6))
        contact_agreement_counts.plot.pie(autopct='%1.1f%%', startangle=90, colors=['lightgreen', 'lightcoral'], ax=ax)
        ax.set_title('Contact Agreement')
        ax.set_ylabel('')
        pdf.savefig(fig)
        plt.close(fig)

        # Login Activity (Last 3 Active Days)
        df_login = pd.DataFrame(LOGIN_ROWS)
        df_login['Timestamp'] = pd.to_datetime(df_login['Timestamp'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
        df_login['Timestamp'] = df_login['Timestamp'].fillna(pd.to_datetime(df_login['Timestamp'], format='%m/%d/%Y %H:%M:%S', errors='coerce'))
        df_login['Date'] = df_login['Timestamp'].dt.date
        last_3_dates = df_login['Date'].drop_duplicates().sort_values(ascending=False).head(3)
        login_counts = df_login[df_login['Date'].isin(last_3_dates)].groupby('Date').size()

        fig, ax = plt.subplots(figsize=(8, 6))
        bars = login_counts.sort_index().plot(kind='bar', color='dodgerblue', edgecolor='black', ax=ax)
        ax.set_title('Login Activity (Last 3 Active Days)')
        ax.set_xlabel('Date')
        ax.set_ylabel('Login Count')
        ax.set_xticklabels(login_counts.index, rotation=45)

        # Add count as text on top of each bar
        for i, bar in enumerate(bars.patches):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height,
                    f'{int(height)}',  # Display the count as text
                    ha='center', va='bottom', fontsize=10)

        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

        # Registration Activity (Last 3 Active Days)
        df_registration = pd.DataFrame(ROWS)
        df_registration['Timestamp'] = pd.to_datetime(df_registration['Timestamp'], format='%m/%d/%Y %H:%M:%S', errors='coerce')
        df_registration['Date'] = df_registration['Timestamp'].dt.date
        last_3_dates = df_registration['Date'].drop_duplicates().sort_values(ascending=False).head(3)
        registration_counts = df_registration[df_registration['Date'].isin(last_3_dates)].groupby('Date').size()

        fig, ax = plt.subplots(figsize=(8, 6))
        bars = registration_counts.sort_index().plot(kind='bar', color='dodgerblue', edgecolor='black', ax=ax)
        ax.set_title('Registration Activity (Last 3 Active Days)')
        ax.set_xlabel('Date')
        ax.set_ylabel('Registration Count')
        ax.set_xticklabels(registration_counts.index, rotation=45)

        # Add count as text on top of each bar
        for i, bar in enumerate(bars.patches):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height,
                    f'{int(height)}',  # Display the count as text
                    ha='center', va='bottom', fontsize=10)

        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

    # Download PDF file
    pdf_buffer.seek(0)
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name="dashboard_plots.pdf",
        mimetype="application/pdf",
    )



if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
