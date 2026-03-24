"""
Main Claude agent loop for data cleaning.

Orchestrates the full pipeline:
  1. Read raw file lines
  2. Detect (and confirm with Claude if needed) where the real header row is
  3. Parse into DataFrame
  4. Detect and strip footer rows
  5. Detect platform
  6. Map column names (with Claude for unknowns)
  7. Infer column types and clean data
  8. Build standardized output DataFrame

Claude is only called when heuristic confidence is below threshold.
"""

import json
import os
import re
from typing import Optional

import anthropic
import pandas as pd

import detector
import cleaner
import normalizer
from prompts import (
    SYSTEM_PROMPT,
    HEADER_DETECTION_PROMPT,
    PLATFORM_DETECTION_PROMPT,
    COLUMN_MAPPING_PROMPT,
    AMBIGUOUS_DATA_PROMPT,
)
from schema import STANDARD_COLUMNS

# Confidence thresholds — below these we call Claude
HEADER_CONFIDENCE_THRESHOLD = 0.70
PLATFORM_CONFIDENCE_THRESHOLD = 0.65

DEFAULT_MODEL = "claude-opus-4-5"


def clean_file(input_path: str, config: dict) -> dict:
    """
    Main entry point. Clean a raw marketing platform CSV and return a result dict.

    config keys:
        api_key (str)          : Anthropic API key
        model (str)            : Claude model ID (default: claude-opus-4-5)
        output_path (str)      : Where to write cleaned CSV (optional)
        output_format (str)    : 'csv', 'json', or 'both' (default: 'csv')
        platform_hint (str)    : Skip platform detection if already known
        verbose (bool)         : Print progress to stdout
        dry_run (bool)         : Process but don't write output files
    """
    state = _init_state(input_path, config)

    try:
        client = _make_client(config)

        # ── Step 1: Read raw lines ───────────────────────────────────────────
        _log(state, "Reading raw file...")
        raw_lines, encoding = _read_raw_lines(input_path)
        if not raw_lines:
            return _fail(state, "File is empty or could not be read")

        # ── Step 2: Detect header row ────────────────────────────────────────
        _log(state, "Detecting header row...")
        header_result = detector.detect_header_row(raw_lines)

        if header_result["confidence"] < HEADER_CONFIDENCE_THRESHOLD:
            _log(state, f"Low confidence ({header_result['confidence']:.0%}), asking Claude...")
            header_result = _ask_claude_header(client, raw_lines, header_result, state)

        header_idx = header_result["header_row_index"]
        state["metadata_rows_skipped"] = header_result["skipped_rows"]
        state["header_row_index"] = header_idx
        _log(state, f"Header at row {header_idx} (skipped {header_result['skipped_rows']} metadata rows) [{header_result['method']}]")

        # ── Step 3: Parse into DataFrame ─────────────────────────────────────
        _log(state, "Parsing CSV...")
        try:
            df = pd.read_csv(
                input_path,
                skiprows=header_idx,
                header=0,
                encoding=encoding,
                dtype=str,          # read everything as string — we do our own type parsing
                keep_default_na=False,
            )
        except Exception as e:
            return _fail(state, f"Failed to parse CSV after row detection: {e}")

        state["rows_input"] = len(df)
        _log(state, f"Loaded {len(df)} rows, {len(df.columns)} columns")

        # ── Step 4: Detect and strip footer rows ─────────────────────────────
        _log(state, "Detecting footer rows...")
        footer_result = detector.detect_footer_rows(df)
        if footer_result["footer_start_index"] is not None:
            n_before = len(df)
            df = df.iloc[: footer_result["footer_start_index"]].reset_index(drop=True)
            state["footer_rows_removed"] = n_before - len(df)
            _log(state, f"Removed {state['footer_rows_removed']} footer rows ({footer_result['footer_types']})")

        # ── Step 5: Detect platform ───────────────────────────────────────────
        platform_hint = config.get("platform_hint")
        if platform_hint:
            platform = platform_hint
            platform_confidence = 1.0
            platform_method = "hint"
        else:
            _log(state, "Detecting platform...")
            platform_result = detector.detect_platform(df.columns.tolist())

            if platform_result["confidence"] < PLATFORM_CONFIDENCE_THRESHOLD or not platform_result["platform"]:
                _log(state, f"Low confidence ({platform_result['confidence']:.0%}), asking Claude...")
                platform_result = _ask_claude_platform(client, df, state)

            platform = platform_result["platform"] or "unknown"
            platform_confidence = platform_result["confidence"]
            platform_method = platform_result["method"]

        state["platform"] = platform
        state["platform_confidence"] = platform_confidence
        _log(state, f"Platform: {platform} ({platform_confidence:.0%}) [{platform_method}]")

        # ── Step 6: Map column names ──────────────────────────────────────────
        _log(state, "Mapping column names...")

        def _claude_column_callback(pending_cols, plt, df_sample):
            return _ask_claude_column_mapping(client, pending_cols, plt, df_sample, state)

        column_map = normalizer.normalize_columns(
            raw_columns=df.columns.tolist(),
            platform=platform,
            claude_callback=_claude_column_callback,
            df_sample=df.head(3),
        )

        state["column_map"] = column_map
        state["unmapped_columns"] = normalizer.get_unmapped_columns(column_map)

        if state["unmapped_columns"]:
            state["warnings"].append(
                f"Could not map {len(state['unmapped_columns'])} columns: {state['unmapped_columns']}"
            )

        _log(state, f"Mapped {len(column_map)} columns ({len(state['unmapped_columns'])} unmapped)")

        # ── Step 7: Infer types and clean data ────────────────────────────────
        _log(state, "Cleaning data...")
        column_types = cleaner.infer_column_types(df, column_map)
        df = cleaner.clean_dataframe(df, column_types)
        df = cleaner.remove_empty_rows(df)

        # Add platform column
        df["platform"] = platform

        # ── Step 8: Build standardized output ────────────────────────────────
        _log(state, "Building standard output schema...")
        df_out = normalizer.build_output_dataframe(df, column_map)

        state["rows_output"] = len(df_out)
        state["rows_removed"] = state["rows_input"] - state["rows_output"]

        # ── Step 9: Write output ──────────────────────────────────────────────
        if not config.get("dry_run", False):
            output_path = config.get("output_path") or _default_output_path(input_path)
            output_format = config.get("output_format", "csv")
            _write_output(df_out, output_path, output_format, state)
            state["output_path"] = output_path
        else:
            state["output_path"] = None
            _log(state, "Dry run — no files written")

        state["success"] = True
        state["dataframe"] = df_out  # available for in-process callers
        _log(state, f"Done. {state['rows_output']} clean rows.")

    except Exception as e:
        return _fail(state, str(e))

    return _build_result(state)


