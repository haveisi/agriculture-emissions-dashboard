from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt


def load_csv(data_dir: Path, filename: str) -> pd.DataFrame:
    df = pd.read_csv(data_dir / filename)
    df.columns = df.columns.str.strip()
    return df


def load_factor_map(emission_factors: pd.DataFrame) -> dict:
    return dict(zip(emission_factors["source_key"], emission_factors["ef_kgco2e_per_unit"]))


def calc_stationary_scope1(facilities: pd.DataFrame, ef_map: dict) -> pd.DataFrame:
    df = facilities.copy()
    df["ef_kgco2e_per_unit"] = df["fuel_type"].map(ef_map)

    missing = df[df["ef_kgco2e_per_unit"].isna()]
    if not missing.empty:
        raise ValueError(f"Missing stationary factors for: {missing['fuel_type'].unique().tolist()}")

    df["kgco2e"] = df["activity_value"] * df["ef_kgco2e_per_unit"]
    df["emission_source"] = "stationary_scope1"
    return df


def calc_fleet_scope1(fleet: pd.DataFrame, ef_map: dict) -> pd.DataFrame:
    df = fleet.copy()
    df["ef_kgco2e_per_unit"] = df["fuel_type"].map(ef_map)

    missing = df[df["ef_kgco2e_per_unit"].isna()]
    if not missing.empty:
        raise ValueError(f"Missing fleet factors for: {missing['fuel_type'].unique().tolist()}")

    df["kgco2e"] = df["activity_value"] * df["ef_kgco2e_per_unit"]
    df["emission_source"] = "fleet_scope1"
    return df


def calc_scope2_electricity(electricity: pd.DataFrame, ef_map: dict) -> pd.DataFrame:
    df = electricity.copy()
    df["source_key"] = "egrid_" + df["subregion"]
    df["ef_kgco2e_per_unit"] = df["source_key"].map(ef_map)

    missing = df[df["ef_kgco2e_per_unit"].isna()]
    if not missing.empty:
        raise ValueError(f"Missing electricity factors for: {missing['subregion'].unique().tolist()}")

    df["kgco2e"] = df["electricity_mwh"] * df["ef_kgco2e_per_unit"]
    df["emission_source"] = "scope2_electricity"
    return df


def calc_farm_emissions(farm_fields: pd.DataFrame, ef_map: dict) -> pd.DataFrame:
    df = farm_fields.copy()

    required_cols = [
        "field_id", "farm_id", "system_type", "crop", "area_ha", "yield_tonnes",
        "diesel_liters", "n_fertilizer_kg", "herbicide_kg", "lime_kg",
        "compost_kg", "seed_kg", "transport_input_tkm", "estimated_soc_change_tco2e"
    ]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing farm input columns: {missing_cols}")

    df["diesel_kgco2e"] = df["diesel_liters"] * ef_map.get("diesel_liters", 0)
    df["fertilizer_prod_kgco2e"] = df["n_fertilizer_kg"] * ef_map.get("n_fertilizer_kg", 0)
    df["herbicide_kgco2e"] = df["herbicide_kg"] * ef_map.get("herbicide_kg", 0)
    df["lime_kgco2e"] = df["lime_kg"] * ef_map.get("lime_kg", 0)
    df["compost_kgco2e"] = df["compost_kg"] * ef_map.get("compost_kg", 0)
    df["seed_kgco2e"] = df["seed_kg"] * ef_map.get("seed_kg", 0)
    df["transport_input_kgco2e"] = df["transport_input_tkm"] * ef_map.get("transport_input_tkm", 0)
    df["soil_n2o_kgco2e"] = df["n_fertilizer_kg"] * ef_map.get("soil_n2o_from_n_input", 0)

    df["gross_farm_kgco2e"] = (
        df["diesel_kgco2e"]
        + df["fertilizer_prod_kgco2e"]
        + df["herbicide_kgco2e"]
        + df["lime_kgco2e"]
        + df["compost_kgco2e"]
        + df["seed_kgco2e"]
        + df["transport_input_kgco2e"]
        + df["soil_n2o_kgco2e"]
    )

    df["soc_change_kgco2e_memo"] = df["estimated_soc_change_tco2e"] * 1000
    df["gross_farm_tco2e"] = df["gross_farm_kgco2e"] / 1000
    df["kgco2e_per_tonne_crop"] = df["gross_farm_kgco2e"] / df["yield_tonnes"]

    return df


