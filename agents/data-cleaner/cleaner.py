"""
Deterministic data cleaning functions.
No Claude calls. No side effects. Pure transformations.

Handles the real-world mess in marketing exports:
  - Currency: $1,234.56 / €1.234,56 / (1,234.56) / 1.2M
  - Percentages: 12.5% / 0.125 (already decimal) / 12.5 (missing symbol)
  - Dates: Jan 1 2024 / 01/01/2024 / 2024-01 / Q1 2024 / Week of ...
  - Numbers: 1,234,567 / 1.234.567 / 1.23E+06
  - Nulls: "-" / "--" / "N/A" / "n/a" / "<blank>" / "(not set)"
"""

import re
from typing import Optional

import pandas as pd
from dateutil import parser as dateutil_parser

from schema import STANDARD_COLUMNS, PERCENTAGE_COLUMNS, CURRENCY_COLUMNS

# Values treated as null/missing across all platforms
NULL_SENTINELS = {
    "-", "--", "---", "n/a", "na", "N/A", "NA",
    "(not set)", "<not set>", "<blank>", "none",
    "null", "undefined", "unknown", "--", "∞",
}

# Currency symbols to strip
CURRENCY_SYMBOLS = "$€£¥₹₩₱฿"

# ── Type inference ────────────────────────────────────────────────────────────

def infer_column_types(df: pd.DataFrame, column_map: dict) -> dict:
    """
    Given a DataFrame and a column_map (raw_name → standard_name),
    return a dict of raw_column_name → type string.

    Type is one of: 'currency', 'percentage', 'date', 'number', 'text'
    Falls back to sampling column values when standard mapping is unknown.
    """
    col_types = {}
    reverse_map = {v: k for k, v in column_map.items() if v is not None}

    for col in df.columns:
        standard = column_map.get(col)

        if standard == "date":
            col_types[col] = "date"
        elif standard in CURRENCY_COLUMNS:
            col_types[col] = "currency"
        elif standard in PERCENTAGE_COLUMNS:
            col_types[col] = "percentage"
        elif standard in STANDARD_COLUMNS:
            col_types[col] = "number"
        else:
            # Sample-based inference for unmapped columns
            col_types[col] = _infer_from_sample(df[col])

    return col_types


def _infer_from_sample(series: pd.Series) -> str:
    """Infer column type from a sample of values."""
    sample = series.dropna().astype(str).head(20)
    if sample.empty:
        return "text"

    has_currency = sample.str.contains(r"[$€£¥]", regex=True).any()
    has_percent = sample.str.endswith("%").any()
    has_date = sample.apply(_looks_like_date).any()

    if has_currency:
        return "currency"
    if has_percent:
        return "percentage"
    if has_date:
        return "date"

    # Try parsing as numbers
    numeric_count = sum(1 for v in sample if _try_numeric(v) is not None)
    if numeric_count / len(sample) >= 0.7:
        return "number"

    return "text"


# ── Per-value cleaners ────────────────────────────────────────────────────────

def clean_currency(value) -> Optional[float]:
    """
    Parse a currency value to a plain float.

    Handles:
      $1,234.56  →  1234.56
      €1.234,56  →  1234.56  (European)
      (1,234.56) →  -1234.56 (negative in parens)
      1.2M       →  1200000.0
      1.2K       →  1200.0
      1.2B       →  1200000000.0
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    if s in NULL_SENTINELS or s == "":
        return None

    # Negative in parentheses
    negative = s.startswith("(") and s.endswith(")")
    if negative:
        s = s[1:-1]

    # Strip currency symbols and trailing currency codes
    s = s.lstrip(CURRENCY_SYMBOLS).strip()
    s = re.sub(r"\s*[A-Z]{3}$", "", s).strip()  # trailing "USD", "EUR" etc.

    # M / K / B suffixes
    multiplier = 1.0
    if s and s[-1].upper() == "M":
        multiplier = 1_000_000
        s = s[:-1]
    elif s and s[-1].upper() == "K":
        multiplier = 1_000
        s = s[:-1]
    elif s and s[-1].upper() == "B":
        multiplier = 1_000_000_000
        s = s[:-1]

    # Distinguish decimal point from thousands separator
    s = _normalize_number_string(s)
    if s is None:
        return None

    try:
        result = float(s) * multiplier
        return -result if negative else result
    except ValueError:
        return None


def clean_percentage(value, col_name: str = "", is_already_decimal: bool = False) -> Optional[float]:
    """
    Parse a percentage to a decimal float (e.g. 12.5% → 0.125).

    If the value has no % symbol, uses col_name and value range to decide
    whether it's already decimal or needs dividing by 100.
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    if s in NULL_SENTINELS or s == "":
        return None

    has_symbol = s.endswith("%")
    s = s.rstrip("%").strip()

    try:
        num = float(s.replace(",", ""))
    except ValueError:
        return None

    if has_symbol or is_already_decimal:
        return num / 100.0

    # No symbol — infer from value range and column name
    pct_col = any(k in col_name.lower() for k in ("rate", "ctr", "share", "ratio", "%"))
    if pct_col and 0.0 <= num <= 1.0:
        return num  # already decimal
    if pct_col and 1.0 < num <= 100.0:
        return num / 100.0

    # Default: if value is between 0 and 1 treat as decimal, else divide
    return num if 0.0 <= num <= 1.0 else num / 100.0


