#!/usr/bin/env python3
"""
Solar & Energy Performance Monthly Report Generator
Tailored for Inverex Inverters & Obsidian Vault Integration.
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np

# Optional chart plotting support
try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# Default target Obsidian vault path
DEFAULT_VAULT_MONTHLY_REPORTS_DIR = Path(
    "/Users/ishop/documents/Personal Vault/Solar/Monthly Reports"
)


def load_and_preprocess(csv_path: str):
    """Loads CSV and prepares continuous timestamps and delta hours."""
    print(f"[*] Reading telemetry from: {csv_path}")
    df = pd.read_csv(csv_path, low_memory=False)
    
    # Parse timestamps and sort chronologically
    df['Create Time'] = pd.to_datetime(df['Create Time'])
    df = df.sort_values('Create Time').reset_index(drop=True)
    
    # Extract target month and year based on dominant month in file
    month_counts = df['Create Time'].dt.to_period('M').value_counts()
    target_period = month_counts.index[0]
    target_year = target_period.year
    target_month = target_period.month
    
    # Filter strictly for the primary month
    df_month = df[df['Create Time'].dt.to_period('M') == target_period].copy()
    
    # Calculate time delta (dt) in hours, capped at 15 mins (0.25 hrs) to prevent gap skew
    dt_seconds = df_month['Create Time'].diff().dt.total_seconds().fillna(300)
    df_month['dt_hours'] = (dt_seconds / 3600.0).clip(lower=0, upper=0.25)
    
    return df_month, target_year, target_month


def calculate_metrics(df: pd.DataFrame, year: int, month: int):
    """Calculates all core solar, battery, grid, resilience, and diagnostic metrics."""
    # 1. Energy Integrals (kWh) = Power (W) * dt (hours) / 1000
    solar_kwh = (df['Pv Input Power 1'] * df['dt_hours'] / 1000.0).sum()
    grid_import_kwh = (df['Grid Power Input Active Total'] * df['dt_hours'] / 1000.0).sum()
    home_load_kwh = (df['Ac Output Active Power Total'] * df['dt_hours'] / 1000.0).sum()
    bat_charge_kwh = (df['Battery Charging Power'] * df['dt_hours'] / 1000.0).sum()
    bat_discharge_kwh = (df['Battery Discharging Power'] * df['dt_hours'] / 1000.0).sum()
    
    # Self-Sufficiency / Independence Ratio (%)
    solar_supplied_kwh = max(0.0, home_load_kwh - grid_import_kwh)
    self_sufficiency_pct = (solar_supplied_kwh / home_load_kwh * 100) if home_load_kwh > 0 else 0.0
    self_sufficiency_pct = min(100.0, max(0.0, self_sufficiency_pct))
    
    # Battery Round-Trip Efficiency (RTE %)
    battery_rte = (bat_discharge_kwh / bat_charge_kwh * 100) if bat_charge_kwh > 0 else 0.0
    
    # 2. Daily Solar Curtailment ("Wasted Potential" estimate)
    df['hour'] = df['Create Time'].dt.hour
    curtailed_mask = (
        (df['hour'] >= 10) & 
        (df['hour'] <= 15) & 
        (df['Battery Voltage'] >= 27.0) & 
        (df['Pv Input Power 1'] < 150)
    )
    curtailment_kwh = (600.0 * df.loc[curtailed_mask, 'dt_hours'] / 1000.0).sum()
    
    # 3. Grid Reliability & Outages
    is_outage = (df['Work Mode'] == 'B') | (df['Grid Voltage R'] < 50.0)
    outage_hours = (is_outage * df['dt_hours']).sum()
    total_hours = df['dt_hours'].sum()
    outage_pct = (outage_hours / total_hours * 100) if total_hours > 0 else 0.0
    backup_energy_kwh = (df.loc[is_outage, 'Ac Output Active Power Total'] * df.loc[is_outage, 'dt_hours'] / 1000.0).sum()
    
    # Outage Granularity (Incidents, Longest Outage, Average Duration)
    outage_blocks = (is_outage != is_outage.shift()).cumsum()
    outage_groups = df[is_outage].groupby(outage_blocks[is_outage])
    
    incident_durations = outage_groups['dt_hours'].sum()
    incident_starts = outage_groups['Create Time'].first()
    
    # Filter out 1-sample blips (< 6 minutes)
    real_outages = incident_durations[incident_durations >= 0.1]
    total_blackout_incidents = len(real_outages)
    avg_outage_hours = real_outages.mean() if total_blackout_incidents > 0 else 0.0
    
    if total_blackout_incidents > 0:
        longest_idx = real_outages.idxmax()
        longest_outage_hours = real_outages.loc[longest_idx]
        longest_outage_start = incident_starts.loc[longest_idx].strftime('%b %d, %I:%M %p')
    else:
        longest_outage_hours = 0.0
        longest_outage_start = "None"

    # 4. Grid Power Quality (When Grid is connected)
    grid_connected = (df['Grid Voltage R'] >= 50.0) & (df['Work Mode'] == 'L')
    if grid_connected.any():
        grid_volts = df.loc[grid_connected, 'Grid Voltage R']
        min_grid_volt = grid_volts.min()
        max_grid_volt = grid_volts.max()
        avg_grid_volt = grid_volts.mean()
        brownout_count = (grid_volts < 180.0).sum()
        surge_count = (grid_volts > 250.0).sum()
    else:
        min_grid_volt = max_grid_volt = avg_grid_volt = 0.0
        brownout_count = surge_count = 0

    # 5. Peaks & Electricals
    peak_solar_w = df['Pv Input Power 1'].max()
    
    # Peak Household Load & Timestamp
    peak_load_idx = df['Ac Output Active Power Total'].idxmax()
    peak_load_w = df.loc[peak_load_idx, 'Ac Output Active Power Total']
    peak_load_time = df.loc[peak_load_idx, 'Create Time'].strftime('%b %d at %I:%M %p')
    peak_load_pct = df.loc[peak_load_idx, 'Ac OutputLoad Total'] if 'Ac OutputLoad Total' in df.columns else np.nan
    
    min_bat_volt = df['Battery Voltage'].min()
    max_bat_volt = df['Battery Voltage'].max()
    
    # High Battery Discharge Current (>40A)
    high_discharge_events = (df['Discharging Current'] > 40.0).sum() if 'Discharging Current' in df.columns else 0

    # 6. Thermal Health & Fault Monitoring
    max_inverter_temp = df['Inner Temperature'].max() if 'Inner Temperature' in df.columns else np.nan
    hours_above_50c = (df.loc[df['Inner Temperature'] > 50.0, 'dt_hours'].sum()) if 'Inner Temperature' in df.columns else 0.0
    
    # Faults
    total_fault_events = (df['Fault 1'] > 0).sum() if 'Fault 1' in df.columns else 0

    # Power Factor (Median when load > 50W)
    load_mask = df['Ac Output Active Power Total'] > 50
    valid_pf = (
        df.loc[load_mask, 'Ac Output Active Power Total'] / 
        df.loc[load_mask, 'Ac Output Apparent Power Total'].replace(0, np.nan)
    ).dropna()
    avg_pf = valid_pf.median() if len(valid_pf) > 0 else 0.8
    
    num_days = df['Create Time'].dt.date.nunique()
    avg_daily_solar = solar_kwh / num_days if num_days > 0 else 0
    avg_daily_load = home_load_kwh / num_days if num_days > 0 else 0

    return {
        "year": year,
        "month": month,
        "num_days": num_days,
        "solar_kwh": solar_kwh,
        "grid_import_kwh": grid_import_kwh,
        "home_load_kwh": home_load_kwh,
        "bat_charge_kwh": bat_charge_kwh,
        "bat_discharge_kwh": bat_discharge_kwh,
        "self_sufficiency_pct": self_sufficiency_pct,
        "battery_rte": battery_rte,
        "curtailment_kwh": curtailment_kwh,
        "outage_hours": outage_hours,
        "outage_pct": outage_pct,
        "total_blackout_incidents": total_blackout_incidents,
        "avg_outage_hours": avg_outage_hours,
        "longest_outage_hours": longest_outage_hours,
        "longest_outage_start": longest_outage_start,
        "backup_energy_kwh": backup_energy_kwh,
        "min_grid_volt": min_grid_volt,
        "max_grid_volt": max_grid_volt,
        "avg_grid_volt": avg_grid_volt,
        "brownout_count": brownout_count,
        "surge_count": surge_count,
        "peak_solar_w": peak_solar_w,
        "peak_load_w": peak_load_w,
        "peak_load_time": peak_load_time,
        "peak_load_pct": peak_load_pct,
        "min_bat_volt": min_bat_volt,
        "max_bat_volt": max_bat_volt,
        "high_discharge_events": high_discharge_events,
        "max_inverter_temp": max_inverter_temp,
        "hours_above_50c": hours_above_50c,
        "total_fault_events": total_fault_events,
        "avg_pf": avg_pf,
        "avg_daily_solar": avg_daily_solar,
        "avg_daily_load": avg_daily_load,
    }


def generate_charts(df: pd.DataFrame, assets_dir: Path, year: int, month: int):
    """Generates clean PNG visual assets for Obsidian note embedding."""
    if not HAS_MATPLOTLIB:
        print("[!] Matplotlib not installed. Skipping PNG chart creation.")
        return {}
    
    assets_dir.mkdir(parents=True, exist_ok=True)
    chart_files = {}

    plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
    
    # 1. Daily Energy Balance Stacked Bar Chart
    df['date'] = df['Create Time'].dt.date
    daily = df.groupby('date').apply(lambda g: pd.Series({
        'Solar (kWh)': (g['Pv Input Power 1'] * g['dt_hours'] / 1000).sum(),
        'Grid (kWh)': (g['Grid Power Input Active Total'] * g['dt_hours'] / 1000).sum(),
        'Load (kWh)': (g['Ac Output Active Power Total'] * g['dt_hours'] / 1000).sum()
    })).reset_index()

    fig, ax = plt.subplots(figsize=(10, 4.5), dpi=150)
    x = np.arange(len(daily))
    width = 0.35
    
    ax.bar(x - width/2, daily['Solar (kWh)'], width, label='Solar Generated', color='#f59e0b', alpha=0.9)
    ax.bar(x + width/2, daily['Grid (kWh)'], width, label='Grid Imported', color='#ef4444', alpha=0.85)
    ax.plot(x, daily['Load (kWh)'], color='#3b82f6', marker='o', markersize=3, linewidth=1.5, label='Home Demand')
    
    ax.set_title(f'Daily Energy Generation vs. Import ({year}-{month:02d})', fontsize=12, fontweight='bold', pad=12)
    ax.set_xlabel('Day of Month', fontsize=10)
    ax.set_ylabel('Energy (kWh)', fontsize=10)
    ax.set_xticks(x[::2])
    ax.set_xticklabels([d.strftime('%d') for d in daily['date'][::2]])
    ax.legend(frameon=True)
    plt.tight_layout()
    
    daily_chart_path = assets_dir / f"{year}-{month:02d}-daily-energy.png"
    plt.savefig(daily_chart_path)
    plt.close()
    chart_files['daily_energy'] = daily_chart_path.name

    # 2. 24-Hour Diurnal Hourly Curve
    hourly = df.groupby('hour').agg({
        'Pv Input Power 1': 'mean',
        'Ac Output Active Power Total': 'mean',
        'Battery Discharging Power': 'mean',
        'Battery Charging Power': 'mean'
    }).reset_index()

    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=150)
    ax.plot(hourly['hour'], hourly['Pv Input Power 1'], label='Solar PV (W)', color='#f59e0b', linewidth=2.5)
    ax.plot(hourly['hour'], hourly['Ac Output Active Power Total'], label='Home Load (W)', color='#3b82f6', linewidth=2)
    ax.plot(hourly['hour'], hourly['Battery Discharging Power'], label='Battery Discharging (W)', color='#8b5cf6', linestyle='--', linewidth=1.5)
    ax.plot(hourly['hour'], hourly['Battery Charging Power'], label='Battery Charging (W)', color='#10b981', linestyle=':', linewidth=1.5)

    ax.set_title('Average 24-Hour Diurnal Power Profile (Hourly)', fontsize=12, fontweight='bold', pad=12)
    ax.set_xlabel('Hour of Day (00:00 - 23:00)', fontsize=10)
    ax.set_ylabel('Average Power (Watts)', fontsize=10)
    ax.set_xticks(range(0, 24, 2))
    ax.legend(frameon=True)
    plt.tight_layout()

    diurnal_chart_path = assets_dir / f"{year}-{month:02d}-diurnal-profile.png"
    plt.savefig(diurnal_chart_path)
    plt.close()
    chart_files['diurnal_profile'] = diurnal_chart_path.name

    return chart_files


def build_obsidian_markdown(metrics: dict, chart_files: dict) -> str:
    """Builds clean, Obsidian-native markdown with YAML frontmatter, callouts, and audit tables."""
    year = metrics['year']
    month = f"{metrics['month']:02d}"
    
    # Fault evaluation string
    if metrics['total_fault_events'] == 0:
        fault_status = "✅ Clean (0 hardware trips)"
    else:
        fault_status = f"⚠️ Warning ({metrics['total_fault_events']} trips logged)"
    
    # Format charts block
    charts_md = ""
    if chart_files:
        charts_md = f"""