# ── Claude call helpers ───────────────────────────────────────────────────────

def _ask_claude_header(client, raw_lines: list[str], heuristic: dict, state: dict) -> dict:
    """Ask Claude to confirm or correct the header row detection."""
    rows_text = "\n".join(
        f"[{i}] {line.strip()}" for i, line in enumerate(raw_lines[:15])
    )
    prompt = HEADER_DETECTION_PROMPT.format(
        n_rows=min(15, len(raw_lines)),
        rows_text=rows_text,
        heuristic_index=heuristic["header_row_index"],
        confidence=heuristic["confidence"],
    )
    response = _call_claude(client, prompt, max_tokens=256, state=state)
    parsed = _parse_json(response)
    return detector.merge_claude_header_result(heuristic, parsed)


def _ask_claude_platform(client, df: pd.DataFrame, state: dict) -> dict:
    """Ask Claude to identify the advertising platform."""
    headers = ", ".join(df.columns.tolist())
    sample_rows = df.head(3).to_string(index=False)
    prompt = PLATFORM_DETECTION_PROMPT.format(
        headers=headers,
        sample_rows=sample_rows,
    )
    response = _call_claude(client, prompt, max_tokens=256, state=state)
    parsed = _parse_json(response)
    return detector.merge_claude_platform_result(parsed)


