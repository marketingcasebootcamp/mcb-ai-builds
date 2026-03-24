"""
Heuristic detection of:
  - Which row is the real header row (skipping metadata rows above it)
  - Which advertising platform produced the file
  - Which rows are footers / totals that should be removed

Returns structured dicts. Never modifies data. No Claude calls — agent.py
calls Claude when confidence is below threshold and passes results back here
for merging.
"""

import re
import difflib
from typing import Optional

import pandas as pd

from schema import (
    PLATFORM_SIGNALS,
    PLATFORM_SIGNAL_THRESHOLD,
    METADATA_PATTERNS,
    FOOTER_PATTERNS,
)

# Confidence thresholds below which we ask Claude to confirm
HEADER_CONFIDENCE_THRESHOLD = 0.70
PLATFORM_CONFIDENCE_THRESHOLD = 0.65


# ── Header row detection ──────────────────────────────────────────────────────

def detect_header_row(raw_lines: list[str], max_scan: int = 15) -> dict:
    """
    Scan the first `max_scan` raw text lines to find where the real header row
    starts. Returns a dict with the header row index and metadata.

    Strategy (three passes):
      Pass 1 — score each row for metadata signals. Mark high-scoring rows
                as metadata. First non-metadata row is the header candidate.
      Pass 2 — validate the candidate: all strings, >=4 columns, no numbers.
      Pass 3 — confirm by checking that the row after it looks like data.
    """
    lines = raw_lines[:max_scan]
    if not lines:
        return _header_result(0, 0, [], 0.5, "heuristic")

    parsed = [_parse_line(line) for line in lines]
    n = len(parsed)

    # Pass 1 — metadata scoring
    metadata_flags = []
    for cells in parsed:
        score = _metadata_score(cells)
        metadata_flags.append(score >= 0.4)

    # Find first non-metadata row
    candidate_idx = 0
    for i, is_meta in enumerate(metadata_flags):
        if not is_meta:
            candidate_idx = i
            break

    # Pass 2 — validate candidate looks like a header
    candidate_score = _header_score(parsed[candidate_idx])

    # Pass 3 — check the row after candidate looks like data
    if candidate_idx + 1 < n:
        next_row_score = _data_row_score(parsed[candidate_idx + 1])
    else:
        next_row_score = 0.5  # no next row to check, neutral

    # Combine scores
    confidence = (candidate_score * 0.6) + (next_row_score * 0.4)

    # If candidate is still low quality, try incrementing by 1
    if confidence < HEADER_CONFIDENCE_THRESHOLD and candidate_idx + 1 < n:
        alt_score = _header_score(parsed[candidate_idx + 1])
        if alt_score > candidate_score:
            candidate_idx += 1
            confidence = min(alt_score * 0.7 + next_row_score * 0.3, 0.85)

    skipped = candidate_idx
    metadata_rows = lines[:skipped]

    return _header_result(
        header_row_index=candidate_idx,
        skipped_rows=skipped,
        metadata_rows=metadata_rows,
        confidence=confidence,
        method="heuristic",
    )


def merge_claude_header_result(heuristic: dict, claude_response: dict) -> dict:
    """Merge Claude's header detection result into the heuristic result."""
    return _header_result(
        header_row_index=claude_response["header_row_index"],
        skipped_rows=claude_response["header_row_index"],
        metadata_rows=heuristic["metadata_rows"],
        confidence=claude_response.get("confidence", 0.95),
        method="claude",
    )


def _header_result(header_row_index, skipped_rows, metadata_rows, confidence, method):
    return {
        "header_row_index": header_row_index,
        "skipped_rows": skipped_rows,
        "metadata_rows": metadata_rows,
        "confidence": confidence,
        "method": method,
    }


def _parse_line(line: str) -> list[str]:
    """Split a raw CSV line into cells, handling quoted fields minimally."""
    import csv, io
    try:
        reader = csv.reader(io.StringIO(line))
        return [cell.strip() for cell in next(reader)]
    except Exception:
        return [c.strip() for c in line.split(",")]


def _metadata_score(cells: list[str]) -> float:
    """Return 0.0–1.0 likelihood that this row is a metadata row."""
    if not cells:
        return 1.0
    text = " ".join(cells).lower()
    matches = sum(1 for pat in METADATA_PATTERNS if pat in text)
    # Also flag rows with very few cells (title rows often have 1-2 cells)
    few_cells_bonus = 0.3 if len(cells) <= 2 else 0.0
    return min((matches * 0.25) + few_cells_bonus, 1.0)


def _header_score(cells: list[str]) -> float:
    """Return 0.0–1.0 likelihood that this row is a column header row."""
    if len(cells) < 3:
        return 0.1
    score = 0.0
    # Headers have many non-empty cells
    non_empty = [c for c in cells if c]
    score += min(len(non_empty) / 6, 0.3)
    # Headers are mostly strings, not numbers
    numeric_count = sum(1 for c in non_empty if _looks_numeric(c))
    string_ratio = 1 - (numeric_count / max(len(non_empty), 1))
    score += string_ratio * 0.4
    # Headers often have title-cased or capitalized words
    title_count = sum(1 for c in non_empty if c and (c[0].isupper() or "_" in c))
    score += min(title_count / max(len(non_empty), 1), 1.0) * 0.2
    # Headers don't have currency symbols
    currency_free = not any("$" in c or "€" in c or "£" in c for c in cells)
    score += 0.1 if currency_free else 0.0
    return min(score, 1.0)


