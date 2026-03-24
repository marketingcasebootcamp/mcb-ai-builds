"""
Data Cleaner Agent — Runner

Importable function for use by apps and other agents:
    from agents.data_cleaner.runner import run
    result = run({"input_path": "report.csv", "verbose": True})

CLI usage:
    python runner.py report.csv
    python runner.py report.csv --output-path cleaned.csv --verbose
    python runner.py report.csv --platform-hint google_ads --dry-run
    python runner.py report.csv --output-format both
"""

import argparse
import os
import sys

import agent


def run(config: dict) -> dict:
    """
    Clean a marketing platform CSV export.

    Args:
        config (dict): Configuration options.
            input_path (str)       : Path to raw CSV file. REQUIRED.
            output_path (str)      : Output path. Defaults to <input>_cleaned.csv
            output_format (str)    : 'csv', 'json', or 'both'. Default: 'csv'
            platform_hint (str)    : Skip detection — use known platform slug.
                                     Options: google_ads, meta, ga4, tiktok,
                                     linkedin, microsoft_ads, pinterest
            api_key (str)          : Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
            model (str)            : Claude model. Default: claude-opus-4-5
            verbose (bool)         : Print progress. Default: False
            dry_run (bool)         : Process but don't write files. Default: False

    Returns:
        dict with keys:
            success (bool)
            output_path (str | None)
            rows_input (int)
            rows_output (int)
            rows_removed (int)
            metadata_rows_skipped (int)
            footer_rows_removed (int)
            platform (str)
            platform_confidence (float)
            column_map (dict)
            unmapped_columns (list)
            claude_calls (int)
            warnings (list)
            errors (list)
            dataframe (pd.DataFrame | None)  — only when called as a library
    """
    input_path = config.get("input_path")
    if not input_path:
        return {
            "success": False,
            "errors": ["input_path is required"],
            "warnings": [],
        }

    if not os.path.isfile(input_path):
        return {
            "success": False,
            "errors": [f"File not found: {input_path}"],
            "warnings": [],
        }

    return agent.clean_file(input_path, config)


def main():
    parser = argparse.ArgumentParser(
        description="Clean marketing platform CSV exports into a standardized schema.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python runner.py report.csv
  python runner.py report.csv --output-path cleaned.csv --verbose
  python runner.py report.csv --platform-hint google_ads
  python runner.py report.csv --output-format both --dry-run
        """,
    )
    parser.add_argument("input_path", help="Path to raw CSV export")
    parser.add_argument("--output-path", help="Output file path (default: <input>_cleaned.csv)")
    parser.add_argument(
        "--output-format",
        choices=["csv", "json", "both"],
        default="csv",
        help="Output format (default: csv)",
    )
    parser.add_argument(
        "--platform-hint",
        choices=["google_ads", "meta", "ga4", "tiktok", "linkedin", "microsoft_ads", "pinterest"],
        help="Skip platform detection — specify platform directly",
    )
    parser.add_argument(
        "--model",
        default="claude-opus-4-5",
        help="Claude model ID (default: claude-opus-4-5)",
    )
    parser.add_argument("--api-key", help="Anthropic API key (or set ANTHROPIC_API_KEY env var)")
    parser.add_argument("--verbose", action="store_true", help="Print progress details")
    parser.add_argument("--dry-run", action="store_true", help="Process but don't write output")

    args = parser.parse_args()

    config = {
        "input_path": args.input_path,
        "output_path": args.output_path,
        "output_format": args.output_format,
        "platform_hint": args.platform_hint,
        "model": args.model,
        "api_key": args.api_key,
        "verbose": args.verbose,
        "dry_run": args.dry_run,
    }

    print(f"\nData Cleaner Agent")
    print(f"Input:  {args.input_path}")
    print("-" * 50)

    result = run(config)

    print()
    _print_summary(result)

    sys.exit(0 if result["success"] else 1)


def _print_summary(result: dict):
    status = "SUCCESS" if result["success"] else "FAILED"
    print(f"Status:             {status}")

    if result.get("errors"):
        for err in result["errors"]:
            print(f"Error:              {err}")
        return

    print(f"Platform:           {result['platform']} ({result['platform_confidence']:.0%} confidence)")
    print(f"Header row:         {result['header_row_index']}")
    print(f"Metadata rows:      {result['metadata_rows_skipped']} skipped")
    print(f"Footer rows:        {result['footer_rows_removed']} removed")
    print(f"Rows in:            {result['rows_input']}")
    print(f"Rows out:           {result['rows_output']}")
    print(f"Rows dropped:       {result['rows_removed']}")
    print(f"Columns mapped:     {len(result['column_map'])}")
    print(f"Unmapped columns:   {len(result['unmapped_columns'])}")
    print(f"Claude API calls:   {result['claude_calls']}")

    if result.get("output_path"):
        print(f"Output:             {result['output_path']}")

    if result.get("warnings"):
        print()
        print("Warnings:")
        for w in result["warnings"]:
            print(f"  ! {w}")

    if result.get("unmapped_columns"):
        print()
        print("Unmapped columns (kept with raw_ prefix):")
        for col in result["unmapped_columns"]:
            print(f"  - {col}")

    if result.get("column_map"):
        print()
        print("Column mapping:")
        for raw, std in result["column_map"].items():
            if std is None:
                print(f"  {raw:35s} → [dropped]")
            elif std == "_unmapped_":
                print(f"  {raw:35s} → raw_{raw.lower().replace(' ', '_')}")
            else:
                print(f"  {raw:35s} → {std}")


if __name__ == "__main__":
    main()
