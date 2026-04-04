import matplotlib
matplotlib.use('Agg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.patches as mpatches
import pandas as pd
import io

from services.dashboard_utils import find_column, parse_timestamps

# Consistent colour palette matching the Plotly dashboard
_BLUE   = '#636EFA'
_RED    = '#EF553B'
_GREEN  = '#00CC96'
_PURPLE = '#AB63FA'
_ORANGE = '#FFA15A'


# ── internal helpers ───────────────────────────────────────────────────────

def _parse_logins_timestamps(logins_df):
    """Return logins_df with a 'Parsed' datetime column, dropping unparseable rows."""
    if 'Timestamp' not in logins_df.columns:
        return pd.DataFrame()
    return parse_timestamps(logins_df.copy(), 'Timestamp', 'Parsed').dropna(subset=['Parsed'])


def _section_page(title):
    """A full-page section divider with a coloured banner and the section title."""
    fig = Figure(figsize=(8.5, 11))
    ax = fig.add_subplot(111)
    fig.patch.set_facecolor('white')

    # Coloured banner across the top third
    ax.axhspan(0.6, 1.0, xmin=0, xmax=1, color='#0b2a5b', zorder=0)

    ax.text(0.5, 0.78, title,
            ha='center', va='center',
            fontsize=34, fontweight='bold', color='white',
            transform=ax.transAxes)

    ax.text(0.5, 0.42,
            'Foodbank Dashboard Report',
            ha='center', va='center',
            fontsize=14, color='#4c5870',
            transform=ax.transAxes)

    ax.axis('off')
    return fig


def _save(fig, pdf):
    """Render a Figure to the PdfPages object."""
    FigureCanvas(fig)
    pdf.savefig(fig)


# ── Section 1: Overview ────────────────────────────────────────────────────

def _registrations_trend(users_df):
    ts_col = find_column(users_df, ['Timestamp'], contains=True)
    if not ts_col or users_df.empty:
        return None
    df = users_df.copy()
    df['Parsed'] = pd.to_datetime(df[ts_col], errors='coerce')
    df = df.dropna(subset=['Parsed'])
    if df.empty:
        return None

    counts = df.groupby(df['Parsed'].dt.date).size().sort_index()

    fig = Figure(figsize=(10, 5))
    ax = fig.add_subplot(111)
    bars = ax.bar(counts.index.astype(str), counts.values, color=_BLUE, edgecolor='white')
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.05, str(int(h)),
                ha='center', va='bottom', fontsize=8)
    ax.set_title('Registrations Trend', fontweight='bold', pad=12)
    ax.set_xlabel('Date')
    ax.set_ylabel('Registrations')
    ax.tick_params(axis='x', rotation=45)
    ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    return fig


def _logins_trend(logins_df):
    df = _parse_logins_timestamps(logins_df)
    if df.empty:
        return None

    counts = df.groupby(df['Parsed'].dt.date).size().sort_index()

    fig = Figure(figsize=(10, 5))
    ax = fig.add_subplot(111)
    ax.plot(counts.index.astype(str), counts.values, marker='o', color=_BLUE, linewidth=2)
    for x, y in zip(counts.index.astype(str), counts.values):
        ax.text(x, y + 0.2, str(y), ha='center', va='bottom', fontsize=8)
    ax.set_title('Logins Trend', fontweight='bold', pad=12)
    ax.set_xlabel('Date')
    ax.set_ylabel('Login Count')
    ax.tick_params(axis='x', rotation=45)
    ax.grid(True, alpha=0.3)
    ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    return fig


# ── Section 2: People & Needs ──────────────────────────────────────────────

def _gender_chart(users_df):
    col = find_column(users_df, ['Sex', 'Gender'], contains=True)
    if not col:
        return None
    counts = users_df[col].dropna().value_counts()
    if counts.empty:
        return None
    fig = Figure(figsize=(7, 6))
    ax = fig.add_subplot(111)
    ax.pie(counts, labels=counts.index, autopct='%1.1f%%', startangle=90,
           colors=[_BLUE, _RED, _GREEN, _PURPLE, _ORANGE])
    ax.set_title('Sex Distribution', fontweight='bold', pad=12)
    fig.tight_layout()
    return fig


