# Solar & Energy Performance Report Specification

Based on telemetry analysis of the Inverex solar inverter dataset (`csv/inverex-apr-2025.csv`), this document outlines every critical metric, data point, and analytical section required to build a comprehensive, senior-grade home energy report.

---

## 1. Executive Summary & Energy Balance (The Macro View)

### 1.1 Total Household Energy Consumption ($\text{kWh}$)
* **Source Columns**: `Ac Output Active Power Total` (W), `Create Time`
* **Formula**: $\sum \left( P_{\text{load}} \times \frac{\Delta t}{1000} \right)$
* **Why It Is Necessary**: This is your baseline demand. Without knowing the exact total energy your household consumed during the month, you cannot measure solar coverage, evaluate savings, or properly size future upgrades.

### 1.2 Utility Grid Import ($\text{kWh}$)
* **Source Columns**: `Grid Power Input Active Total` (W), `Create Time`
* **Formula**: $\sum \left( P_{\text{grid}} \times \frac{\Delta t}{1000} \right)$
* **Why It Is Necessary**: Represents the actual units purchased from the power company. Comparing this against your utility bill allows you to verify billing accuracy and calculate financial savings.

### 1.3 Gross Solar Generation ($\text{kWh}$)
* **Source Columns**: `Pv Input Power 1` (W), `Create Time`
* **Formula**: $\sum \left( P_{\text{pv}} \times \frac{\Delta t}{1000} \right)$
* **Why It Is Necessary**: Measures the total clean energy harvested by your solar panels over the month, establishing the return on investment (ROI) of your photovoltaic system.

### 1.4 Solar Self-Sufficiency / Independence Ratio (%)
* **Formula**: $\frac{\text{Solar Generation Consumed Directly or via Battery}}{\text{Total Household Consumption}} \times 100$
* **Why It Is Necessary**: Quantifies your degree of energy independence from the national grid. A score of 80% means 80% of your power needs were met entirely by your own solar and battery setup.

---

## 2. Solar Harvesting & Curtailment (Efficiency Analysis)

### 2.1 Daytime Solar Curtailment / "Wasted Potential" ($\text{kWh}$)
* **Source Columns**: `Pv Input Power 1`, `Battery Voltage` (or `Battery Capacity`), `Ac Output Active Power Total`, `Create Time`
* **Condition**: Peak sunlight hours (10:00 AM – 3:00 PM) where battery is fully charged ($\ge 27.0\text{V}$) and generation drops to match small load demands.
* **Why It Is Necessary**: In off-grid/non-export setups, when the battery is full and house load is low, the inverter throttles solar panel output. Calculating throttled potential reveals how much "free" solar power was left on the table, guiding load-shifting decisions (e.g., timing water pumps, EV charging, or laundry).

### 2.2 Solar Generation Profile & Peak kW Yield
* **Source Columns**: `Pv Input Power 1`, `Solar Current Input 1`, `Pv Input Voltage 1`
* **Metrics**: Daily average solar profile (hourly curve), monthly peak generation (W), and average daily production ($\text{kWh/day}$).
* **Why It Is Necessary**: Identifies seasonal generation curves, panel degradation, or dirt accumulation. If a bright, cloudless midday does not produce expected peak wattage, panels may need cleaning or checking for shading.

---

## 3. Grid Reliability & Outage Audit (Resilience Analysis)

### 3.1 Total Hours of Load Shedding / Power Blackouts
* **Source Columns**: `Work Mode` (`B` vs `L`), `Grid Voltage R` ($< 50\text{V}$), `Status Grid`
* **Metrics**: Total blackout duration (hours & % of month), count of outage incidents, average blackout duration, and longest single blackout event.
* **Why It Is Necessary**: The data for April 2025 demonstrates that the grid was absent for over 75% of the month (~532 hours). Tracking outage severity proves the reliability value of the inverter/battery system as a life-safety backup.

### 3.2 Critical Backup Energy Delivered ($\text{kWh}$)
* **Source Columns**: `Ac Output Active Power Total` when `Work Mode == 'B'`
* **Why It Is Necessary**: Quantifies the exact amount of electricity delivered to keep your home running when the grid failed, measuring the true resilience provided by your system.

