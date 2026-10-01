import argparse
import os
import pandas as pd


def convert_xlsx_to_csv(xlsx_path, output_csv=None, sheet_name=None):
    if not os.path.exists(xlsx_path):
        print(f"Error: File '{xlsx_path}' does not exist.")
        return

    # Load the Excel file
    excel_file = pd.ExcelFile(xlsx_path)

    # Determine base name without extension
    base_name = os.path.splitext(xlsx_path)[0]

    # If a specific sheet is requested
    if sheet_name:
        if sheet_name not in excel_file.sheet_names:
            print(
                f"Error: Sheet '{sheet_name}' not found. Available sheets: {excel_file.sheet_names}"
            )
            return

        out_path = output_csv or f"{base_name}.csv"
        df = pd.read_excel(xlsx_path, sheet_name=sheet_name)
        df.to_csv(out_path, index=False, encoding="utf-8")
        print(f"Exported sheet '{sheet_name}' -> '{out_path}'")
        return

    # If the workbook has multiple sheets and no specific output name was requested,
    # export all sheets separately
    if len(excel_file.sheet_names) > 1 and not output_csv:
        print(
            f"Found multiple sheets ({len(excel_file.sheet_names)}). Exporting all:"
        )
        for name in excel_file.sheet_names:
            df = pd.read_excel(xlsx_path, sheet_name=name)
            out_path = f"{base_name}_{name}.csv"
            df.to_csv(out_path, index=False, encoding="utf-8")
            print(f" - {name} -> {out_path}")
    else:
        # Single sheet or explicitly given output_csv
        out_path = output_csv or f"{base_name}.csv"
        df = pd.read_excel(xlsx_path, sheet_name=0)
        df.to_csv(out_path, index=False, encoding="utf-8")
        print(f"Converted '{xlsx_path}' -> '{out_path}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert any Excel (.xlsx) file to CSV format."
    )
    parser.add_argument("input_file", help="Path to the .xlsx file")
    parser.add_argument(
        "-o",
        "--output",
        help="Optional output CSV path (default: same name with .csv extension)",
        default=None,
    )
    parser.add_argument(
        "-s",
        "--sheet",
        help="Optional specific sheet name to export",
        default=None,
    )

    args = parser.parse_args()
    convert_xlsx_to_csv(args.input_file, args.output, args.sheet)
