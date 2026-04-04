from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output, State, MATCH

from services import data_service
from services.dashboard_utils import (
    add_time_buckets,
    apply_date_range,
    ensure_datetime_series,
    find_column,
    parse_timestamps,
    resample_counts,
)


PLOT_TEMPLATE = "plotly_white"
DEFAULT_MARGIN = dict(l=40, r=20, t=60, b=40)
px.defaults.template = PLOT_TEMPLATE

USERS_TS_COL = "Timestamp"
LOGINS_TS_COL = "Timestamp"
USERS_PARSED_COL = "ParsedRegistration"
LOGINS_PARSED_COL = "ParsedLogin"
USERNAME_COL = "Username"


DATE_DEFAULT_END = date.today()
DATE_DEFAULT_START = DATE_DEFAULT_END - timedelta(days=90)


def _info_icon(description):
    return html.Span(
        "i",
        className="info-icon",
        title=description,
        **{"aria-label": description},
    )


def _kpi_card(label, value_id, description):
    return html.Div(
        [
            html.Div(
                [
                    html.Span(label, className="kpi-label"),
                    _info_icon(description),
                ],
                className="kpi-header",
            ),
            html.Div("0", id=value_id, className="kpi-value"),
        ],
        className="kpi-card",
    )


def _graph_card(graph_id, title, description):
    return html.Div(
        [
            html.Div(
                [
                    html.Span(title, className="card-title"),
                    html.Div(
                        [
                            _info_icon(description),
                            html.Button(
                                "−",
                                id={"type": "minimize-btn", "index": graph_id},
                                className="minimize-btn",
                                title="Minimize",
                                n_clicks=0,
                            ),
                        ],
                        className="card-actions",
                    ),
                ],
                className="card-header",
            ),
            html.Div(
                dcc.Graph(id=graph_id),
                id={"type": "graph-container", "index": graph_id},
            ),
        ],
        className="graph-card",
    )


def _serialize_df(df):
    if df is None:
        return None
    return df.to_json(orient="split", date_format="iso")


def _deserialize_df(payload):
    if not payload:
        return pd.DataFrame()
    try:
        df = pd.read_json(payload, orient="split", convert_dates=True)
    except ValueError:
        return pd.DataFrame()

    for col in (USERS_PARSED_COL, LOGINS_PARSED_COL):
        if col in df.columns:
            df[col] = ensure_datetime_series(df[col])
    return df


