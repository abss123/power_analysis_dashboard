"""Streamlit UI for the MDE calculator. All statistics live in power_calc.py."""

import csv
import io
from pathlib import Path

import streamlit as st

import power_calc as pc

HERE = Path(__file__).parent
TYPES = ["Continuous", "Binary"]
DEFAULT_MEAN = {"Continuous": 4.3, "Binary": 0.30}
DEFAULT_SD = 1.5
# Q3 defaults to a binary (behavioural) outcome so both types are visible out of the box.
DEFAULT_TYPE_BY_QUESTION = {3: "Binary"}

st.set_page_config(page_title="MDE calculator", layout="wide")
st.title("Minimum detectable effect calculator")

with st.expander("How to read this"):
    st.markdown(
        "The **minimum detectable effect (MDE)** is the smallest true difference between groups "
        "that this experiment would reliably pick up (with the chosen power and significance). "
        "Your budget sets how many people we can pay; they are split evenly into groups, and "
        "smaller groups mean larger MDEs. Each MDE is shown in the outcome's own units, in "
        "standard deviations, and as a share of the average; if the effect you expect is smaller "
        "than the MDE, the experiment is likely to miss it. "
        "See `METHODOLOGY.md` for the formulas and assumptions."
    )
with st.expander("Show the code behind the numbers (power_calc.py)"):
    st.code((HERE / "power_calc.py").read_text(), language="python")

# ---------------------------------------------------------------- budget
st.header("Budget")
budget_cols = st.columns(3)
budget = budget_cols[0].number_input("Budget ($)", min_value=0.0, value=800.0, step=50.0)
rate_per_hour = budget_cols[1].number_input(
    "Rate per person per hour ($)", min_value=0.01, value=15.0, step=1.0
)
minutes_per_person = budget_cols[2].number_input(
    "Duration per person (minutes, incl. questionnaire and game)",
    min_value=1.0, value=30.0, step=5.0,
)

cost_each = pc.cost_per_person(rate_per_hour, minutes_per_person)
n_total = pc.participants_affordable(budget, rate_per_hour, minutes_per_person)

result_cols = st.columns(3)
result_cols[0].metric("Participants we can afford", n_total)
result_cols[1].metric("Cost per person", f"${cost_each:,.2f}")
result_cols[2].metric("Total spend", f"${n_total * cost_each:,.2f}")

if n_total < 4:
    st.warning("The budget must cover at least 4 people (one per group in the 4-way design).")
    st.stop()

two_way_groups = pc.split_into_groups(n_total, 2)
four_way_groups = pc.split_into_groups(n_total, 4)


# ---------------------------------------------------------------- helpers
def reset_mean(prefix, q):
    """When a question's type changes, reset its average to a sensible default."""
    st.session_state[f"{prefix}_q{q}_mean"] = DEFAULT_MEAN[st.session_state[f"{prefix}_q{q}_type"]]


def format_mde(mde, sd, mean, outcome_type):
    """e.g. '0.82 pts (0.54 SD, 19% of mean)' or '25 pp (0.54 SD, 83% of mean)'."""
    raw = f"{mde * 100:.0f} pp" if outcome_type == "Binary" else f"{mde:.2f} pts"
    share = pc.share_of_mean(mde, mean)
    share_text = f", {share:.0%} of mean" if share is not None else ""
    return f"{raw} ({pc.in_sd_units(mde, sd):.2f} SD{share_text})"


def design_settings(prefix):
    """Significance, power and number of questions for one design."""
    significance = st.number_input(
        "Significance (confidence level, %)", 50.0, 99.9, 95.0, 0.5, key=f"{prefix}_sig"
    ) / 100
    power = st.number_input("Power (%)", 50.0, 99.9, 80.0, 0.5, key=f"{prefix}_power") / 100
    n_questions = st.number_input(
        "Number of questions (attitudinal + behavioral)", 1, 10, 3, 1, key=f"{prefix}_nq"
    )
    return significance, power, int(n_questions)