def _age_chart(users_df):
    col = find_column(users_df, ['Date of Birth', 'DOB'], contains=True)
    if not col:
        return None
    df = users_df.copy()
    df['DOB_Parsed'] = pd.to_datetime(df[col], errors='coerce')
    df['Age'] = (pd.Timestamp.now() - df['DOB_Parsed']).dt.days // 365
    ages = df['Age'].dropna()
    if ages.empty:
        return None
    fig = Figure(figsize=(8, 5))
    ax = fig.add_subplot(111)
    ax.hist(ages, bins=10, color=_BLUE, edgecolor='white')
    ax.set_title('Age Distribution', fontweight='bold', pad=12)
    ax.set_xlabel('Age')
    ax.set_ylabel('Users')
    ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    return fig


def _language_chart(users_df):
    col = find_column(users_df,
                      ['Primary Language', 'First Language', 'Main Language', 'Language'],
                      contains=True)
    if not col:
        return None
    counts = (users_df[col].dropna().astype(str).str.strip()
              .pipe(lambda s: s[s != '']).value_counts().head(12))
    if counts.empty:
        return None
    fig = Figure(figsize=(9, 5))
    ax = fig.add_subplot(111)
    ax.bar(counts.index.astype(str), counts.values, color=_PURPLE, edgecolor='white')
    ax.set_title('Primary Language', fontweight='bold', pad=12)
    ax.set_xlabel('Language')
    ax.set_ylabel('Users')
    ax.tick_params(axis='x', rotation=45)
    ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    return fig


def _dietary_chart(users_df):
    col = find_column(users_df,
                      ['Dietary Requirements', 'Dietary Requirement', 'Dietary'],
                      contains=True)
    if not col:
        return None
    series = (users_df[col].dropna().astype(str).str.strip()
              .str.split(r'[;,/]').explode().str.strip())
    series = series[series != '']
    counts = series.value_counts().head(12)
    if counts.empty:
        return None
    fig = Figure(figsize=(9, 5))
    ax = fig.add_subplot(111)
    ax.bar(counts.index.astype(str), counts.values, color=_ORANGE, edgecolor='white')
    ax.set_title('Dietary Requirements', fontweight='bold', pad=12)
    ax.set_xlabel('Requirement')
    ax.set_ylabel('Users')
    ax.tick_params(axis='x', rotation=45)
    ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    return fig


def _household_chart(users_df):
    adult_col = find_column(users_df,
                            ['Number of Adults in Household', 'Adults in Household', 'Adults'],
                            contains=True)
    child_col = find_column(users_df,
                            ['Number of Children in Household', 'Children in Household', 'Children'],
                            contains=True)
    if not adult_col and not child_col:
        return None

    fig = Figure(figsize=(9, 5))
    ax = fig.add_subplot(111)
    legend_patches = []
    all_keys = set()

    if adult_col:
        adults = pd.to_numeric(users_df[adult_col], errors='coerce').dropna()
        adult_counts = adults.value_counts().sort_index()
        all_keys.update(adult_counts.index.astype(int))

    if child_col:
        children = pd.to_numeric(users_df[child_col], errors='coerce').dropna()
        child_counts = children.value_counts().sort_index()
        all_keys.update(child_counts.index.astype(int))

    sorted_keys = sorted(all_keys)
    x = range(len(sorted_keys))
    key_to_pos = {k: i for i, k in enumerate(sorted_keys)}

    if adult_col:
        adult_vals = [adult_counts.get(k, 0) for k in sorted_keys]
        ax.bar([i - 0.2 for i in x], adult_vals, width=0.35, color=_BLUE, label='Adults')
        legend_patches.append(mpatches.Patch(color=_BLUE, label='Adults'))

    if child_col:
        child_vals = [child_counts.get(k, 0) for k in sorted_keys]
        ax.bar([i + 0.2 for i in x], child_vals, width=0.35, color=_RED, label='Children')
        legend_patches.append(mpatches.Patch(color=_RED, label='Children'))

    ax.set_xticks(list(x))
    ax.set_xticklabels([str(k) for k in sorted_keys])
    if legend_patches:
        ax.legend(handles=legend_patches)
    ax.set_title('Household Adults vs Children', fontweight='bold', pad=12)
    ax.set_xlabel('Count in Household')
    ax.set_ylabel('Households')
    ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    return fig