def _empty_figure(title):
    fig = go.Figure()
    fig.add_annotation(
        text="No data available",
        x=0.5,
        y=0.5,
        showarrow=False,
        xref="paper",
        yref="paper",
    )
    fig.update_layout(
        title=title,
        template=PLOT_TEMPLATE,
        margin=DEFAULT_MARGIN,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return fig


def _apply_layout(fig, title=None, x_label=None, y_label=None):
    fig.update_layout(template=PLOT_TEMPLATE, margin=DEFAULT_MARGIN)
    if title:
        fig.update_layout(title=title)
    if x_label is not None:
        fig.update_xaxes(title=x_label)
    if y_label is not None:
        fig.update_yaxes(title=y_label)
    return fig


def _build_time_series(df, parsed_col, granularity, title, y_label, kind="line"):
    counts = resample_counts(df, parsed_col, granularity)
    if counts.empty:
        return _empty_figure(title)

    if kind == "bar":
        fig = px.bar(
            counts,
            x="bucket",
            y="count",
            title=title,
            labels={"bucket": "Date", "count": y_label},
        )
    else:
        fig = px.line(
            counts,
            x="bucket",
            y="count",
            title=title,
            labels={"bucket": "Date", "count": y_label},
            markers=True,
        )

    fig.update_xaxes(type="category", tickangle=45)
    return _apply_layout(fig, title=title, x_label="Date", y_label=y_label)


def _value_counts_chart(
    df,
    column,
    title,
    chart_type="bar",
    split_multi=False,
    max_categories=12,
):
    if df.empty or column not in df.columns:
        return _empty_figure(title)

    series = df[column].dropna()
    if series.empty:
        return _empty_figure(title)

    series = series.astype(str).str.strip()
    if split_multi:
        series = series.str.split(r"[;,/]").explode().str.strip()

    series = series[series != ""]
    if series.empty:
        return _empty_figure(title)

    counts = series.value_counts().head(max_categories)
    if counts.empty:
        return _empty_figure(title)

    if chart_type == "pie":
        fig = px.pie(values=counts.values, names=counts.index, title=title)
    else:
        fig = px.bar(
            x=counts.index.astype(str),
            y=counts.values,
            title=title,
            labels={"x": "", "y": "Count"},
        )
        fig.update_xaxes(tickangle=45)

    return _apply_layout(fig, title=title)


def _login_activity_last_three(logins_df, granularity="daily"):
    title = "Login Activity (Last 3 Active Periods)"
    counts = resample_counts(logins_df, LOGINS_PARSED_COL, granularity)
    if counts.empty:
        return _empty_figure(title)

    counts = counts.tail(3)
    fig = px.bar(
        counts,
        x="bucket",
        y="count",
        title=title,
        labels={"bucket": "Date", "count": "Login Count"},
    )
    fig.update_xaxes(type="category", tickangle=45)
    return _apply_layout(fig, title=title, x_label="Date", y_label="Login Count")


def _login_activity_total(logins_df, granularity="daily"):
    return _build_time_series(
        logins_df,
        LOGINS_PARSED_COL,
        granularity,
        "Login Activity Total",
        "Login Count",
        kind="line",
    )


def _registration_activity_last_three(users_df, granularity="daily"):
    title = "Registration Activity (Last 3 Active Periods)"
    counts = resample_counts(users_df, USERS_PARSED_COL, granularity)
    if counts.empty:
        return _empty_figure(title)

    counts = counts.tail(3)
    fig = px.bar(
        counts,
        x="bucket",
        y="count",
        title=title,
        labels={"bucket": "Date", "count": "Registration Count"},
    )
    fig.update_xaxes(type="category", tickangle=45)
    return _apply_layout(fig, title=title, x_label="Date", y_label="Registration Count")


def _gender_distribution(users_df):
    gender_col = find_column(users_df, ["Sex", "Gender"], contains=True)
    return _value_counts_chart(users_df, gender_col, "Gender Distribution", chart_type="pie")


def _ethnicity_distribution(users_df):
    ethnicity_col = find_column(users_df, ["Ethnicity"], contains=True)
    return _value_counts_chart(users_df, ethnicity_col, "Ethnicity Distribution")


def _work_status(users_df):
    work_col = find_column(
        users_df,
        ["Right to work in the UK for yourself", "Right to work", "Work Status"],
        contains=True,
    )
    return _value_counts_chart(users_df, work_col, "Right to Work Status", chart_type="pie")



def _contact_agreement(users_df):
    contact_col = find_column(
        users_df,
        [
            "Are you happy for us to contact you via email/WhatsApp about other services?",
            "Contact Agreement",
            "Contact Consent",
        ],
        contains=True,
    )
    return _value_counts_chart(users_df, contact_col, "Contact Agreement", chart_type="pie")


def _english_ability(users_df):
    eng_col = find_column(
        users_df,
        [
            "How would you rate your ability in speaking English?",
            "English Ability",
            "English Proficiency",
        ],
        contains=True,
    )
    return _value_counts_chart(users_df, eng_col, "English Speaking Ability")


def build_plot_figure(plot_key, users_df, logins_df, granularity="daily"):
    builders = {
        "login_activity": lambda: _login_activity_last_three(logins_df, granularity),
        "login_total": lambda: _login_activity_total(logins_df, granularity),
        "registration_activity": lambda: _registration_activity_last_three(users_df, granularity),
        "gender_distribution": lambda: _gender_distribution(users_df),
        "age_distribution": lambda: _age_distribution(users_df),
        "ethnicity_distribution": lambda: _ethnicity_distribution(users_df),
        "work_status": lambda: _work_status(users_df),
        "contact_agreement": lambda: _contact_agreement(users_df),
        "english_ability": lambda: _english_ability(users_df),
    }
    builder = builders.get(plot_key)
    if not builder:
        return _empty_figure("Unknown Plot")
    return builder()


def _age_distribution(users_df):
    title = "Age Distribution"
    if users_df.empty:
        return _empty_figure(title)

    dob_col = find_column(users_df, ["Date of Birth", "DOB"], contains=True)
    if not dob_col:
        return _empty_figure(title)

    df = users_df.copy()
    df["DOB_Parsed"] = pd.to_datetime(df[dob_col], errors="coerce")
    df["Age"] = (pd.Timestamp.now() - df["DOB_Parsed"]).dt.days // 365
    df = df.dropna(subset=["Age"])

    if df.empty:
        return _empty_figure(title)

    fig = px.histogram(
        df,
        x="Age",
        nbins=10,
        title=title,
        labels={"Age": "Age", "count": "Users"},
    )
    return _apply_layout(fig, title=title, x_label="Age", y_label="Users")


def _area_distribution(users_df):
    title = "Visitor Area Distribution"
    postcode_col = find_column(users_df, ["Postcode", "Post Code", "PostCode"], contains=True)
    if not postcode_col or users_df.empty:
        return _empty_figure(title)

    outward = (
        users_df[postcode_col]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .str.split(" ")
        .str[0]
    )
    outward = outward[outward != ""]
    if outward.empty:
        return _empty_figure(title)

    counts = outward.value_counts().sort_values(ascending=False)
    fig = px.bar(
        x=counts.index.astype(str),
        y=counts.values,
        title=title,
        labels={"x": "Outward Code", "y": "Visitors"},
    )
    fig.update_xaxes(type="category", tickangle=45, categoryorder="total descending")
    return _apply_layout(fig, title=title, x_label="Outward Code", y_label="Visitors")


def _household_adults_children(users_df):
    title = "Household Size: Adults vs Children"
    adult_col = find_column(
        users_df,
        ["Number of Adults in Household", "Adults in Household", "Adults"],
        contains=True,
    )
    child_col = find_column(
        users_df,
        ["Number of Children in Household", "Children in Household", "Children"],
        contains=True,
    )

    if not adult_col and not child_col:
        return _empty_figure(title), adult_col, child_col

    fig = go.Figure()

    if adult_col:
        adults = pd.to_numeric(users_df[adult_col], errors="coerce").dropna()
        adult_counts = adults.value_counts().sort_index()
        if not adult_counts.empty:
            fig.add_bar(
                x=adult_counts.index.astype(int).astype(str),
                y=adult_counts.values,
                name="Adults",
            )

    if child_col:
        children = pd.to_numeric(users_df[child_col], errors="coerce").dropna()
        child_counts = children.value_counts().sort_index()
        if not child_counts.empty:
            fig.add_bar(
                x=child_counts.index.astype(int).astype(str),
                y=child_counts.values,
                name="Children",
            )

    if not fig.data:
        return _empty_figure(title), adult_col, child_col

    fig.update_layout(barmode="group")
    fig.update_xaxes(type="category")
    return _apply_layout(fig, title=title, x_label="Count in Household", y_label="Households"), adult_col, child_col


def _household_total(users_df, adult_col, child_col):
    title = "Total Household Size"
    if not adult_col or not child_col or users_df.empty:
        return _empty_figure(title)

    adults = pd.to_numeric(users_df[adult_col], errors="coerce")
    children = pd.to_numeric(users_df[child_col], errors="coerce")
    total = adults.fillna(0) + children.fillna(0)
    total = total[~(adults.isna() & children.isna())]

    if total.empty:
        return _empty_figure(title)

    counts = total.value_counts().sort_index()
    if counts.empty:
        return _empty_figure(title)

    fig = px.bar(
        x=counts.index.astype(int).astype(str),
        y=counts.values,
        title=title,
        labels={"x": "Household Size", "y": "Households"},
    )
    fig.update_xaxes(type="category")
    return _apply_layout(fig, title=title, x_label="Household Size", y_label="Households")


def _new_vs_returning(logins_df, first_login_map, granularity):
    title = "New vs Returning Logins"
    if logins_df.empty or USERNAME_COL not in logins_df.columns or LOGINS_PARSED_COL not in logins_df.columns:
        return _empty_figure(title)

    if not first_login_map:
        return _empty_figure(title)

    df = logins_df.dropna(subset=[USERNAME_COL, LOGINS_PARSED_COL]).copy()
    if df.empty:
        return _empty_figure(title)

    df["UserKey"] = df[USERNAME_COL].astype(str)
    first_dates = pd.to_datetime(df["UserKey"].map(first_login_map), errors="coerce").dt.date
    df = df.assign(FirstLoginDate=first_dates, LoginDate=df[LOGINS_PARSED_COL].dt.date)
    df = df.dropna(subset=["FirstLoginDate"])

    if df.empty:
        return _empty_figure(title)

    df["Status"] = "Returning"
    df.loc[df["LoginDate"] == df["FirstLoginDate"], "Status"] = "New"

    df = add_time_buckets(df, LOGINS_PARSED_COL, granularity)
    if df["_bucket"].isna().all():
        return _empty_figure(title)

    grouped = (
        df.groupby(["_bucket", "_bucket_sort", "Status"]).size().reset_index(name="count").sort_values("_bucket_sort")
    )

    fig = px.bar(
        grouped,
        x="_bucket",
        y="count",
        color="Status",
        title=title,
        labels={"_bucket": "Date", "count": "Logins"},
        barmode="stack",
    )
    fig.update_xaxes(type="category", tickangle=45)
    return _apply_layout(fig, title=title, x_label="Date", y_label="Logins")


def _cohort_retention(users_df, logins_df):
    title = "Cohort Retention (Registration Month vs Login Month)"
    if users_df.empty or logins_df.empty:
        return _empty_figure(title)

    if USERNAME_COL not in users_df.columns or USERS_PARSED_COL not in users_df.columns:
        return _empty_figure(title)

    if USERNAME_COL not in logins_df.columns or LOGINS_PARSED_COL not in logins_df.columns:
        return _empty_figure(title)

    reg_df = users_df.dropna(subset=[USERNAME_COL, USERS_PARSED_COL]).copy()
    log_df = logins_df.dropna(subset=[USERNAME_COL, LOGINS_PARSED_COL]).copy()

    if reg_df.empty or log_df.empty:
        return _empty_figure(title)

    reg_df["UserKey"] = reg_df[USERNAME_COL].astype(str)
    reg_df["Cohort"] = reg_df[USERS_PARSED_COL].dt.to_period("M").astype(str)

    cohort_sizes = reg_df.drop_duplicates("UserKey").groupby("Cohort")["UserKey"].nunique()
    if cohort_sizes.empty:
        return _empty_figure(title)

    log_df["UserKey"] = log_df[USERNAME_COL].astype(str)
    log_df["ActivityMonth"] = log_df[LOGINS_PARSED_COL].dt.to_period("M").astype(str)

    merged = log_df.merge(reg_df[["UserKey", "Cohort"]].drop_duplicates(), on="UserKey", how="inner")
    if merged.empty:
        return _empty_figure(title)

    active = (
        merged.groupby(["Cohort", "ActivityMonth"])["UserKey"].nunique().reset_index(name="ActiveUsers")
    )

    pivot = active.pivot(index="Cohort", columns="ActivityMonth", values="ActiveUsers").fillna(0)
    if pivot.empty:
        return _empty_figure(title)

    cohort_order = sorted(pivot.index, key=lambda x: pd.Period(x, freq="M"))
    activity_order = sorted(pivot.columns, key=lambda x: pd.Period(x, freq="M"))
    pivot = pivot.loc[cohort_order, activity_order]

    retention = pivot.div(cohort_sizes.reindex(cohort_order), axis=0) * 100
    retention = retention.fillna(0)

    fig = go.Figure(
        data=go.Heatmap(
            z=retention.values,
            x=retention.columns.tolist(),
            y=retention.index.tolist(),
            colorscale="Blues",
            zmin=0,
            zmax=100,
            colorbar=dict(title="% Active"),
            hovertemplate="Cohort %{y}<br>Month %{x}<br>%{z:.1f}% active<extra></extra>",
        )
    )

    fig.update_layout(
        title=title,
        template=PLOT_TEMPLATE,
        margin=DEFAULT_MARGIN,
        xaxis_title="Login Month",
        yaxis_title="Registration Cohort",
    )
    return fig


def init_dashboard_dash(server):
    app = Dash(
        __name__,
        server=server,
        url_base_pathname="/dashboard/",
        external_stylesheets=["/static/styles.css"],
    )
    app.title = "Dashboard"

    app.layout = html.Div(
        [
            dcc.Store(id="users-store"),
            dcc.Store(id="logins-store"),
            dcc.Store(id="first-logins-store"),
            dcc.Store(id="total-users-store"),
            html.Div(
                [
                    html.Div(
                        [
                            html.H1("Dashboard", className="dash-title"),
                            html.P(
                                "Storytelling view of registrations, needs, and engagement.",
                                className="dash-subtitle",
                            ),
                        ],
                        className="dash-brand",
                    ),
                    html.Div(
                        [
                            html.A("Home", href="/", className="header-button"),
                            html.A(
                                "Download PDF",
                                href="/download_dashboard",
                                className="header-button header-button--primary",
                            ),
                        ],
                        className="dash-actions",
                    ),
                ],
                className="dash-header",
            ),
            html.Div(
                [
                    html.Div(
                        [
                            html.Label("Date range", className="filter-label"),
                            dcc.DatePickerRange(
                                id="date-range",
                                start_date=DATE_DEFAULT_START.isoformat(),
                                end_date=DATE_DEFAULT_END.isoformat(),
                                display_format="YYYY-MM-DD",
                            ),
                        ],
                        className="filter-group",
                    ),
                    html.Div(
                        [
                            html.Label("Time granularity", className="filter-label"),
                            dcc.RadioItems(
                                id="granularity",
                                options=[
                                    {"label": "Daily", "value": "daily"},
                                    {"label": "Weekly", "value": "weekly"},
                                    {"label": "Monthly", "value": "monthly"},
                                ],
                                value="weekly",
                                inline=True,
                                className="granularity-toggle",
                            ),
                        ],
                        className="filter-group",
                    ),
                    html.Button(
                        "Apply date range",
                        id="apply-filters",
                        n_clicks=0,
                        className="apply-button",
                    ),
                ],
                className="filter-bar",
            ),
            dcc.Tabs(
                id="dash-tabs",
                value="tab-overview",
                className="dash-tabs",
                children=[
                    dcc.Tab(
                        label="Overview",
                        value="tab-overview",
                        className="dash-tab",
                        selected_className="dash-tab--selected",
                        children=[
                            html.Div(
                                [
                                    _kpi_card(
                                        "Total Registered Users",
                                        "kpi-total-users",
                                        "Unique registered users in the dataset.",
                                    ),
                                    _kpi_card(
                                        "New Registrations",
                                        "kpi-new-registrations",
                                        "Registrations that fall within the selected date range.",
                                    ),
                                    _kpi_card(
                                        "Total Logins",
                                        "kpi-total-logins",
                                        "All login records within the selected date range.",
                                    ),
                                    _kpi_card(
                                        "Active Users",
                                        "kpi-active-users",
                                        "Unique users who logged in during the selected range.",
                                    ),
                                    _kpi_card(
                                        "Returning Rate",
                                        "kpi-returning-rate",
                                        "Share of active users with at least two logins in the range.",
                                    ),
                                ],
                                className="kpi-grid",
                            ),
                            html.Div(
                                [
                                    _graph_card(
                                        "registrations-trend",
                                        "Registrations Trend",
                                        "Registrations over time, bucketed by the chosen granularity.",
                                    ),
                                    _graph_card(
                                        "logins-trend",
                                        "Logins Trend",
                                        "Login activity over time, bucketed by the chosen granularity.",
                                    ),
                                ],
                                className="dash-grid dash-grid--two",
                            ),
                        ],
                    ),
                    dcc.Tab(
                        label="People & Needs",
                        value="tab-people",
                        className="dash-tab",
                        selected_className="dash-tab--selected",
                        children=[
                            html.Div(
                                [
                                    _graph_card(
                                        "gender-chart",
                                        "Sex Distribution",
                                        "Distribution of users by sex/gender.",
                                    ),
                                    _graph_card(
                                        "age-chart",
                                        "Age Distribution",
                                        "Age profile calculated from date of birth.",
                                    ),
                                    _graph_card(
                                        "language-chart",
                                        "Primary Language",
                                        "Primary language reported by users.",
                                    ),
                                    _graph_card(
                                        "dietary-chart",
                                        "Dietary Requirements",
                                        "Dietary needs reported by users (split for multi-select).",
                                    ),
                                    _graph_card(
                                        "household-chart",
                                        "Household Adults vs Children",
                                        "Distribution of adult and child counts per household.",
                                    ),
                                    _graph_card(
                                        "household-total-chart",
                                        "Total Household Size",
                                        "Combined household size (adults + children).",
                                    ),
                                    _graph_card(
                                        "area-chart",
                                        "Visitor Area Distribution",
                                        "Number of visitors per outward postcode (e.g. E14, SW1).",
                                    ),
                                ],
                                className="dash-grid",
                            )
                        ],
                    ),
                    dcc.Tab(
                        label="Engagement & Outreach",
                        value="tab-engagement",
                        className="dash-tab",
                        selected_className="dash-tab--selected",
                        children=[
                            html.Div(
                                [
                                    _graph_card(
                                        "new-returning-chart",
                                        "New vs Returning Logins",
                                        "Logins classified by whether it is the user's first login.",
                                    ),
                                ],
                                className="dash-grid",
                            )
                        ],
                    ),
                ],
            ),
        ],
        className="dash-page",
    )

    @app.callback(
        Output("users-store", "data"),
        Output("logins-store", "data"),
        Output("first-logins-store", "data"),
        Output("total-users-store", "data"),
        Input("apply-filters", "n_clicks"),
        State("date-range", "start_date"),
        State("date-range", "end_date"),
    )
    def load_and_filter_data(_n_clicks, start_date, end_date):
        users_df, logins_df = data_service.get_all_data_frames()

        users_df = parse_timestamps(users_df, USERS_TS_COL, USERS_PARSED_COL)
        logins_df = parse_timestamps(logins_df, LOGINS_TS_COL, LOGINS_PARSED_COL)

        # Total ever-registered users — computed before date filtering
        if USERNAME_COL in users_df.columns:
            total_users_all_time = int(users_df[USERNAME_COL].nunique())
        else:
            total_users_all_time = len(users_df)

        first_login_map = {}
        if USERNAME_COL in logins_df.columns:
            valid = logins_df.dropna(subset=[USERNAME_COL, LOGINS_PARSED_COL]).copy()
            if not valid.empty:
                valid["UserKey"] = valid[USERNAME_COL].astype(str)
                first = valid.groupby("UserKey")[LOGINS_PARSED_COL].min()
                first_login_map = {key: value.date().isoformat() for key, value in first.items()}

        users_filtered = apply_date_range(users_df, USERS_PARSED_COL, start_date, end_date)
        logins_filtered = apply_date_range(logins_df, LOGINS_PARSED_COL, start_date, end_date)

        return _serialize_df(users_filtered), _serialize_df(logins_filtered), first_login_map, total_users_all_time

    @app.callback(
        Output("kpi-total-users", "children"),
        Output("kpi-new-registrations", "children"),
        Output("kpi-total-logins", "children"),
        Output("kpi-active-users", "children"),
        Output("kpi-returning-rate", "children"),
        Output("registrations-trend", "figure"),
        Output("logins-trend", "figure"),
        Input("users-store", "data"),
        Input("logins-store", "data"),
        Input("total-users-store", "data"),
        Input("granularity", "value"),
    )
    def update_overview(users_payload, logins_payload, total_users_all_time, granularity):
        users_df = _deserialize_df(users_payload)
        logins_df = _deserialize_df(logins_payload)

        total_users = total_users_all_time or 0

        new_registrations = len(users_df)
        total_logins = len(logins_df)

        if USERNAME_COL in logins_df.columns:
            active_users = logins_df[USERNAME_COL].nunique()
            counts = logins_df.groupby(USERNAME_COL).size() if not logins_df.empty else pd.Series(dtype=int)
            returning_users = (counts >= 2).sum() if not counts.empty else 0
            returning_rate = (returning_users / active_users * 100) if active_users else None
        else:
            active_users = 0
            returning_rate = None

        returning_display = f"{returning_rate:.1f}%" if returning_rate is not None else "N/A"

        registrations_trend = _build_time_series(
            users_df,
            USERS_PARSED_COL,
            granularity,
            "Registrations Trend",
            "Registrations",
            kind="bar",
        )

        logins_trend = _build_time_series(
            logins_df,
            LOGINS_PARSED_COL,
            granularity,
            "Logins Trend",
            "Logins",
            kind="line",
        )

        return (
            f"{total_users:,}",
            f"{new_registrations:,}",
            f"{total_logins:,}",
            f"{active_users:,}",
            returning_display,
            registrations_trend,
            logins_trend,
        )

    @app.callback(
        Output("gender-chart", "figure"),
        Output("age-chart", "figure"),
        Output("language-chart", "figure"),
        Output("dietary-chart", "figure"),
        Output("household-chart", "figure"),
        Output("household-total-chart", "figure"),
        Output("area-chart", "figure"),
        Input("users-store", "data"),
    )
    def update_people_needs(users_payload):
        users_df = _deserialize_df(users_payload)

        gender_col = find_column(users_df, ["Sex", "Gender"], contains=True)
        gender_fig = _value_counts_chart(users_df, gender_col, "Sex Distribution", chart_type="pie")

        age_fig = _age_distribution(users_df)

        language_col = find_column(users_df, ["Primary Language", "First Language", "Main Language", "Language"], contains=True)
        language_fig = _value_counts_chart(users_df, language_col, "Primary Language")

        dietary_col = find_column(
            users_df,
            ["Dietary Requirements", "Dietary Requirement", "Dietary"],
            contains=True,
        )
        dietary_fig = _value_counts_chart(
            users_df,
            dietary_col,
            "Dietary Requirements",
            split_multi=True,
        )

        household_fig, adult_col, child_col = _household_adults_children(users_df)
        household_total_fig = _household_total(users_df, adult_col, child_col)
        area_fig = _area_distribution(users_df)

        return (
            gender_fig,
            age_fig,
            language_fig,
            dietary_fig,
            household_fig,
            household_total_fig,
            area_fig,
        )

    @app.callback(
        Output("new-returning-chart", "figure"),
        Input("users-store", "data"),
        Input("logins-store", "data"),
        Input("first-logins-store", "data"),
        Input("granularity", "value"),
    )
    def update_engagement(users_payload, logins_payload, first_logins_map, granularity):
        logins_df = _deserialize_df(logins_payload)

        return _new_vs_returning(logins_df, first_logins_map or {}, granularity)

    app.clientside_callback(
        """
        function(n_clicks) {
            if (n_clicks % 2 === 1) {
                return [{"display": "none"}, "+"];
            }
            return [{"display": "block"}, "\u2212"];
        }
        """,
        Output({"type": "graph-container", "index": MATCH}, "style"),
        Output({"type": "minimize-btn", "index": MATCH}, "children"),
        Input({"type": "minimize-btn", "index": MATCH}, "n_clicks"),
        prevent_initial_call=True,
    )

    return app
