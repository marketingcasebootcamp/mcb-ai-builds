# Data Cleaner Agent

Cleans raw marketing platform CSV exports into a consistent, analysis-ready schema.

Handles the real-world mess that every marketer deals with: metadata rows before the actual header, Total/Grand Total rows at the bottom, wildly different column names across platforms, currency symbols, percentages stored as strings, and inconsistent date formats.

---

## What it does

| Problem | How it's solved |
|---|---|
| 2–4 metadata rows before the real header | Heuristic detection + Claude fallback |
| "Total" / "Grand Total" rows at the bottom | Pattern matching + statistical detection |
| Different column names per platform | Known synonym maps + fuzzy match + Claude for unknowns |
| `$1,234.56` stored as string | Currency cleaner → plain float |
| `12.5%` or `0.125` both meaning CTR | Percentage normalizer → always decimal (0.125) |
| `Jan 1, 2024` / `01/01/24` / `Q1 2024` | Date normalizer → always `YYYY-MM-DD` |
| `1,234,567` vs `1.234.567` (European) | Number string disambiguator |
| Unknown platform format | Claude identifies from column headers |

---

## Supported platforms

| Platform | Slug |
|---|---|
| Google Ads | `google_ads` |
| Meta (Facebook/Instagram) | `meta` |
| Google Analytics 4 | `ga4` |
| TikTok Ads | `tiktok` |
| LinkedIn Campaign Manager | `linkedin` |
| Microsoft Ads | `microsoft_ads` |
| Pinterest Ads | `pinterest` |
| Unknown / custom | Detected automatically by Claude |

---

## Output schema

Every cleaned file has the same columns, in this order:

| Column | Type | Notes |
|---|---|---|
| `date` | string | `YYYY-MM-DD` always |
| `platform` | string | Platform slug |
| `campaign_name` | string | |
| `campaign_id` | string | |
| `ad_group_name` | string | Ad set / ad group |
| `ad_group_id` | string | |
| `ad_name` | string | |
| `ad_id` | string | |
| `impressions` | float | |
| `reach` | float | |
| `clicks` | float | |
| `spend` | float | USD, no symbols |
| `conversions` | float | |
| `conversion_value` | float | USD |
| `ctr` | float | Decimal: `0.0125` not `1.25%` |
| `cpc` | float | USD |
| `cpm` | float | USD |
| `roas` | float | |
| `frequency` | float | |
| `video_views` | float | |
| `video_view_rate` | float | Decimal |
| `quality_score` | float | |
| `search_impression_share` | float | Decimal |

Columns from the original file that don't map to the schema are kept with a `raw_` prefix. Columns explicitly not useful (status flags, internal IDs, URLs) are dropped.

---

## Setup

```bash
cd agents/data-cleaner
pip install -r requirements.txt
cp .env.example .env
# edit .env and add your ANTHROPIC_API_KEY
```

---

## Usage

### CLI

```bash
# Basic
python runner.py my_google_ads_report.csv

# With options
python runner.py report.csv --output-path cleaned.csv --verbose

# Skip platform detection if you already know it
python runner.py report.csv --platform-hint google_ads

# Output both CSV and JSON
python runner.py report.csv --output-format both

# Test without writing files
python runner.py report.csv --dry-run --verbose
```

### As a library (from another agent or app)

```python
from agents.data_cleaner.runner import run

result = run({
    "input_path": "reports/google_ads_jan2025.csv",
    "output_format": "csv",
    "verbose": True,
})

if result["success"]:
    df = result["dataframe"]           # pandas DataFrame
    print(f"Platform: {result['platform']}")
    print(f"Rows cleaned: {result['rows_output']}")
    print(f"Claude calls made: {result['claude_calls']}")
else:
    print(result["errors"])
```

### Chain with other agents

```python
from agents.data_cleaner.runner import run as clean
from agents.insights_writer.runner import run as write_insights

# Step 1: clean the raw export
clean_result = clean({"input_path": "raw_report.csv"})

# Step 2: pass cleaned data to insights writer
if clean_result["success"]:
    insights = write_insights({
        "dataset": clean_result["dataframe"],
        "platform": clean_result["platform"],
    })
```

---

## File structure

```
agents/data-cleaner/
  runner.py       ← Entry point (CLI + importable run() function)
  agent.py        ← Orchestrates the full pipeline, owns all Claude API calls
  detector.py     ← Heuristic detection: header rows, platform, footer rows
  cleaner.py      ← Deterministic value cleaning: currency, %, dates, numbers
  normalizer.py   ← Column name mapping and output schema builder
  schema.py       ← All platform mappings, column synonyms, standard schema
  prompts.py      ← All Claude prompt templates
  requirements.txt
  .env.example
  metadata.yaml
  README.md
```

---

## When does it call Claude?

Claude is only called when heuristic confidence falls below a threshold — keeping the common case fast and free:

| Decision | Heuristic threshold | Claude called when |
|---|---|---|
| Header row detection | 70% confidence | File has unusual metadata rows |
| Platform detection | 65% confidence | Columns don't match known patterns |
| Column mapping | Exact + fuzzy match | Column name not in synonym map |

Typical usage: **0 Claude calls** for standard Google Ads / Meta exports. **1–2 calls** for unusual or custom exports. **3 calls max** for completely unknown formats.

---

## Limitations

- Input must be CSV (not XLSX, PDF, or API response)
- Multi-currency files: symbols are stripped but no FX conversion is done
- Two-row merged headers (some LinkedIn exports): flagged in warnings, not auto-merged
- Quarterly/monthly date granularity: mapped to first day of the period