def _data_row_score(cells: list[str]) -> float:
    """Return 0.0–1.0 likelihood that this row is a data row (not a header)."""
    if not cells:
        return 0.0
    non_empty = [c for c in cells if c]
    if not non_empty:
        return 0.0
    # Data rows have numeric values
    numeric_count = sum(1 for c in non_empty if _looks_numeric(c))
    score = min(numeric_count / max(len(non_empty), 1), 1.0) * 0.7
    # Or date-like values
    date_count = sum(1 for c in non_empty if _looks_like_date(c))
    score += min(date_count * 0.3, 0.3)
    return min(score, 1.0)


def _looks_numeric(value: str) -> bool:
    """True if value looks like a number (with possible currency/percent symbols)."""
    cleaned = value.strip().lstrip("$€£¥").rstrip("%").replace(",", "").replace(".", "")
    return cleaned.lstrip("-").isdigit() and len(cleaned) > 0


def _looks_like_date(value: str) -> bool:
    """True if value looks like a date string."""
    patterns = [
        r"\d{4}-\d{2}-\d{2}",
        r"\d{1,2}/\d{1,2}/\d{2,4}",
        r"[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}",
        r"Q[1-4]\s+\d{4}",
        r"\d{4}-\d{2}$",
    ]
    return any(re.search(p, value) for p in patterns)


# ── Platform detection ────────────────────────────────────────────────────────

def detect_platform(columns: list[str]) -> dict:
    """
    Score each known platform by how many of its signals appear in the
    column headers. Returns the top match if it exceeds the threshold.
    """
    normalized = [c.lower().strip() for c in columns]
    col_text = " | ".join(normalized)

    scores = {}
    signal_matches = {}
    for platform, signals in PLATFORM_SIGNALS.items():
        matches = [s for s in signals if s in col_text]
        scores[platform] = len(matches)
        signal_matches[platform] = matches

    if not scores:
        return _platform_result(None, [], 0.0, "heuristic")

    top_platform = max(scores, key=scores.get)
    top_score = scores[top_platform]

    if top_score < PLATFORM_SIGNAL_THRESHOLD:
        # Not enough signals — ask Claude
        return _platform_result(None, [], 0.0, "heuristic")

    # Confidence: ratio of matched signals vs total signals for this platform
    total_signals = len(PLATFORM_SIGNALS[top_platform])
    confidence = min(top_score / total_signals + 0.3, 0.95)

    return _platform_result(
        platform=top_platform,
        signal_matches=signal_matches[top_platform],
        confidence=confidence,
        method="heuristic",
    )


def merge_claude_platform_result(claude_response: dict) -> dict:
    """Merge Claude's platform detection response."""
    return _platform_result(
        platform=claude_response.get("platform") or None,
        signal_matches=[],
        confidence=claude_response.get("confidence", 0.9),
        method="claude",
    )


def _platform_result(platform, signal_matches, confidence, method):
    return {
        "platform": platform,
        "signal_matches": signal_matches,
        "confidence": confidence,
        "method": method,
    }


# ── Footer row detection ──────────────────────────────────────────────────────

def detect_footer_rows(df: pd.DataFrame) -> dict:
    """
    Scan from the bottom of the DataFrame upward looking for:
      - Rows whose first cell matches FOOTER_PATTERNS
      - Rows where all cells are blank
      - A single row where numeric columns are sums of rows above (Total row)

    Returns the index of the first footer row (to slice df[:footer_start_index]).
    """
    if df.empty:
        return _footer_result(None, 0, [])

    footer_start = None
    footer_types = []
    compiled = [re.compile(p, re.IGNORECASE) for p in FOOTER_PATTERNS]

    # Scan bottom-up
    for i in range(len(df) - 1, -1, -1):
        row = df.iloc[i]
        first_cell = str(row.iloc[0]).strip() if len(row) > 0 else ""

        # Check footer patterns on first cell
        if any(pat.search(first_cell) for pat in compiled):
            footer_start = i
            footer_types.append(_classify_footer(first_cell))
            continue

        # Check all-blank row
        if row.isna().all() or all(str(v).strip() in ("", "nan") for v in row):
            footer_start = i
            footer_types.append("blank")
            continue

        # If we found a non-footer row, stop scanning upward
        break

    # Additionally check for a "totals" signature row anywhere in the bottom 5
    if footer_start is None:
        total_idx = _find_totals_row(df)
        if total_idx is not None:
            footer_start = total_idx
            footer_types.append("total_signature")

    footer_count = (len(df) - footer_start) if footer_start is not None else 0

    return _footer_result(
        footer_start_index=footer_start,
        footer_row_count=footer_count,
        footer_types=list(set(footer_types)),
    )


def _classify_footer(cell_value: str) -> str:
    v = cell_value.lower().strip()
    if "total" in v:
        return "total"
    if "summary" in v or "subtotal" in v:
        return "summary"
    if "disclaimer" in v or "source" in v:
        return "disclaimer"
    if "export" in v or "generat" in v or "download" in v:
        return "export_metadata"
    return "other"


def _find_totals_row(df: pd.DataFrame, check_last_n: int = 5) -> Optional[int]:
    """
    Detect a row where numeric columns are unusually large compared to
    other rows — signature of a Grand Total row not caught by pattern match.
    """
    numeric_cols = df.select_dtypes(include="number").columns
    if len(numeric_cols) == 0 or len(df) < 3:
        return None

    tail = df.tail(check_last_n)
    body = df.iloc[:-check_last_n]
    if body.empty:
        return None

    body_means = body[numeric_cols].mean()

    for i in range(len(tail) - 1, -1, -1):
        row_vals = tail.iloc[i][numeric_cols]
        # A Total row is typically >= 5x the mean of any column
        if any(row_vals > body_means * 5):
            return tail.index[i]

    return None


def _footer_result(footer_start_index, footer_row_count, footer_types):
    return {
        "footer_start_index": footer_start_index,
        "footer_row_count": footer_row_count,
        "footer_types": footer_types,
    }
