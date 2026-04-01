import streamlit as st
import pandas as pd
from pathlib import Path
import altair as alt

st.set_page_config(
    page_title="Agriculture Emissions Dashboard",
    layout="wide"
)

# -----------------------------
# Styling
# -----------------------------
st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
}
h1, h2, h3 {
    font-weight: 700;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Load data
# -----------------------------
base_dir = Path(__file__).resolve().parent.parent
data_dir = base_dir / "data"
out_dir = base_dir / "outputs"

scenario_summary = pd.read_csv(out_dir / "scenario_summary.csv")
farm_summary = pd.read_csv(out_dir / "farm_summary.csv")
emission_factors = pd.read_csv(data_dir / "emission_factors.csv")
farm_inputs = pd.read_csv(data_dir / "farm_inputs.csv")

# -----------------------------
# Sidebar controls
# -----------------------------
st.sidebar.header("Scenario Controls")

scenario = st.sidebar.selectbox(
    "Scenario",
    scenario_summary["scenario"].unique()
)

fertilizer_reduction = st.sidebar.slider(
    "Fertilizer reduction (%)",
    0, 50, 20
)

fertilizer_cost_per_tonne = st.sidebar.slider(
    "Fertilizer cost ($/tonne)",
    300, 1500, 800, 50
)

st.sidebar.caption(
    "Sensitivity assumption: fertilizer drives ~40% of upstream emissions in this simplified model."
)

show_raw = st.sidebar.checkbox("Show raw tables", value=False)

# -----------------------------
# Select scenario
# -----------------------------
selected = scenario_summary[scenario_summary["scenario"] == scenario].copy()

scope1 = float(selected["scope1_tco2e"].iloc[0])
base_scope2 = float(selected["scope2_tco2e"].iloc[0])
livestock = float(selected["livestock_tco2e"].iloc[0])
land = float(selected["land_use_change_tco2e"].iloc[0])

conv = float(selected["conventional_kgco2e_per_tonne"].iloc[0])
base_regen = float(selected["regenerative_kgco2e_per_tonne"].iloc[0])

# -----------------------------
# Sensitivity assumption
# -----------------------------
fertilizer_share = 0.4

scope2 = base_scope2 * (1 - fertilizer_share * (fertilizer_reduction / 100))
regen = base_regen * (1 - fertilizer_share * (fertilizer_reduction / 100))

reduction = (1 - regen / conv) * 100

# -----------------------------
# Cost model
# -----------------------------
total_fertilizer_kg = farm_inputs["n_fertilizer_kg"].sum()
total_fertilizer_tonnes = total_fertilizer_kg / 1000

reduced_fertilizer_tonnes = total_fertilizer_tonnes * (1 - fertilizer_reduction / 100)
fertilizer_tonnes_saved = total_fertilizer_tonnes - reduced_fertilizer_tonnes

base_fertilizer_cost = total_fertilizer_tonnes * fertilizer_cost_per_tonne
new_fertilizer_cost = reduced_fertilizer_tonnes * fertilizer_cost_per_tonne
fertilizer_cost_savings = base_fertilizer_cost - new_fertilizer_cost

scope2_reduction_tco2e = base_scope2 - scope2
regen_intensity_reduction = base_regen - regen

# -----------------------------
# Title
# -----------------------------
st.title("Agriculture Emissions Dashboard")

st.markdown("### Key takeaway")
st.markdown(f"**Regenerative system reduces emissions intensity by {reduction:.0f}%**")

st.info(
    "Sensitivity assumption: fertilizer contributes approximately 40% of upstream emissions in this model."
)

# -----------------------------
# KPI Row
# -----------------------------
c1, c2, c3, c4, c5 = st.columns(5)

c1.metric("Scope 1", f"{scope1:,.0f}")
c2.metric("Scope 2", f"{scope2:,.0f}", delta=f"{scope2 - base_scope2:+.0f} vs original")
c3.metric("Livestock", f"{livestock:,.0f}")
c4.metric("Land-use", f"{land:,.0f}")
c5.metric("Reduction", f"{reduction:.0f}%")

# -----------------------------
# Cost row
# -----------------------------
st.subheader("Cost Impact")

k1, k2, k3, k4 = st.columns(4)

k1.metric("Base Fertilizer Cost", f"${base_fertilizer_cost:,.0f}")
k2.metric("Adjusted Fertilizer Cost", f"${new_fertilizer_cost:,.0f}")
k3.metric("Estimated Savings", f"${fertilizer_cost_savings:,.0f}")
k4.metric("Fertilizer Saved", f"{fertilizer_tonnes_saved:,.2f} t")

# -----------------------------
# Charts row
# -----------------------------
left, right = st.columns(2)

with left:
    st.subheader("Emissions by Scenario")

    chart_df = scenario_summary.copy()
    chart_df.loc[chart_df["scenario"] == scenario, "scope2_tco2e"] = scope2

    melted = chart_df.melt(
        id_vars="scenario",
        value_vars=["scope1_tco2e", "scope2_tco2e"],
        var_name="scope",
        value_name="emissions"
    )

    chart = alt.Chart(melted).mark_bar().encode(
        x=alt.X("scenario:N", title=None),
        y=alt.Y("emissions:Q", title="tCO2e"),
        color=alt.Color(
            "scope:N",
            scale=alt.Scale(
                domain=["scope2_tco2e", "scope1_tco2e"],
                range=["#1f77b4", "#aec7e8"]
            ),
            legend=None
        ),
        tooltip=["scenario", "scope", "emissions"]
    ).properties(height=350)

    st.altair_chart(chart, use_container_width=True)

with right:
    st.subheader("Intensity Comparison")

    comp = pd.DataFrame({
        "system": ["Conventional", "Regenerative"],
        "value": [conv, regen]
    })

    chart2 = alt.Chart(comp).mark_bar(size=80).encode(
        x=alt.X("system:N", title=None),
        y=alt.Y("value:Q", title="kgCO2e/t"),
        color=alt.Color(
            "system:N",
            scale=alt.Scale(
                domain=["Conventional", "Regenerative"],
                range=["#d62728", "#2ca02c"]
            ),
            legend=None
        ),
        tooltip=["system", "value"]
    ).properties(height=350)

    st.altair_chart(chart2, use_container_width=True)

# -----------------------------
# Cost vs emissions tradeoff
# -----------------------------
st.subheader("Cost and Emissions Tradeoff")

tradeoff_df = pd.DataFrame({
    "Metric": ["Scope 2 Reduction (tCO2e)", "Fertilizer Cost Savings ($)"],
    "Value": [scope2_reduction_tco2e, fertilizer_cost_savings]
})

chart_tradeoff = alt.Chart(tradeoff_df).mark_bar(size=80).encode(
    x=alt.X("Metric:N", title=None),
    y=alt.Y("Value:Q", title="Value"),
    color=alt.Color(
        "Metric:N",
        scale=alt.Scale(
            range=["#4c78a8", "#2ca02c"]
        ),
        legend=None
    ),
    tooltip=["Metric", "Value"]
).properties(height=350)

st.altair_chart(chart_tradeoff, use_container_width=True)

# -----------------------------
# Breakdown
# -----------------------------
st.subheader("Emissions Breakdown")

breakdown = pd.DataFrame({
    "category": ["Scope 2", "Scope 1", "Livestock", "Land Use"],
    "value": [scope2, scope1, livestock, land]
})

chart3 = alt.Chart(breakdown).mark_bar(size=60).encode(
    x=alt.X("category:N", sort=["Scope 2", "Scope 1", "Livestock", "Land Use"]),
    y=alt.Y("value:Q", title="tCO2e"),
    color=alt.condition(
        alt.datum.value < 0,
        alt.value("#2ca02c"),
        alt.value("#4c78a8")
    ),
    tooltip=["category", "value"]
).properties(height=350)

st.altair_chart(chart3, use_container_width=True)

# -----------------------------
# Interpretation
# -----------------------------
st.markdown("---")
st.subheader("Interpretation")

st.write(f"""
- Scope 2 dominates total emissions across all scenarios  
- Regenerative system reduces intensity from {conv:.0f} → {regen:.0f} kgCO2e/t  
- Total modeled reduction: {reduction:.0f}%  
- Current fertilizer reduction sensitivity: {fertilizer_reduction}%  
- Estimated Scope 2 reduction: {scope2_reduction_tco2e:,.1f} tCO2e  
- Estimated fertilizer savings: ${fertilizer_cost_savings:,.0f}
""")

st.write("Primary driver: input-related emissions (fertilizer + upstream supply chain)")

# -----------------------------
# Decision layer
# -----------------------------
st.subheader("Decision Implications")

st.write(f"""
- Largest lever: fertilizer reduction  
- Supplier practices outweigh operational efficiency  
- Scenario modeling is required before scaling interventions  
- Under current assumptions, a {fertilizer_reduction}% fertilizer reduction saves approximately ${fertilizer_cost_savings:,.0f}
  while reducing Scope 2 by {scope2_reduction_tco2e:,.1f} tCO2e

Use case:
- ESG reporting  
- supplier transition strategy  
- emissions benchmarking  
- cost and emissions tradeoff analysis
""")

# -----------------------------
# Credibility
# -----------------------------
st.subheader("Model Credibility")

if "confidence_level" in emission_factors.columns:
    conf = emission_factors["confidence_level"].value_counts().reset_index()
    conf.columns = ["level", "count"]

    chart4 = alt.Chart(conf).mark_bar().encode(
        x="level:N",
        y="count:Q",
        color=alt.Color(
            "level:N",
            scale=alt.Scale(
                domain=["High", "Medium", "Low"],
                range=["#2ca02c", "#ff7f0e", "#d62728"]
            )
        )
    ).properties(height=300)

    st.altair_chart(chart4, use_container_width=True)

st.caption("Simplified model using EPA, eGRID, and IPCC-style factors.")

# -----------------------------
# Raw data
# -----------------------------
if show_raw:
    st.markdown("---")
    st.subheader("Raw Data")

    st.dataframe(scenario_summary, use_container_width=True)
    st.dataframe(farm_summary, use_container_width=True)
    st.dataframe(emission_factors, use_container_width=True)
    st.dataframe(farm_inputs, use_container_width=True)