## 📊 Energy Performance Visualizations

### Daily Energy Harvest & Grid Dependence
![[{chart_files.get('daily_energy', '')}]]

### 24-Hour Diurnal Curve (Average Day Profile)
![[{chart_files.get('diurnal_profile', '')}]]
"""

    md = f"""---
type: solar-report
year: {year}
month: {month}
date: {year}-{month}
solar_generation_kwh: {metrics['solar_kwh']:.2f}
grid_imported_kwh: {metrics['grid_import_kwh']:.2f}
household_consumed_kwh: {metrics['home_load_kwh']:.2f}
battery_charged_kwh: {metrics['bat_charge_kwh']:.2f}
battery_discharged_kwh: {metrics['bat_discharge_kwh']:.2f}
self_sufficiency_pct: {metrics['self_sufficiency_pct']:.1f}
blackout_hours: {metrics['outage_hours']:.1f}
outage_pct: {metrics['outage_pct']:.1f}
longest_outage_hours: {metrics['longest_outage_hours']:.1f}
fault_events: {metrics['total_fault_events']}
tags:
  - solar/monthly-report
  - inverex
  - energy-audit
---

# ☀️ Solar & Energy Performance Report: {year}-{month}

> [!summary] Executive Monthly Summary
> - **Total Clean Solar Harvested**: **`{metrics['solar_kwh']:.1f} kWh`** (Daily Avg: `{metrics['avg_daily_solar']:.1f} kWh/day`)
> - **Total Household Consumption**: **`{metrics['home_load_kwh']:.1f} kWh`** (Daily Avg: `{metrics['avg_daily_load']:.1f} kWh/day`)
> - **Solar Independence Ratio**: **`{metrics['self_sufficiency_pct']:.1f}%`** of home power was provided off-grid
> - **Grid Purchased**: **`{metrics['grid_import_kwh']:.1f} kWh`**
> - **Total Load Shedding**: **`{metrics['outage_hours']:.1f} Hours`** (`{metrics['outage_pct']:.1f}%` of month)

