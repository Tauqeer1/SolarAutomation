# SolarAutomation ☀️⚡

Automated monthly performance analysis and reporting pipeline for Inverex solar inverters, integrating telemetry data into Obsidian markdown reports with visualization charts.

## Features

- **Batch Excel to CSV Conversion**: Seamlessly converts multi-sheet or single-sheet inverter telemetry workbooks.
- **Analytics & Health Metrics**: Computes solar generation, grid imports, home consumption, self-sufficiency %, battery round-trip efficiency (RTE), solar curtailment estimates, and blackout/load-shedding impact.
- **Visualizations**: Automatically renders daily energy balance charts and 24-hour diurnal power profiles using `matplotlib`.
- **Obsidian Vault Integration**: Generates native Obsidian markdown reports complete with YAML frontmatter, audit tables, and callouts.
- **Automated Pipeline**: Watches for new raw files in `data/`, automatically converts them to `csv/`, and generates reports in one command.

## Project Structure

```text
SolarAutomation/
├── data/                         # Raw .xlsx export files (ignored by git)
├── csv/                          # Converted .csv files (ignored by git)
├── process_new_data.py           # Pipeline runner (detects new files and runs workflow)
├── xlsx_to_csv.py                # Excel to CSV conversion utility
├── generate_obsidian_report.py   # Analytics & Obsidian report generator
├── requirements.txt              # Core project dependencies
└── requirements-lock.txt         # Pinned environment dependencies
```

## Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone git@github.com:Tauqeer1/SolarAutomation.git
   cd SolarAutomation
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Automated Pipeline (Recommended)
Place your monthly `.xlsx` file into the `data/` folder and run:
```bash
python process_new_data.py
```
This will automatically:
1. Detect any new files in `data/`.
2. Convert them into `csv/`.
3. Generate the Obsidian report and save visual charts directly to your Obsidian vault.

### Manual Usage
If you prefer running individual steps manually:

- **Convert Excel to CSV:**
  ```bash
  python xlsx_to_csv.py data/<filename>.xlsx -o csv/<filename>.csv
  ```

- **Generate Obsidian Report:**
  ```bash
  python generate_obsidian_report.py csv/<filename>.csv
  ```

## Configuration
By default, reports and visual chart assets are written to:
`~/documents/Personal Vault/Solar/Monthly Reports/`

You can customize this path by editing `DEFAULT_VAULT_MONTHLY_REPORTS_DIR` inside [generate_obsidian_report.py](file:///Users/ishop/Documents/Projects/SolarAutomation/generate_obsidian_report.py) or by passing a custom vault path as an argument:
```bash
python generate_obsidian_report.py csv/<filename>.csv "/path/to/your/vault"
```
