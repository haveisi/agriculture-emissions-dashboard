from __future__ import annotations

from pathlib import Path
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"


def load_factor_map(path: Path) -> dict[str, float]:
    df = pd.read_csv(path)
    return dict(zip(df["source_key"], df["ef_kgco2e_per_unit"]))


def calc_stationary_scope1(facilities: pd.DataFrame, ef_map: dict[str, float]) -> pd.DataFrame:
    df = facilities.copy()
    df["ef_kgco2e_per_unit"] = df["fuel_type"].map(ef_map)
    missing = df[df["ef_kgco2e_per_unit"].isna()]
    if not missing.empty:
        raise ValueError(
            f"Missing emission factors for facility fuels: {missing['fuel_type'].unique().tolist()}"
        )
    df["kgco2e"] = df["activity_value"] * df["ef_kgco2e_per_unit"]
    df["emission_source"] = "stationary_scope1"
    return df


def calc_fleet_scope1(fleet: pd.DataFrame, ef_map: dict[str, float]) -> pd.DataFrame:
    df = fleet.copy()
    df["ef_kgco2e_per_unit"] = df["fuel_type"].map(ef_map)
    missing = df[df["ef_kgco2e_per_unit"].isna()]
    if not missing.empty:
        raise ValueError(
            f"Missing emission factors for fleet fuels: {missing['fuel_type'].unique().tolist()}"
        )
    df["kgco2e"] = df["activity_value"] * df["ef_kgco2e_per_unit"]
    df["emission_source"] = "fleet_scope1"
    return df


def calc_farm_emissions(fields: pd.DataFrame, inputs: pd.DataFrame, ef_map: dict[str, float]) -> pd.DataFrame:
    df = fields.merge(inputs, on="field_id", how="inner")

    df["diesel_kgco2e"] = df["diesel_liters"] * ef_map["diesel_liters"]
    df["fertilizer_prod_kgco2e"] = df["n_fertilizer_kg"] * ef_map["n_fertilizer_kg"]
    df["herbicide_kgco2e"] = df["herbicide_kg"] * ef_map["herbicide_kg"]
    df["lime_kgco2e"] = df["lime_kg"] * ef_map["lime_kg"]
    df["compost_kgco2e"] = df["compost_kg"] * ef_map["compost_kg"]
    df["seed_kgco2e"] = df["seed_kg"] * ef_map["seed_kg"]
    df["transport_input_kgco2e"] = df["transport_input_tkm"] * ef_map["transport_input_tkm"]
    df["soil_n2o_kgco2e"] = df["n_fertilizer_kg"] * ef_map["soil_n2o_from_n_input"]

    component_cols = [
        "diesel_kgco2e",
        "fertilizer_prod_kgco2e",
        "herbicide_kgco2e",
        "lime_kgco2e",
        "compost_kgco2e",
        "seed_kgco2e",
        "transport_input_kgco2e",
        "soil_n2o_kgco2e",
    ]

    df["gross_farm_kgco2e"] = df[component_cols].sum(axis=1)
    df["soc_change_kgco2e_memo"] = df["estimated_soc_change_tco2e"] * 1000.0
    df["kgco2e_per_tonne_crop"] = df["gross_farm_kgco2e"] / df["yield_tonnes"]

    return df


def summarize_operational_scope1(stationary_df: pd.DataFrame, fleet_df: pd.DataFrame) -> pd.DataFrame:
    total_stationary = stationary_df["kgco2e"].sum()
    total_fleet = fleet_df["kgco2e"].sum()
    total_gross_scope1 = total_stationary + total_fleet

    summary = pd.DataFrame({
        "metric": [
            "stationary_scope1_tco2e",
            "fleet_scope1_tco2e",
            "gross_global_scope1_tco2e",
        ],
        "value": [
            total_stationary / 1000,
            total_fleet / 1000,
            total_gross_scope1 / 1000,
        ],
    })
    return summary


def summarize_farm_comparison(farm_df: pd.DataFrame) -> pd.DataFrame:
    grouped = (
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
    grouped["gross_farm_tco2e"] = grouped["gross_farm_kgco2e"] / 1000
    grouped["gross_kgco2e_per_tonne"] = grouped["gross_farm_kgco2e"] / grouped["yield_tonnes"]
    grouped["memo_net_tco2e_after_soc"] = (
        grouped["gross_farm_kgco2e"] + grouped["soc_change_kgco2e_memo"]
    ) / 1000
    return grouped


def main() -> None:
    facilities = pd.read_csv(DATA_DIR / "facilities.csv")
    fleet = pd.read_csv(DATA_DIR / "fleet_fuel.csv")
    farm_fields = pd.read_csv(DATA_DIR / "farm_fields.csv")
    farm_inputs = pd.read_csv(DATA_DIR / "farm_inputs.csv")
    ef_map = load_factor_map(DATA_DIR / "emission_factors.csv")

    stationary_df = calc_stationary_scope1(facilities, ef_map)
    fleet_df = calc_fleet_scope1(fleet, ef_map)
    farm_df = calc_farm_emissions(farm_fields, farm_inputs, ef_map)

    scope1_summary = summarize_operational_scope1(stationary_df, fleet_df)
    farm_summary = summarize_farm_comparison(farm_df)

    out_dir = BASE_DIR / "outputs"
    out_dir.mkdir(exist_ok=True)

    stationary_df.to_csv(out_dir / "stationary_scope1_detail.csv", index=False)
    fleet_df.to_csv(out_dir / "fleet_scope1_detail.csv", index=False)
    farm_df.to_csv(out_dir / "farm_emissions_detail.csv", index=False)
    scope1_summary.to_csv(out_dir / "scope1_summary.csv", index=False)
    farm_summary.to_csv(out_dir / "farm_summary.csv", index=False)
    print("\n=== INTERPRETATION ===")
    print("Facility and fleet fuel dominate corporate gross Scope 1 in this example.")
    print("The farm comparison suggests lower gross emissions intensity in the regenerative system,")
    print("but results depend heavily on placeholder emission factors and simplified assumptions.")
    print("Memo soil carbon values are reported separately and are not netted against gross Scope 1.")
    print("\n=== GROSS OPERATIONAL SCOPE 1 SUMMARY ===")
    print(scope1_summary.to_string(index=False))

    print("\n=== FARM / SUPPLIER COMPARISON (MEMO ANALYSIS) ===")
    print(farm_summary.to_string(index=False))

    print(f"\nFiles written to: {out_dir}")


if __name__ == "__main__":
    main()