---

## ⚡ Energy Balance Breakdown

| Metric | Energy (kWh) | Share / Note |
| :--- | :--- | :--- |
| **Gross Solar Generation** | `{metrics['solar_kwh']:.2f} kWh` | Harvested clean energy |
| **Utility Grid Import** | `{metrics['grid_import_kwh']:.2f} kWh` | Purchased from power utility |
| **Total Household Consumption** | `{metrics['home_load_kwh']:.2f} kWh` | Total AC electricity consumed |
| **Estimated Midday Curtailment** | `{metrics['curtailment_kwh']:.2f} kWh` | Untapped solar (battery full & low load) |

---

## 🔋 Battery Cycling & Bank Health

> [!info] Storage Dynamics
> - **Energy Charged**: `{metrics['bat_charge_kwh']:.2f} kWh`
> - **Energy Discharged**: `{metrics['bat_discharge_kwh']:.2f} kWh`
> - **Observed Round-Trip Efficiency (RTE)**: `{metrics['battery_rte']:.1f}%`
> - **Voltage Window**: `{metrics['min_bat_volt']:.1f}V` (min under load) to `{metrics['max_bat_volt']:.1f}V` (max absorption)
> - **High-Current Discharges (>40A)**: `{metrics['high_discharge_events']}` incidents