def summarize_farm(farm_df: pd.DataFrame) -> pd.DataFrame:
    summary = (
        farm_df.groupby("system_type", dropna=False)
        .agg(
            fields=("field_id", "count"),
            area_ha=("area_ha", "sum"),
            yield_tonnes=("yield_tonnes", "sum"),
            gross_farm_kgco2e=("gross_farm_kgco2e", "sum"),
            soc_change_kgco2e_memo=("soc_change_kgco2e_memo", "sum"),
        )
        .reset_index()
    )

    summary["gross_farm_tco2e"] = summary["gross_farm_kgco2e"] / 1000
    summary["gross_kgco2e_per_tonne"] = summary["gross_farm_kgco2e"] / summary["yield_tonnes"]
    summary["memo_net_tco2e_after_soc"] = (
        summary["gross_farm_kgco2e"] + summary["soc_change_kgco2e_memo"]
    ) / 1000

    return summary


def calc_livestock_emissions(livestock: pd.DataFrame, ef_map: dict) -> pd.DataFrame:
    df = livestock.copy()

    if df.empty:
        return df

    df["enteric_key"] = "enteric_" + df["animal_type"]
    df["manure_key"] = "manure_" + df["manure_system"]

    df["enteric_kgco2e_per_head"] = df["enteric_key"].map(ef_map)
    df["manure_kgco2e_per_head"] = df["manure_key"].map(ef_map)

    missing_enteric = df[df["enteric_kgco2e_per_head"].isna()]
    if not missing_enteric.empty:
        raise ValueError(f"Missing enteric factors for: {missing_enteric['animal_type'].unique().tolist()}")

    missing_manure = df[df["manure_kgco2e_per_head"].isna()]
    if not missing_manure.empty:
        raise ValueError(f"Missing manure factors for: {missing_manure['manure_system'].unique().tolist()}")

    df["enteric_kgco2e"] = df["headcount"] * df["enteric_kgco2e_per_head"]
    df["manure_kgco2e"] = df["headcount"] * df["manure_kgco2e_per_head"]
    df["gross_livestock_kgco2e"] = df["enteric_kgco2e"] + df["manure_kgco2e"]

    return df


def calc_land_use_change(luc: pd.DataFrame) -> pd.DataFrame:
    df = luc.copy()

    if df.empty:
        return df

    df["land_use_change_kgco2e"] = df["area_ha"] * df["kgco2e_per_ha"]
    return df


def apply_scenario(
    farm_fields: pd.DataFrame,
    fleet: pd.DataFrame,
    scenario: str
) -> tuple[pd.DataFrame, pd.DataFrame]:
    farm_fields_s = farm_fields.copy()
    fleet_s = fleet.copy()

    numeric_cols = [
        "diesel_liters",
        "n_fertilizer_kg",
        "herbicide_kg",
        "lime_kg",
        "compost_kg",
        "seed_kg",
        "transport_input_tkm",
        "estimated_soc_change_tco2e",
        "activity_value",
    ]

    for col in numeric_cols:
        if col in farm_fields_s.columns:
            farm_fields_s[col] = farm_fields_s[col].astype(float)
        if col in fleet_s.columns:
            fleet_s[col] = fleet_s[col].astype(float)

    if scenario == "baseline":
        return farm_fields_s, fleet_s

    if scenario == "fertilizer_reduction_20":
        farm_fields_s["n_fertilizer_kg"] *= 0.8

    elif scenario == "regenerative_boost":
        regen_mask = farm_fields_s["system_type"] == "regenerative"
        farm_fields_s.loc[regen_mask, "n_fertilizer_kg"] *= 0.5
        farm_fields_s.loc[regen_mask, "herbicide_kg"] *= 0.3
        farm_fields_s.loc[regen_mask, "estimated_soc_change_tco2e"] *= 1.5

    elif scenario == "renewable_diesel_shift":
        diesel_mask = fleet_s["fuel_type"] == "diesel_mobile"

        converted_rows = fleet_s[diesel_mask].copy()
        converted_rows["activity_value"] = converted_rows["activity_value"] * 0.5
        converted_rows["fuel_type"] = "renewable_diesel"

        fleet_s.loc[diesel_mask, "activity_value"] *= 0.5
        fleet_s = pd.concat([fleet_s, converted_rows], ignore_index=True)

    else:
        raise ValueError(f"Unknown scenario: {scenario}")

    return farm_fields_s, fleet_s

