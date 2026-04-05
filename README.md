# GHG Accounting Model for Regenerative Agriculture Supply Chains

# Agriculture Emissions Dashboard

Interactive Streamlit dashboard for analyzing agricultural emissions, fertilizer sensitivity, and cost-emissions tradeoffs.
## Live Demo
[Open the dashboard] (https://agriculture-emissions-dashboard-gxcwsmcncuoyhvjwlmcx3a.streamlit.app/)

## Features
- Emissions breakdown by scope
- Fertilizer reduction sensitivity analysis
- Cost vs emissions tradeoff modeling

  ## Overview

This project implements a Python-based greenhouse gas (GHG) accounting model for agricultural operations and supply chains.

It demonstrates how to estimate:

* Scope 1 emissions (stationary + fleet fuel)
* Scope 2 emissions (purchased electricity)
* Farm-level emissions from inputs and operations
* Emissions intensity (kgCO2e per tonne)
* Scenario-based comparisons (e.g., fertilizer reduction, regenerative practices)

The model is designed to reflect real-world ESG and sustainability analytics workflows while remaining transparent and easy to follow.

---

## Why this matters

Agriculture is a major contributor to global emissions due to:

* Fuel combustion
* Fertilizer production and soil emissions (N₂O)
* Input manufacturing and transport
* Land management practices

There is increasing interest in **regenerative agriculture** as a way to reduce emissions intensity and improve soil carbon outcomes.

This project explores how different practices impact emissions and efficiency.

---

## Model Structure

### 1. Scope 1 (Operational)

* Stationary combustion (facilities)
* Mobile combustion (fleet fuel)

### 2. Scope 2 (Electricity)

* Purchased electricity emissions
* Location-based approach using grid emission factors

### 3. Farm-Level Emissions

Includes:

* Diesel use
* Nitrogen fertilizer (production + soil N₂O)
* Agricultural inputs (herbicides, lime, etc.)
* Yield-based intensity calculation

### 4. Scenario Analysis

The model evaluates multiple scenarios:

* Baseline
* Fertilizer reduction (−20%)
* Regenerative boost (lower inputs + higher soil carbon)

---

## Example Results

### Operational Emissions

* Scope 1: ~423 tCO2e
* Scope 2: ~1350 tCO2e

### Farm Emissions Intensity

| System       | kgCO2e / tonne |
| ------------ | -------------- |
| Conventional | ~200           |
| Regenerative | ~70            |

Under regenerative scenarios, emissions intensity decreases significantly due to reduced fertilizer use and improved soil carbon outcomes.

---

## Visualization

### Farm Emissions Intensity

![Farm Intensity](outputs/figures/farm_intensity.png)

---

## Interpretation

The model shows a clear reduction in emissions intensity under regenerative farming systems.

* Conventional systems rely heavily on fertilizer inputs, driving higher emissions.
* Regenerative systems reduce input use and improve soil carbon performance.

However:

* Results depend heavily on assumptions and emission factors
* Soil carbon is treated as a **memo item** and not netted against Scope 1
* This is a simplified model, not a full GHG inventory

---

## How to Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the model:

```bash
python src/ghg_accounting.py
```

Outputs:

* Scenario results → `outputs/scenario_summary.csv`
* Charts → `outputs/figures/`

---

## Project Structure

```
ghg_regen/
├── data/
│   ├── emission_factors.csv
│   ├── facilities.csv
│   ├── fleet_fuel.csv
│   ├── farm_fields.csv
│   ├── farm_inputs.csv
│   ├── electricity_use.csv
│   ├── livestock.csv
│   ├── land_use_change.csv
│
├── outputs/
│   ├── scenario_summary.csv
│   └── figures/
│       └── farm_intensity.png
│
├── src/
│   └── ghg_accounting.py
│
├── README.md
├── requirements.txt
├── .gitignore
```

---

## Data Notes

* Emission factors are a mix of:

  * EPA-style combustion factors (illustrative)
  * IPCC-style agricultural proxies (simplified)
* Values are not fully validated and are intended for demonstration purposes

---

## Limitations

* Not a complete GHG Protocol-compliant inventory
* Scope 3 emissions are not included
* Livestock and land-use change are simplified
* No uncertainty or sensitivity analysis

---

## Author

Developed as part of a portfolio demonstrating:

* ESG analytics
* sustainability modeling
* applied Python for environmental data
