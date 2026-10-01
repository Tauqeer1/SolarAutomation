#!/usr/bin/env python3
"""
Orchestrator script:
1. Compares data/*.xlsx with csv/*.csv.
2. Converts any unprocessed .xlsx file to .csv via xlsx_to_csv.py.
3. Automatically triggers generate_obsidian_report.py for each new CSV.
"""

import sys
import subprocess
from pathlib import Path

# Paths relative to project root
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CSV_DIR = BASE_DIR / "csv"

XLSX_TO_CSV_SCRIPT = BASE_DIR / "xlsx_to_csv.py"
REPORT_SCRIPT = BASE_DIR / "generate_obsidian_report.py"


def run_command(cmd: list) -> bool:
    """Executes a command and streams output, returning True on success."""
    result = subprocess.run(cmd)
    return result.returncode == 0


def process_unprocessed_files():
    # Ensure folders exist
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CSV_DIR.mkdir(parents=True, exist_ok=True)

    xlsx_files = sorted(DATA_DIR.glob("*.xlsx"))

    if not xlsx_files:
        print("[!] No .xlsx files found in 'data/' directory.")
        return

    unprocessed_count = 0

    for xlsx_path in xlsx_files:
        # Ignore temporary Excel lock files (e.g. ~$filename.xlsx)
        if xlsx_path.name.startswith("~$"):
            continue

        target_csv_path = CSV_DIR / f"{xlsx_path.stem}.csv"

        if target_csv_path.exists():
            print(f"[SKIP] Already converted: {xlsx_path.name} -> {target_csv_path.name}")
            continue

        unprocessed_count += 1
        print(f"\n{'='*60}")
        print(f"[*] Found new file: {xlsx_path.name}")
        print(f"{'='*60}")

        # Step 1: Convert XLSX -> CSV
        print(f"\n[Step 1/2] Converting to CSV...")
        cmd_convert = [
            sys.executable,
            str(XLSX_TO_CSV_SCRIPT),
            str(xlsx_path),
            "-o",
            str(target_csv_path)
        ]

        if not run_command(cmd_convert):
            print(f"[!] Error: Conversion failed for {xlsx_path.name}. Skipping report generation.")
            continue

        # Step 2: Generate Obsidian Report
        print(f"\n[Step 2/2] Generating Obsidian Report...")
        cmd_report = [
            sys.executable,
            str(REPORT_SCRIPT),
            str(target_csv_path)
        ]

        if not run_command(cmd_report):
            print(f"[!] Error: Report generation failed for {target_csv_path.name}.")
        else:
            print(f"[SUCCESS] Processed {xlsx_path.name} successfully!\n")

    if unprocessed_count == 0:
        print("\nAll files are up to date. Nothing to process.")
    else:
        print(f"\n[DONE] Finished processing {unprocessed_count} new file(s).")


if __name__ == "__main__":
    process_unprocessed_files()