def _ask_claude_column_mapping(
    client,
    pending_cols: list[str],
    platform: str,
    df_sample: Optional[pd.DataFrame],
    state: dict,
) -> dict:
    """Ask Claude to map unknown column names to standard schema fields."""
    # Build columns_with_samples text
    lines = []
    for col in pending_cols:
        if df_sample is not None and col in df_sample.columns:
            samples = df_sample[col].dropna().astype(str).tolist()[:3]
            sample_str = ", ".join(f'"{v}"' for v in samples)
        else:
            sample_str = "(no sample data)"
        lines.append(f"  {col}: [{sample_str}]")
    columns_with_samples = "\n".join(lines)

    prompt = COLUMN_MAPPING_PROMPT.format(
        platform=platform or "unknown",
        columns_with_samples=columns_with_samples,
        standard_fields=", ".join(STANDARD_COLUMNS),
    )
    response = _call_claude(client, prompt, max_tokens=1024, state=state)
    parsed = _parse_json(response)
    return parsed.get("mappings", {})


def _call_claude(client, prompt: str, max_tokens: int, state: dict) -> str:
    """Make a single Claude API call and return the text response."""
    state["claude_calls"] += 1
    message = client.messages.create(
        model=state["model"],
        max_tokens=max_tokens,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _parse_json(text: str) -> dict:
    """Extract and parse JSON from Claude's response."""
    # Claude sometimes wraps JSON in ```json ... ``` blocks
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract first JSON object
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        return {}


# ── Output helpers ────────────────────────────────────────────────────────────

def _write_output(df: pd.DataFrame, output_path: str, fmt: str, state: dict):
    base = output_path.replace(".csv", "").replace(".json", "")
    if fmt in ("csv", "both"):
        df.to_csv(f"{base}.csv", index=False)
        _log(state, f"Wrote CSV: {base}.csv")
    if fmt in ("json", "both"):
        df.to_json(f"{base}.json", orient="records", indent=2, date_format="iso")
        _log(state, f"Wrote JSON: {base}.json")


def _default_output_path(input_path: str) -> str:
    base = input_path.rsplit(".", 1)[0]
    return f"{base}_cleaned.csv"


def _read_raw_lines(path: str):
    """Try multiple encodings and return (lines, encoding_used)."""
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            with open(path, "r", encoding=enc, errors="strict") as f:
                lines = f.readlines()
            return lines, enc
        except (UnicodeDecodeError, LookupError):
            continue
    return [], "utf-8"


def _make_client(config: dict) -> anthropic.Anthropic:
    api_key = config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "Anthropic API key required. Set ANTHROPIC_API_KEY env var or pass api_key in config."
        )
    return anthropic.Anthropic(api_key=api_key)


# ── State helpers ─────────────────────────────────────────────────────────────

def _init_state(input_path: str, config: dict) -> dict:
    return {
        "input_path": input_path,
        "output_path": None,
        "rows_input": 0,
        "rows_output": 0,
        "rows_removed": 0,
        "metadata_rows_skipped": 0,
        "footer_rows_removed": 0,
        "header_row_index": 0,
        "platform": "unknown",
        "platform_confidence": 0.0,
        "column_map": {},
        "unmapped_columns": [],
        "claude_calls": 0,
        "model": config.get("model", DEFAULT_MODEL),
        "verbose": config.get("verbose", False),
        "success": False,
        "dataframe": None,
        "warnings": [],
        "errors": [],
    }


def _fail(state: dict, error_msg: str) -> dict:
    state["errors"].append(error_msg)
    state["success"] = False
    return _build_result(state)


def _build_result(state: dict) -> dict:
    return {
        "success": state["success"],
        "output_path": state["output_path"],
        "rows_input": state["rows_input"],
        "rows_output": state["rows_output"],
        "rows_removed": state["rows_removed"],
        "metadata_rows_skipped": state["metadata_rows_skipped"],
        "footer_rows_removed": state["footer_rows_removed"],
        "header_row_index": state["header_row_index"],
        "platform": state["platform"],
        "platform_confidence": state["platform_confidence"],
        "column_map": state["column_map"],
        "unmapped_columns": state["unmapped_columns"],
        "claude_calls": state["claude_calls"],
        "warnings": state["warnings"],
        "errors": state["errors"],
        "dataframe": state.get("dataframe"),  # None in CLI context
    }


def _log(state: dict, msg: str):
    if state.get("verbose"):
        print(f"  [data-cleaner] {msg}")