def clean_date(value) -> Optional[str]:
    """
    Parse any date-like string to ISO YYYY-MM-DD.

    Handles:
      Jan 1, 2024        → 2024-01-01
      01/01/2024         → 2024-01-01
      2024-01            → 2024-01-01  (month-only → first of month)
      Q1 2024            → 2024-01-01  (quarter → first day)
      Week of Jan 1 2024 → 2024-01-01
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    if s in NULL_SENTINELS or s == "":
        return None

    # Quarter pattern: Q1 2024 → 2024-01-01
    q_match = re.match(r"Q([1-4])\s+(\d{4})", s, re.IGNORECASE)
    if q_match:
        q, yr = int(q_match.group(1)), int(q_match.group(2))
        month = (q - 1) * 3 + 1
        return f"{yr}-{month:02d}-01"

    # Month-only: 2024-01 → 2024-01-01
    if re.match(r"^\d{4}-\d{2}$", s):
        return f"{s}-01"

    # Week of pattern: strip prefix and parse the date inside
    s = re.sub(r"^week\s+of\s+", "", s, flags=re.IGNORECASE).strip()

    # Try dateutil (handles most formats, US date convention dayfirst=False)
    try:
        dt = dateutil_parser.parse(s, dayfirst=False)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, OverflowError):
        pass

    # Try common explicit formats as fallback
    for fmt in ("%m/%d/%y", "%d/%m/%Y", "%B %d %Y", "%b %d %Y", "%Y%m%d"):
        try:
            import datetime
            dt = datetime.datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


def clean_number(value) -> Optional[float]:
    """
    Parse a numeric string (with possible thousands separators) to float.

    Handles:
      1,234,567    → 1234567.0
      1.234.567    → 1234567.0  (European thousands)
      1.23E+06     → 1230000.0
      1.5          → 1.5
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if s in NULL_SENTINELS or s == "":
        return None

    # Handle scientific notation
    if "e" in s.lower():
        try:
            return float(s)
        except ValueError:
            return None

    s = _normalize_number_string(s)
    if s is None:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _normalize_number_string(s: str) -> Optional[str]:
    """
    Resolve ambiguous comma/dot usage and return a plain float string.
    Returns None if value cannot be interpreted as a number.
    """
    s = s.strip()
    dot_count = s.count(".")
    comma_count = s.count(",")

    if dot_count == 0 and comma_count == 0:
        return s  # plain integer

    if dot_count == 1 and comma_count == 0:
        return s  # standard decimal: 1234.56

    if comma_count == 1 and dot_count == 0:
        # Could be European decimal (1234,56) or US thousands (1,234)
        comma_pos = s.index(",")
        after_comma = s[comma_pos + 1:]
        # European decimal: digits after comma are not exactly 3
        if len(after_comma) != 3:
            return s.replace(",", ".")  # European: 1234,56 → 1234.56
        else:
            return s.replace(",", "")  # US thousands: 1,234 → 1234

    if comma_count >= 1 and dot_count == 1:
        # US format: 1,234,567.89 — strip commas
        if s.index(",") < s.index("."):
            return s.replace(",", "")
        # European format: 1.234.567,89 — swap
        else:
            return s.replace(".", "").replace(",", ".")

    if dot_count >= 2 and comma_count == 0:
        # European thousands: 1.234.567 — strip dots except last is unlikely
        return s.replace(".", "")

    if comma_count >= 2 and dot_count == 0:
        # Multiple commas: 1,234,567 — strip commas
        return s.replace(",", "")

    return None


# ── Row and DataFrame cleaners ────────────────────────────────────────────────

def clean_row(row: pd.Series, column_types: dict) -> pd.Series:
    """Apply the appropriate cleaner to each cell in a row."""
    cleaned = {}
    for col, val in row.items():
        col_type = column_types.get(col, "text")
        if col_type == "currency":
            cleaned[col] = clean_currency(val)
        elif col_type == "percentage":
            cleaned[col] = clean_percentage(val, col_name=str(col))
        elif col_type == "date":
            cleaned[col] = clean_date(val)
        elif col_type == "number":
            cleaned[col] = clean_number(val)
        else:
            cleaned[col] = _clean_text(val)
    return pd.Series(cleaned)


def _clean_text(value) -> Optional[str]:
    """Strip whitespace; convert null sentinels to None."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    s = str(value).strip()
    if s.lower() in {v.lower() for v in NULL_SENTINELS}:
        return None
    return s if s else None


def remove_empty_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Drop rows where all numeric columns are null/zero AND all string columns
    are null. Preserves legitimately all-zero rows (new campaigns) by requiring
    fewer than 2 non-null, non-zero values across the entire row.
    """
    def is_empty_row(row):
        non_null_nonzero = sum(
            1 for v in row
            if v is not None
            and not (isinstance(v, float) and pd.isna(v))
            and v != 0
            and str(v).strip() not in ("", "0", "0.0")
        )
        return non_null_nonzero < 2

    mask = df.apply(is_empty_row, axis=1)
    return df[~mask].reset_index(drop=True)


def clean_dataframe(df: pd.DataFrame, column_types: dict) -> pd.DataFrame:
    """Apply clean_row to every row in the DataFrame."""
    return df.apply(lambda row: clean_row(row, column_types), axis=1)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _looks_like_date(value: str) -> bool:
    patterns = [
        r"\d{4}-\d{2}-\d{2}",
        r"\d{1,2}/\d{1,2}/\d{2,4}",
        r"[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}",
        r"Q[1-4]\s+\d{4}",
    ]
    return any(re.search(p, str(value)) for p in patterns)


def _try_numeric(value: str) -> Optional[float]:
    return clean_number(value)
