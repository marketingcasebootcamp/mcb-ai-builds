"""
All LLM prompt templates in one place.
Use .format(**kwargs) to fill placeholders before passing to Claude.
No logic here — that belongs in agent.py.
"""

SYSTEM_PROMPT = """You are a senior data engineer specializing in marketing analytics.
You have processed thousands of CSV exports from Google Ads, Meta, GA4, TikTok, LinkedIn,
Microsoft Ads, Pinterest, and other advertising platforms.

You know every quirk: metadata rows before the real header, Total rows at the bottom,
inconsistent column naming across platform versions, currency symbols, percentage formatting.

Respond ONLY with valid JSON. No prose outside the JSON.
If you need to explain something, put it inside a "reasoning" or "notes" key."""

# ── Header detection ──────────────────────────────────────────────────────────

HEADER_DETECTION_PROMPT = """You are looking at the first {n_rows} rows of a CSV export from a marketing platform.

RAW ROWS (0-indexed, pipe-separated for readability):
{rows_text}

HEURISTIC RESULT: Automated analysis suggests the header row is at index {heuristic_index} with {confidence:.0%} confidence.

Your task: Identify which row index (0-based) contains the actual column headers.
The header row has column labels like "Campaign", "Impressions", "Cost", "Date", etc.
Rows before it are metadata: report title, date range, account name, applied filters.
The row immediately after the header should contain the first real data row.

Respond with JSON only:
{{
  "header_row_index": <integer>,
  "reasoning": "<one sentence explaining which signals identified it>",
  "confidence": <float 0.0 to 1.0>
}}"""

# ── Platform detection ────────────────────────────────────────────────────────

PLATFORM_DETECTION_PROMPT = """Identify which advertising platform produced this CSV export.

COLUMN HEADERS:
{headers}

SAMPLE DATA ROWS (first 3 rows):
{sample_rows}

Known platforms (use these exact slugs):
google_ads, meta, ga4, tiktok, linkedin, microsoft_ads, pinterest,
snapchat, amazon_ads, dv360, unknown

Respond with JSON only:
{{
  "platform": "<slug>",
  "reasoning": "<one sentence — cite the specific columns or values that identify it>",
  "confidence": <float 0.0 to 1.0>
}}"""

# ── Column mapping ────────────────────────────────────────────────────────────

COLUMN_MAPPING_PROMPT = """Map these unrecognized column names from a {platform} export to the standard marketing schema.

UNRECOGNIZED COLUMNS (with up to 3 sample values each):
{columns_with_samples}

STANDARD SCHEMA FIELDS YOU CAN MAP TO:
date, platform, campaign_name, campaign_id, ad_group_name, ad_group_id,
ad_name, ad_id, impressions, reach, clicks, spend, conversions,
conversion_value, ctr, cpc, cpm, roas, frequency, video_views,
video_view_rate, quality_score, search_impression_share

RULES:
- Map each column to the closest standard field, OR to null to drop it
- Use null for: internal IDs with no analytics value, status flags, URLs, notes fields
- If a column is a metric variant (e.g. "7-Day Click Conversions"), map it to the base metric
- Do NOT invent new standard field names outside the list above
- CTR/rates should map to their standard name — the cleaner will handle decimal conversion

Respond with JSON only:
{{
  "mappings": {{
    "<raw_column_name>": "<standard_field_or_null>",
    ...
  }},
  "notes": "<any important caveats, or empty string>"
}}"""

# ── Ambiguous data format ─────────────────────────────────────────────────────

AMBIGUOUS_DATA_PROMPT = """A column in this {platform} export has inconsistent formatting
that automated cleaning could not resolve.

COLUMN NAME: {column_name}
INTENDED STANDARD MAPPING: {standard_name}
SAMPLE VALUES (raw, unmodified):
{sample_values}

Determine the correct cleaning rule for this column.

Respond with JSON only:
{{
  "type": "<currency | percentage | number | date | text>",
  "already_decimal": <true or false>,
  "scale_factor": <number to multiply raw value by, usually 1 or 0.01>,
  "currency_symbol": "<detected symbol or empty string>",
  "notes": "<any important caveats, or empty string>"
}}"""