def _household_total_chart(users_df):
    adult_col = find_column(users_df,
                            ['Number of Adults in Household', 'Adults in Household', 'Adults'],
                            contains=True)
    child_col = find_column(users_df,
                            ['Number of Children in Household', 'Children in Household', 'Children'],
                            contains=True)
    if not adult_col or not child_col or users_df.empty:
        return None
    adults   = pd.to_numeric(users_df[adult_col], errors='coerce')
    children = pd.to_numeric(users_df[child_col], errors='coerce')
    total    = adults.fillna(0) + children.fillna(0)
    total    = total[~(adults.isna() & children.isna())]
    if total.empty:
        return None
    counts = total.value_counts().sort_index()
    fig = Figure(figsize=(8, 5))
    ax = fig.add_subplot(111)
    ax.bar(counts.index.astype(int).astype(str), counts.values, color=_GREEN, edgecolor='white')
    ax.set_title('Total Household Size', fontweight='bold', pad=12)
    ax.set_xlabel('Household Size')
    ax.set_ylabel('Households')
    ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    return fig


# ── Section 3: Engagement & Outreach ──────────────────────────────────────

def _new_vs_returning_chart(logins_df):
    df = _parse_logins_timestamps(logins_df)
    username_col = find_column(df, ['Username'], contains=False) if not df.empty else None
    if df.empty or not username_col:
        return None

    df = df.dropna(subset=[username_col]).copy()
    df['LoginDate'] = df['Parsed'].dt.date
    first = df.groupby(username_col)['LoginDate'].min().rename('FirstDate')
    df = df.join(first, on=username_col)
    df['Status'] = df.apply(
        lambda r: 'New' if r['LoginDate'] == r['FirstDate'] else 'Returning', axis=1
    )

    pivot = (df.groupby(['LoginDate', 'Status']).size()
               .unstack(fill_value=0)
               .sort_index())

    new_vals = pivot.get('New',       pd.Series(0, index=pivot.index))
    ret_vals = pivot.get('Returning', pd.Series(0, index=pivot.index))
    labels   = [str(d) for d in pivot.index]
    x        = list(range(len(pivot)))

    fig = Figure(figsize=(11, 5))
    ax = fig.add_subplot(111)
    ax.bar(x, new_vals.values, color=_BLUE,  label='New')
    ax.bar(x, ret_vals.values, color=_RED,   label='Returning', bottom=new_vals.values)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right')
    ax.set_title('New vs Returning Logins', fontweight='bold', pad=12)
    ax.set_xlabel('Date')
    ax.set_ylabel('Logins')
    ax.legend()
    ax.spines[['top', 'right']].set_visible(False)
    fig.tight_layout()
    return fig


# ── PDF builder ────────────────────────────────────────────────────────────

def create_dashboard_pdf(users_df, logins_df):
    """
    Builds a PDF with one section per dashboard tab.
    Each section starts with a labelled divider page followed by its plots.
    Plots that have no data are silently skipped.
    """
    sections = [
        {
            "title": "Overview",
            "plots": [
                _registrations_trend(users_df),
                _logins_trend(logins_df),
            ],
        },
        {
            "title": "People & Needs",
            "plots": [
                _gender_chart(users_df),
                _age_chart(users_df),
                _language_chart(users_df),
                _dietary_chart(users_df),
                _household_chart(users_df),
                _household_total_chart(users_df),
            ],
        },
        {
            "title": "Engagement & Outreach",
            "plots": [
                _new_vs_returning_chart(logins_df),
            ],
        },
    ]

    buffer = io.BytesIO()
    with PdfPages(buffer) as pdf:
        for section in sections:
            plots = [p for p in section["plots"] if p is not None]
            if not plots:
                continue
            _save(_section_page(section["title"]), pdf)
            for fig in plots:
                _save(fig, pdf)

    buffer.seek(0)
    return buffer
