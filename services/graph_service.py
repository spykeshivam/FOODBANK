import matplotlib
# Use Agg backend for non-GUI server environments
matplotlib.use('Agg') 
from matplotlib.figure import Figure 
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.image as mpimg
import pandas as pd
import io
import base64

def _fig_to_base64(fig):
    """Helper to convert a Matplotlib Figure object to a base64 string."""
    img = io.BytesIO()
    # Use FigureCanvas to save the figure without using pyplot
    FigureCanvas(fig).print_png(img)
    img.seek(0)
    return base64.b64encode(img.getvalue()).decode()

def generate_dashboard_plots(users_df, logins_df):
    """
    Generates dashboard plots using strictly object-oriented Matplotlib.
    """
    graphs = {}

    # 1. Gender Distribution
    if 'Sex' in users_df.columns:
        fig = Figure(figsize=(6, 6))
        ax = fig.add_subplot(111)
        
        gender_counts = users_df['Sex'].value_counts()
        ax.pie(gender_counts, labels=gender_counts.index, autopct='%1.1f%%', startangle=90, colors=['lightblue', 'pink'])
        ax.set_title('Gender Distribution')
        
        graphs['gender_data'] = _fig_to_base64(fig)
    
    # 2. Login Activity (Last 3 Active Days)
    df_log = logins_df.copy()
    # Standardize timestamp columns
    df_log['Parsed'] = pd.to_datetime(df_log['Timestamp'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    df_log['Parsed'] = df_log['Parsed'].fillna(pd.to_datetime(df_log['Timestamp'], format='%m/%d/%Y %H:%M:%S', errors='coerce'))
    df_log = df_log.dropna(subset=['Parsed'])
    
    if not df_log.empty:
        df_log['Date'] = df_log['Parsed'].dt.date
        last_3 = df_log['Date'].drop_duplicates().sort_values(ascending=False).head(3)
        counts = df_log[df_log['Date'].isin(last_3)].groupby('Date').size().sort_index()

        fig = Figure(figsize=(8, 6))
        ax = fig.add_subplot(111)
        
        bars = ax.bar(counts.index.astype(str), counts.values, color='dodgerblue', edgecolor='black')
        ax.set_title('Login Activity (Last 3 Active Days)')
        ax.set_xlabel('Date')
        ax.set_ylabel('Login Count')
        ax.tick_params(axis='x', rotation=45)
        
        # Add text labels
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height, f'{int(height)}', ha='center', va='bottom')
            
        fig.tight_layout()
        graphs['login_data'] = _fig_to_base64(fig)
    else:
        # Fallback empty plot if no data
        fig = Figure(figsize=(8, 6))
        graphs['login_data'] = _fig_to_base64(fig)

    # 3. Age Distribution
    if 'Date of Birth' in users_df.columns:
        users_df['DOB_Parsed'] = pd.to_datetime(users_df['Date of Birth'], errors='coerce')
        users_df['Age'] = (pd.Timestamp.now() - users_df['DOB_Parsed']).dt.days // 365
        
        fig = Figure(figsize=(8, 6))
        ax = fig.add_subplot(111)
        ax.hist(users_df['Age'].dropna(), bins=10, color='skyblue', edgecolor='black')
        ax.set_title('Age Distribution')
        ax.set_xlabel('Age')
        ax.set_ylabel('Users')
        
        graphs['age_data'] = _fig_to_base64(fig)

    # 4. Ethnicity Distribution
    if 'Ethnicity' in users_df.columns:
        ethnicity_counts = users_df['Ethnicity'].value_counts()
        
        fig = Figure(figsize=(10, 8))
        ax = fig.add_subplot(111)
        # Using simple bar for object-oriented approach
        ax.bar(ethnicity_counts.index.astype(str), ethnicity_counts.values, color='lightcoral', edgecolor='black')
        ax.set_title('Ethnicity Distribution')
        ax.set_xlabel('Ethnicity')
        ax.set_ylabel('Number of Users')
        # Rotate x labels for better readability
        ax.tick_params(axis='x', rotation=45) 
        
        fig.tight_layout()
        graphs['ethnicity_data'] = _fig_to_base64(fig)

    # 5. Right to Work Status
    col_work = 'Right to work in the UK for yourself'
    if col_work in users_df.columns:
        work_counts = users_df[col_work].value_counts()
        
        fig = Figure(figsize=(8, 6))
        ax = fig.add_subplot(111)
        ax.pie(work_counts, labels=work_counts.index, autopct='%1.1f%%', startangle=90, colors=['gold', 'lightgreen', 'lightblue'])
        ax.set_title('Right to Work Status')
        
        graphs['work_data'] = _fig_to_base64(fig)

    # 6. Referral Sources
    col_ref = 'How did you hear about us?'
    if col_ref in users_df.columns:
        ref_counts = users_df[col_ref].value_counts()
        
        fig = Figure(figsize=(10, 8))
        ax = fig.add_subplot(111)
        ax.bar(ref_counts.index.astype(str), ref_counts.values, color='plum', edgecolor='black')
        ax.set_title('Referral Sources')
        ax.set_xlabel('Source')
        ax.set_ylabel('Number of Users')
        ax.tick_params(axis='x', rotation=45)
        
        fig.tight_layout()
        graphs['referral_data'] = _fig_to_base64(fig)

    # 7. Contact Agreement
    col_contact = 'Are you happy for us to contact you via email/WhatsApp about other services?'
    if col_contact in users_df.columns:
        contact_counts = users_df[col_contact].value_counts()
        
        fig = Figure(figsize=(8, 6))
        ax = fig.add_subplot(111)
        ax.pie(contact_counts, labels=contact_counts.index, autopct='%1.1f%%', startangle=90, colors=['lightgreen', 'lightcoral'])
        ax.set_title('Contact Agreement')
        
        graphs['contact_data'] = _fig_to_base64(fig)

    # 8. Registration Activity (Last 3 Active Days)
    # Similar logic to Login Activity but using users_df
    df_reg = users_df.copy()
    if 'Timestamp' in df_reg.columns:
        # Clean Timestamp
        df_reg['Parsed'] = pd.to_datetime(df_reg['Timestamp'], format='%m/%d/%Y %H:%M:%S', errors='coerce')
        # Fallback format if needed
        df_reg['Parsed'] = df_reg['Parsed'].fillna(pd.to_datetime(df_reg['Timestamp'], format='%Y-%m-%d %H:%M:%S', errors='coerce'))
        df_reg = df_reg.dropna(subset=['Parsed'])
        
        if not df_reg.empty:
            df_reg['Date'] = df_reg['Parsed'].dt.date
            last_3_reg = df_reg['Date'].drop_duplicates().sort_values(ascending=False).head(3)
            reg_counts = df_reg[df_reg['Date'].isin(last_3_reg)].groupby('Date').size().sort_index()

            fig = Figure(figsize=(8, 6))
            ax = fig.add_subplot(111)
            bars = ax.bar(reg_counts.index.astype(str), reg_counts.values, color='dodgerblue', edgecolor='black')
            ax.set_title('Registration Activity (Last 3 Active Days)')
            ax.set_xlabel('Date')
            ax.set_ylabel('Registration Count')
            ax.tick_params(axis='x', rotation=45)

            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height, f'{int(height)}', ha='center', va='bottom')
            
            fig.tight_layout()
            graphs['registration_data'] = _fig_to_base64(fig)

    # 9. Total Login Activity (Line Chart)
    if not df_log.empty:
        # Group by date for all available dates
        daily_logins = df_log.groupby('Date').size().sort_index()
        
        fig = Figure(figsize=(10, 6))
        ax = fig.add_subplot(111)
        # Convert date index to string to avoid potential matplotlib date converter issues in thread-safe mode
        ax.plot(daily_logins.index.astype(str), daily_logins.values, marker='o', linestyle='-')
        
        # Add text labels for points
        for x, y in zip(daily_logins.index.astype(str), daily_logins.values):
            ax.text(x, y + 0.1, str(y), ha='center', va='bottom', fontsize=10)

        ax.set_title('Login Activity Total')
        ax.set_xlabel('Date')
        ax.set_ylabel('Login Count')
        ax.grid(True)
        # Autoformat date labels is tricky without pyplot, simple rotation is safer
        ax.tick_params(axis='x', rotation=45)
        
        fig.tight_layout()
        graphs['login_data_fin'] = _fig_to_base64(fig)
        
    # 10. English Speaking Ability
    col_eng = 'How would you rate your ability in speaking English?'
    if col_eng in users_df.columns:
        eng_counts = users_df[col_eng].value_counts()
        
        fig = Figure(figsize=(8, 6))
        ax = fig.add_subplot(111)
        # Use simple bar chart
        ax.bar(eng_counts.index.astype(str), eng_counts.values, color='lightgreen', edgecolor='black')
        ax.set_title('English Speaking Ability')
        ax.set_xlabel('Rating')
        ax.set_ylabel('Number of Users')
        
        graphs['english_data'] = _fig_to_base64(fig)

    return graphs