---

## 🚨 Grid Outage & Resilience Audit

> [!danger] Load Shedding Impact
> - **Total Blackout Time**: `{metrics['outage_hours']:.1f} Hours` (`{metrics['outage_pct']:.1f}%` grid absence)
> - **Longest Single Blackout**: **`{metrics['longest_outage_hours']:.1f} Hours`** (Started: {metrics['longest_outage_start']})
> - **Average Blackout Duration**: `{metrics['avg_outage_hours']:.1f} Hours` per incident
> - **Critical Backup Energy Delivered**: `{metrics['backup_energy_kwh']:.2f} kWh` kept running during outages
> - **Recorded Outage Incidents**: `{metrics['total_blackout_incidents']}` blackout events

### ⚡ Grid Power Quality
| Parameter | Value | Assessment |
| :--- | :--- | :--- |
| **Average Grid Voltage** | `{metrics['avg_grid_volt']:.1f} V` | Normal nominal line: 220V - 230V |
| **Voltage Extremes** | `{metrics['min_grid_volt']:.1f} V` min / `{metrics['max_grid_volt']:.1f} V` max | Stability range |
| **Severe Brownouts (<180V)** | `{metrics['brownout_count']}` readings | {'Stable line' if metrics['brownout_count'] == 0 else 'Risk of inverter rejecting grid'} |
| **Voltage Surges (>250V)** | `{metrics['surge_count']}` readings | {'No surge hazard' if metrics['surge_count'] == 0 else 'Appliance protection risk'} |