def question_inputs(prefix, q, copy_from=None):
    """Render type / average / SD widgets for question q. Returns (type, mean, sd) or None if invalid.

    If copy_from is given (a (type, mean, sd) tuple), the widgets are filled from it and locked.
    """
    type_key, mean_key, sd_key = (f"{prefix}_q{q}_{field}" for field in ("type", "mean", "sd"))
    if copy_from is not None:
        st.session_state[type_key], st.session_state[mean_key], st.session_state[sd_key] = copy_from
    st.session_state.setdefault(type_key, DEFAULT_TYPE_BY_QUESTION.get(q, "Continuous"))
    st.session_state.setdefault(mean_key, DEFAULT_MEAN[st.session_state[type_key]])
    st.session_state.setdefault(sd_key, DEFAULT_SD)

    locked = copy_from is not None
    outcome_type = st.selectbox(
        "Type", TYPES, key=type_key, disabled=locked, on_change=reset_mean, args=(prefix, q)
    )
    is_binary = outcome_type == "Binary"
    mean = st.number_input(
        "Estimated rate (0 to 1)" if is_binary else "Estimated average",
        key=mean_key, step=0.05 if is_binary else 0.1, format="%.2f", disabled=locked,
    )
    if is_binary and 0 < mean < 1:
        st.session_state[sd_key] = pc.sd_for_binary(mean)
    sd = st.number_input(
        "Estimated standard deviation" + (" (from the rate)" if is_binary else ""),
        key=sd_key, step=0.1, format="%.3f", disabled=is_binary or locked,
    )

    if is_binary and not 0 < mean < 1:
        st.warning("For a binary question the rate must be strictly between 0 and 1.")
        return None
    if sd <= 0:
        st.warning("The standard deviation must be greater than 0.")
        return None
    return outcome_type, mean, sd


def summary_row(design, q, inputs, comparison, mde, groups):
    outcome_type, mean, sd = inputs
    share = pc.share_of_mean(mde, mean)
    return {
        "Design": design, "Question": f"Q{q}", "Type": outcome_type,
        "Average": round(mean, 4), "SD": round(sd, 4), "Comparison": comparison,
        "MDE (raw units)": round(mde, 4), "MDE (SD units)": round(pc.in_sd_units(mde, sd), 4),
        "MDE (% of mean)": round(share * 100, 1) if share is not None else None,
        "Group sizes": groups,
    }


# ---------------------------------------------------------------- designs
summary = []
two_way_inputs = {}
left, right = st.columns(2, gap="large")

with left:
    st.header("2-way experiment")
    st.caption("Control vs one variant")
    significance, power, n_questions = design_settings("two")
    n_control, n_variant = two_way_groups
    groups_text = f"{n_control} / {n_variant}"
    for q in range(1, n_questions + 1):
        with st.container(border=True):
            st.subheader(f"Q{q}")
            inputs = question_inputs("two", q)
            two_way_inputs[q] = inputs
            if inputs is None:
                continue
            outcome_type, mean, sd = inputs
            mde = pc.mde_two_way(sd, n_control, n_variant, significance, power)
            st.markdown(f"**Minimum detectable effect:** {format_mde(mde, sd, mean, outcome_type)}")
            st.markdown(f"**Group sizes (Control / Variant):** {groups_text}")
            summary.append(summary_row("2-way", q, inputs, "Control vs variant", mde, groups_text))

with right:
    st.header("4-way experiment")
    st.caption("2x2: control, variant 1, variant 2, variant 3 (= both treatments)")
    mirror = st.checkbox("Use same question inputs as the 2-way experiment", value=True)
    significance, power, n_questions = design_settings("four")
    n_c, n_v1, n_v2, n_v3 = four_way_groups
    n_smallest_variant = min(n_v1, n_v2, n_v3)
    groups_text = f"{n_c} / {n_v1} / {n_v2} / {n_v3}"
    for q in range(1, n_questions + 1):
        with st.container(border=True):
            st.subheader(f"Q{q}")
            copy_from = two_way_inputs.get(q) if mirror else None
            if mirror and q in two_way_inputs and copy_from is None:
                st.warning("The matching 2-way question has invalid inputs; fix it there.")
                continue
            inputs = question_inputs("four", q, copy_from)
            if inputs is None:
                continue
            outcome_type, mean, sd = inputs
            comparisons = [
                ("Main effect", pc.mde_main_effect(sd, n_c, n_v1, n_v2, n_v3, significance, power)),
                ("Single variant vs control", pc.mde_single_variant_vs_control(
                    sd, n_c, n_smallest_variant, significance, power)),
                ("Interaction", pc.mde_interaction(sd, n_c, n_v1, n_v2, n_v3, significance, power)),
            ]
            st.markdown("**Minimum detectable effect:**")
            for label, mde in comparisons:
                st.markdown(f"- {label}: {format_mde(mde, sd, mean, outcome_type)}")
                summary.append(summary_row("4-way", q, inputs, label, mde, groups_text))
            st.markdown(f"**Group sizes (Control / Variant 1 / Variant 2 / Variant 3):** {groups_text}")
            st.caption("Single variant vs control uses the smallest variant group (conservative).")

# ---------------------------------------------------------------- summary
st.header("Summary")
if summary:
    st.dataframe(summary, hide_index=True, width="stretch")
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(summary[0]))
    writer.writeheader()
    writer.writerows(summary)
    st.download_button("Download CSV", buffer.getvalue(), "mde_summary.csv", "text/csv")
else:
    st.info("No valid questions to summarise yet.")
