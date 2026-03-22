import pandas as pd
from pandas.api.types import is_datetime64_any_dtype, is_datetime64tz_dtype


DEFAULT_TIMESTAMP_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%m/%d/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
]


def parse_timestamp_series(series):
    if series is None:
        return pd.Series(dtype="datetime64[ns]")

    if not isinstance(series, pd.Series):
        series = pd.Series(series)

    raw = series.astype(str)
    parsed = pd.to_datetime(raw, format=DEFAULT_TIMESTAMP_FORMATS[0], errors="coerce")
    for fmt in DEFAULT_TIMESTAMP_FORMATS[1:]:
        parsed = parsed.fillna(pd.to_datetime(raw, format=fmt, errors="coerce"))

    parsed = parsed.fillna(pd.to_datetime(raw, errors="coerce"))
    return parsed


def ensure_datetime_series(series):
    if series is None:
        return pd.Series(dtype="datetime64[ns]")

    if not isinstance(series, pd.Series):
        series = pd.Series(series)

    if is_datetime64_any_dtype(series) or is_datetime64tz_dtype(series):
        return series

    return parse_timestamp_series(series)


def parse_timestamps(df, source_col, parsed_col):
    if df is None:
        return pd.DataFrame()

    df = df.copy()
    if source_col not in df.columns:
        df[parsed_col] = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns]")
        return df

    df[parsed_col] = parse_timestamp_series(df[source_col])
    return df


def apply_date_range(df, parsed_col, start_date, end_date):
    if df is None:
        return pd.DataFrame()

    if df.empty:
        return df.copy()

    if parsed_col not in df.columns:
        return df.head(0)

    parsed = ensure_datetime_series(df[parsed_col])
    df[parsed_col] = parsed
    if parsed.dropna().empty:
        return df.head(0)

    start = pd.to_datetime(start_date).date() if start_date else None
    end = pd.to_datetime(end_date).date() if end_date else None

    if start and end and start > end:
        start, end = end, start

    mask = pd.Series(True, index=df.index)
    if start:
        mask &= parsed.dt.date >= start
    if end:
        mask &= parsed.dt.date <= end

    return df.loc[mask].copy()


def add_time_buckets(df, parsed_col, granularity):
    if df.empty or parsed_col not in df.columns:
        return df.assign(_bucket=pd.NA, _bucket_sort=pd.NA)

    parsed = ensure_datetime_series(df[parsed_col])
    if parsed.dropna().empty:
        return df.assign(_bucket=pd.NA, _bucket_sort=pd.NA)

    if granularity == "weekly":
        iso = parsed.dt.isocalendar()
        bucket = iso["year"].astype(str) + "-W" + iso["week"].astype(str).str.zfill(2)
        sort = iso["year"] * 100 + iso["week"]
    elif granularity == "monthly":
        period = parsed.dt.to_period("M")
        bucket = period.astype(str)
        sort = period.dt.to_timestamp()
    else:
        bucket = parsed.dt.date.astype(str)
        sort = parsed.dt.date

    return df.assign(_bucket=bucket, _bucket_sort=sort)


def resample_counts(df, parsed_col, granularity):
    if df is None or df.empty or parsed_col not in df.columns:
        return pd.DataFrame(columns=["bucket", "count"])

    base = df.copy()
    base[parsed_col] = ensure_datetime_series(base[parsed_col])
    base = base.dropna(subset=[parsed_col])
    if base.empty:
        return pd.DataFrame(columns=["bucket", "count"])

    base = add_time_buckets(base, parsed_col, granularity)
    grouped = base.groupby(["_bucket", "_bucket_sort"]).size().reset_index(name="count")
    grouped = grouped.sort_values("_bucket_sort")
    return grouped.rename(columns={"_bucket": "bucket"}).drop(columns="_bucket_sort")


def find_column(df, candidates, contains=False):
    if df is None or df.empty:
        return None

    cols = list(df.columns)
    lower_map = {col.lower(): col for col in cols}

    for candidate in candidates:
        match = lower_map.get(candidate.lower())
        if match:
            return match

    if contains:
        for col in cols:
            lower_col = col.lower()
            for candidate in candidates:
                if candidate.lower() in lower_col:
                    return col

    return None