---

## 🛠️ Electrical & System Diagnostics

| Diagnostic Parameter | Recorded Value | Evaluation |
| :--- | :--- | :--- |
| **Peak Instantaneous Solar** | `{metrics['peak_solar_w']:.0f} W` | Max PV harvest yield |
| **Peak Household Demand** | `{metrics['peak_load_w']:.0f} W` ({metrics['peak_load_pct']:.0f}% load) | Occurred on **{metrics['peak_load_time']}** |
| **Average Power Factor (PF)** | `{metrics['avg_pf']:.2f}` | {'Healthy inductive factor' if metrics['avg_pf'] >= 0.85 else 'Low PF (reactive motor load penalty)'} |
| **Max Inverter Temperature** | `{metrics['max_inverter_temp']:.1f} °C` | Hours above 50°C: **`{metrics['hours_above_50c']:.1f} hrs`** |
| **Hardware Fault Trips (`Fault 1`)**| `{metrics['total_fault_events']}` | {fault_status} |

{charts_md}

---
*Report generated automatically from Inverex inverter telemetry data.*
"""
    return md


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_obsidian_report.py <path_to_csv_file> [optional_vault_reports_path]")
        print("Example: python3 generate_obsidian_report.py csv/inverex-jan-2025.csv")
        sys.exit(1)

    csv_path = sys.argv[1]
    reports_base_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_VAULT_MONTHLY_REPORTS_DIR

    if not os.path.exists(csv_path):
        print(f"[!] Error: CSV file not found at: {csv_path}")
        sys.exit(1)

    # 1. Process Telemetry
    df, year, month = load_and_preprocess(csv_path)

    # 2. Calculate Core Metrics
    print("[*] Computing Phase 1 metrics (with Grid Quality & Diagnostics)...")
    metrics = calculate_metrics(df, year, month)

    # 3. Setup Obsidian Directory Hierarchy: <Vault>/<Year>/
    year_dir = reports_base_dir / str(year)
    assets_dir = reports_base_dir / "assets" / f"{year}-{month:02d}"
    year_dir.mkdir(parents=True, exist_ok=True)

    # 4. Generate Visualizations (if matplotlib is available)
    print(f"[*] Generating charts in: {assets_dir}")
    chart_files = generate_charts(df, assets_dir, year, month)

    # 5. Build Markdown Content
    markdown_content = build_obsidian_markdown(metrics, chart_files)

    # 6. Save Target Report File
    report_filename = f"{year}-{month:02d}-solar-report.md"
    report_path = year_dir / report_filename
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)

    print(f"\n[SUCCESS] Monthly Report written to:")
    print(f" -> {report_path.resolve()}\n")


if __name__ == "__main__":
    main()