def create_dashboard_pdf(users_df, logins_df):
    """
    Builds a PDF report from the generated dashboard plots.
    """
    graphs = generate_dashboard_plots(users_df, logins_df)
    buffer = io.BytesIO()

    plot_order = [
        ("gender_data", "Gender Distribution"),
        ("age_data", "Age Distribution"),
        ("login_data", "Login Activity (Last 3 Active Days)"),
        ("registration_data", "Registration Activity (Last 3 Active Days)"),
        ("ethnicity_data", "Ethnicity Distribution"),
        ("work_data", "Right to Work Status"),
        ("referral_data", "Referral Sources"),
        ("contact_data", "Contact Agreement"),
        ("login_data_fin", "Login Activity Total"),
        ("english_data", "English Speaking Ability"),
    ]

    with PdfPages(buffer) as pdf:
        for key, title in plot_order:
            if key not in graphs:
                continue
            img_bytes = base64.b64decode(graphs[key])
            img = mpimg.imread(io.BytesIO(img_bytes), format="png")

            fig = Figure(figsize=(8.5, 6.5))
            ax = fig.add_subplot(111)
            ax.imshow(img)
            ax.set_title(title)
            ax.axis("off")
            fig.tight_layout()
            pdf.savefig(fig)

    buffer.seek(0)
    return buffer