### 3.3 Grid Power Quality & Voltage Instability
* **Source Columns**: `Grid Voltage R`, `Grid Frequency`
* **Metrics**: Voltage min/max/average when grid is active, frequency drift outside 49.5 Hz – 50.5 Hz, and instances of severe brownouts ($< 180\text{V}$) or surges ($> 250\text{V}$).
* **Why It Is Necessary**: Poor grid quality causes premature appliance failure and forces the inverter to repeatedly reject grid power, triggering unnecessary battery cycling.

---

## 4. Battery Bank Health & Cycling Stress

### 4.1 Battery Energy Throughput (kWh In vs kWh Out)
* **Source Columns**: `Battery Charging Power` (W), `Battery Discharging Power` (W), `Create Time`
* **Metrics**: Total energy charged ($\text{kWh}_{\text{in}}$), total energy discharged ($\text{kWh}_{\text{out}}$).
* **Why It Is Necessary**: Tracks usage volume. Battery warranty and lifespan are directly tied to full equivalent cycle count (Throughput $\div$ Nominal Capacity).

### 4.2 Round-Trip Battery Efficiency (RTE %)
* **Formula**: $\frac{\sum \text{Battery Discharging Energy}}{\sum \text{Battery Charging Energy}} \times 100$
* **Why It Is Necessary**: Measures energy lost to heat and chemical resistance during charging and discharging (typically 75%–85% for lead-acid/tubular, 90%+ for lithium). A dropping RTE indicates battery cell aging.

### 4.3 Deep Discharge Stress & Minimum Voltage Tracking
* **Source Columns**: `Battery Voltage`, `Discharging Current`
* **Metrics**: Monthly minimum battery voltage, daily depth of discharge (DoD), and high-current discharge events ($> 40\text{A}$).
* **Why It Is Necessary**: In April 2025, voltage dropped as low as 23.1V under high load currents. For a 24V nominal bank, deep discharges under load cause sulfation (in lead-acid) or low-voltage cutoffs. Tracking this metric prevents premature battery death.

---

## 5. Load Profile & Electrical Characteristics

### 5.1 Peak Household Demand (Load Spikes)
* **Source Columns**: `Ac Output Active Power Total` (W), `Ac OutputLoad Total` (%)
* **Metrics**: Highest instantaneous peak load (W), highest % capacity load, time of day when peaks occur.
* **Why It Is Necessary**: Prevents inverter overload trips (`Fault 1`). Pinpoints what simultaneous appliance combinations (e.g., microwave + water pump + iron) threaten system stability.

### 5.2 Household Power Factor (PF) & Reactive Power Penalty
* **Source Columns**: `Ac Output Active Power Total` (W), `Ac Output Apparent Power Total` (VA)
* **Formula**: $\text{Power Factor} = \frac{\text{Active Power (W)}}{\text{Apparent Power (VA)}}$
* **Why It Is Necessary**: April data shows an average PF of ~0.72. Heavy reactive loads (inductive motors, old fans, cheap power supplies) draw excess current without performing real work, heating up inverter circuits and draining batteries faster.

---

## 6. System Health, Thermal Safety & Diagnostics

### 6.1 Inverter Operating Temperatures
* **Source Columns**: `Inner Temperature` (°C), `Max Temperature` (°C)
* **Metrics**: Maximum temperature reached, duration of operation above 50°C, correlation of temperature with high charging/load currents.
* **Why It Is Necessary**: Electronic components degrade exponentially at elevated temperatures. Knowing when heat sinks reach 60°C+ indicates if fans need servicing, dust filters need cleaning, or installation room ventilation must be improved before hot summer months.

### 6.2 Fault Log & Error Occurrences
* **Source Columns**: `Fault 1`
* **Why It Is Necessary**: Verifies uninterrupted operation without safety shutdowns or hardware protection trips.

---

## 7. Recommended Report Visualizations

1. **Daily Energy Stacked Bar Chart**: Solar Self-Consumed vs. Grid Imported vs. Battery Discharged for each day of the month.
2. **Average 24-Hour Diurnal Curve**: Mean hourly curves plotting Solar Generation, Home Load, and Battery Charge/Discharge on a single timeline.
3. **Outage Heatmap**: Calendar view showing the exact hours and days grid blackouts occurred.
4. **Battery Voltage vs. Load Scatter Plot**: Correlates load spikes with voltage drops to measure internal battery resistance.