def make_charts(
    scope1_total_tco2e: float,
    scope2_total_tco2e: float,
    farm_summary: pd.DataFrame,
    out_dir: Path
) -> None:
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(exist_ok=True)

    plt.figure()
    plt.bar(["Scope 1", "Scope 2"], [scope1_total_tco2e, scope2_total_tco2e])
    plt.title("Operational Emissions Breakdown")
    plt.ylabel("tCO2e")
    plt.tight_layout()
    plt.savefig(fig_dir / "operational_emissions_breakdown.png")
    plt.close()

    plt.figure()
    plt.bar(farm_summary["system_type"], farm_summary["gross_kgco2e_per_tonne"])
    plt.title("Farm Emissions Intensity")
    plt.ylabel("kgCO2e per tonne")
    plt.tight_layout()
    plt.savefig(fig_dir / "farm_intensity.png")
    plt.close()


def main() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    out_dir = base_dir / "outputs"
    out_dir.mkdir(exist_ok=True)

    emission_factors = load_csv(data_dir, "emission_factors.csv")
    facilities = load_csv(data_dir, "facilities.csv")
    fleet = load_csv(data_dir, "fleet_fuel.csv")

    farm_fields = load_csv(data_dir, "farm_fields.csv")
    farm_inputs = load_csv(data_dir, "farm_inputs.csv")
    farm_fields = farm_fields.merge(farm_inputs, on="field_id", how="left")
    print("Farm fields columns after merge:", farm_fields.columns.tolist())

    electricity = load_csv(data_dir, "electricity_use.csv")
    livestock = load_csv(data_dir, "livestock.csv")
    land_use_change = load_csv(data_dir, "land_use_change.csv")

    ef_map = load_factor_map(emission_factors)

    scenarios = [
        "baseline",
        "fertilizer_reduction_20",
        "regenerative_boost",
        "renewable_diesel_shift",
    ]

    scenario_results = []

    for scenario in scenarios:
        farm_fields_s, fleet_s = apply_scenario(farm_fields, fleet, scenario)

        stationary_df = calc_stationary_scope1(facilities, ef_map)
        fleet_df = calc_fleet_scope1(fleet_s, ef_map)
        scope2_df = calc_scope2_electricity(electricity, ef_map)
        farm_df = calc_farm_emissions(farm_fields_s, ef_map)
        livestock_df = calc_livestock_emissions(livestock, ef_map)
        luc_df = calc_land_use_change(land_use_change)

        scope1_total_tco2e = (stationary_df["kgco2e"].sum() + fleet_df["kgco2e"].sum()) / 1000
        scope2_total_tco2e = scope2_df["kgco2e"].sum() / 1000
        livestock_total_tco2e = (
            livestock_df["gross_livestock_kgco2e"].sum() / 1000 if not livestock_df.empty else 0
        )
        luc_total_tco2e = (
            luc_df["land_use_change_kgco2e"].sum() / 1000 if not luc_df.empty else 0
        )

        farm_summary = summarize_farm(farm_df)

        print(f"\n=== {scenario.upper()} ===")
        print(f"Scope 1: {scope1_total_tco2e:.2f} tCO2e")
        print(f"Scope 2: {scope2_total_tco2e:.2f} tCO2e")
        print(f"Livestock: {livestock_total_tco2e:.2f} tCO2e")
        print(f"Land-use change: {luc_total_tco2e:.2f} tCO2e")
        print(farm_summary.to_string(index=False))

        scenario_results.append({
            "scenario": scenario,
            "scope1_tco2e": scope1_total_tco2e,
            "scope2_tco2e": scope2_total_tco2e,
            "livestock_tco2e": livestock_total_tco2e,
            "land_use_change_tco2e": luc_total_tco2e,
            "conventional_kgco2e_per_tonne": float(
                farm_summary.loc[farm_summary["system_type"] == "conventional", "gross_kgco2e_per_tonne"].iloc[0]
            ) if "conventional" in farm_summary["system_type"].values else None,
            "regenerative_kgco2e_per_tonne": float(
                farm_summary.loc[farm_summary["system_type"] == "regenerative", "gross_kgco2e_per_tonne"].iloc[0]
            ) if "regenerative" in farm_summary["system_type"].values else None,
        })

        if scenario == "baseline":
            stationary_df.to_csv(out_dir / "stationary_scope1_detail.csv", index=False)
            fleet_df.to_csv(out_dir / "fleet_scope1_detail.csv", index=False)
            scope2_df.to_csv(out_dir / "scope2_electricity_detail.csv", index=False)
            farm_df.to_csv(out_dir / "farm_emissions_detail.csv", index=False)
            farm_summary.to_csv(out_dir / "farm_summary.csv", index=False)

            make_charts(scope1_total_tco2e, scope2_total_tco2e, farm_summary, out_dir)

    pd.DataFrame(scenario_results).to_csv(out_dir / "scenario_summary.csv", index=False)

    print("\n=== DONE ===")


if __name__ == "__main__":
    main()