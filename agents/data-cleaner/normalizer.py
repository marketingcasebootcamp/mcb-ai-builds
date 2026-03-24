"""
Column name standardization.

Maps raw export column names → standard schema names using:
  1. Exact match against known platform synonyms (schema.py)
  2. Fuzzy match (difflib) for typos and casing variants
  3. Claude callback for anything still unresolved

No Anthropic SDK import here — agent.py owns all API calls and passes
a claude_callback function into normalize_columns().
"""

import difflib
from typing import Callable, Optional

import pandas as pd

from schema import COLUMN_SYNONYMS, STANDARD_COLUMNS


def normalize_columns(
    raw_columns: list[str],
    platform: str,
    claude_callback: Optional[Callable] = None,
    df_sample: Optional[pd.DataFrame] = None,
) -> dict:
    """
    Return a mapping of raw_column_name → standard_column_name (or None to drop).

    Args:
        raw_columns:      Original column names from the CSV.
        platform:         Detected platform slug (e.g. "google_ads").
        claude_callback:  Called with (pending_columns, platform, df_sample) when
                          heuristics can't resolve a column. Returns a mapping dict.
        df_sample:        First few rows of data — passed to claude_callback for context.

    Returns:
        {
            "Campaign Name": "campaign_name",
            "Impr.": "impressions",
            "Final URL": None,          # drop
            "Some Custom Col": "clicks", # resolved by Claude
        }
    """
    result = {}
    pending = []

    # Build combined synonym map: platform-specific + generic cache
    synonym_map = _build_synonym_map(platform)

    for col in raw_columns:
        normalized_key = col.lower().strip()

        # Step 1 — exact match
        if normalized_key in synonym_map:
            result[col] = synonym_map[normalized_key]
            continue

        # Step 2 — fuzzy match against all synonym keys
        fuzzy = _fuzzy_match(normalized_key, synonym_map)
        if fuzzy is not None:
            result[col] = synonym_map[fuzzy]
            continue

        # Step 3 — check if it's already a standard column name
        if normalized_key in STANDARD_COLUMNS:
            result[col] = normalized_key
            continue
        if normalized_key.replace(" ", "_") in STANDARD_COLUMNS:
            result[col] = normalized_key.replace(" ", "_")
            continue

        # Unresolved — queue for Claude
        pending.append(col)

    # Step 4 — ask Claude for pending columns
    if pending and claude_callback is not None:
        try:
            claude_mappings = claude_callback(pending, platform, df_sample)
            for raw_col, standard_col in claude_mappings.items():
                result[raw_col] = standard_col or None
                # Cache result so repeated files don't re-call Claude
                cache_key = raw_col.lower().strip()
                COLUMN_SYNONYMS["_generic"][cache_key] = standard_col or None
        except Exception:
            # If Claude call fails, keep pending columns unmapped (preserve raw)
            for col in pending:
                result[col] = None  # will become raw_ prefixed in build_output_dataframe
    else:
        # No callback — leave pending as unmapped
        for col in pending:
            result[col] = "_unmapped_"

    return result


def get_unmapped_columns(column_map: dict) -> list[str]:
    """Return list of columns that couldn't be mapped to the standard schema."""
    return [col for col, std in column_map.items() if std == "_unmapped_"]


def build_output_dataframe(df: pd.DataFrame, column_map: dict) -> pd.DataFrame:
    """
    Rename columns to standard names, drop columns mapped to None,
    prefix unmapped columns with 'raw_', and reorder to STANDARD_COLUMNS order.

    Standard columns that are missing from the data are added as empty columns
    so every output file has a consistent schema.
    """
    rename_map = {}
    drop_cols = []

    for raw_col, std_col in column_map.items():
        if std_col is None:
            drop_cols.append(raw_col)
        elif std_col == "_unmapped_":
            # Keep with raw_ prefix
            rename_map[raw_col] = f"raw_{raw_col.lower().replace(' ', '_')}"
        else:
            rename_map[raw_col] = std_col

    # Drop and rename
    df = df.drop(columns=[c for c in drop_cols if c in df.columns], errors="ignore")
    df = df.rename(columns=rename_map)

    # Deduplicate — if two raw cols mapped to same standard col, keep first
    seen = set()
    dedup_cols = []
    for col in df.columns:
        if col not in seen:
            seen.add(col)
            dedup_cols.append(col)
    df = df[dedup_cols]

    # Add missing standard columns as empty
    for std_col in STANDARD_COLUMNS:
        if std_col not in df.columns:
            df[std_col] = None

    # Reorder: standard columns first (in canonical order), then raw_ columns
    raw_extra = [c for c in df.columns if c.startswith("raw_")]
    ordered = [c for c in STANDARD_COLUMNS if c in df.columns] + raw_extra
    df = df[ordered]

    return df


# ── Helpers ───────────────────────────────────────────────────────────────────

def _build_synonym_map(platform: str) -> dict:
    """
    Merge platform-specific synonyms with the generic cache.
    Returns a flat dict of lowercased_raw_name → standard_name.
    """
    base = dict(COLUMN_SYNONYMS.get(platform, {}))
    generic = dict(COLUMN_SYNONYMS.get("_generic", {}))
    return {**generic, **base}  # platform-specific takes precedence


def _fuzzy_match(
    normalized_col: str,
    synonym_map: dict,
    cutoff: float = 0.82,
) -> Optional[str]:
    """
    Return the best matching synonym key for normalized_col, or None.
    Uses difflib SequenceMatcher — no external dependencies.
    """
    candidates = list(synonym_map.keys())
    matches = difflib.get_close_matches(normalized_col, candidates, n=1, cutoff=cutoff)
    return matches[0] if matches else None
