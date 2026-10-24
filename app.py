"""Streamlit UI for the MDE calculator. All statistics live in power_calc.py."""

from pathlib import Path

import streamlit as st

import power_calc as pc

HERE = Path(__file__).parent
TYPES = ["Continuous", "Binary"]
DEFAULT_MEAN = {"Continuous": 4.3, "Binary": 0.30}
DEFAULT_SD = 1.5
# Q3 defaults to a binary (behavioural) outcome so both types are visible out of the box.
DEFAULT_TYPE_BY_QUESTION = {3: "Binary"}

MAIN_A = "Main effect of treatment A"
MAIN_B = "Main effect of treatment B"
INTERACTION = "Interaction (A x B)"
VS_CONTROL = "Each variant vs control (3 tests)"
# How many tests each 4-way comparison adds per question.
TESTS_PER_COMPARISON = {MAIN_A: 1, MAIN_B: 1, INTERACTION: 1, VS_CONTROL: 3}

st.set_page_config(page_title="MDE calculator", layout="wide")
st.title("Minimum detectable effect calculator")

with st.expander("How to read this"):
    st.markdown(
        "The **minimum detectable effect (MDE)** is the smallest true difference between groups "
        "that this experiment would reliably pick up with a two-sided t-test "
        "(at the chosen power and significance); "
        "if the effect you expect is smaller, the experiment is likely to miss it. "
        "Your budget sets how many people we can pay, and smaller groups mean larger MDEs. "
        "The more tests you run, the more likely at least one looks significant purely by chance; "
        "the Bonferroni correction controls that, at the cost of larger MDEs. "
        "See `METHODOLOGY.md` for the formulas and assumptions."
    )
with st.expander("Show the code behind the numbers (power_calc.py)"):
    st.code((HERE / "power_calc.py").read_text(), language="python")

# ---------------------------------------------------------------- budget (sidebar)
with st.sidebar:
    st.header("Budget")
    budget = st.number_input("Budget ($)", min_value=0.0, value=800.0, step=50.0)
    rate_per_hour = st.number_input("Rate per person per hour ($)", min_value=0.01, value=15.0, step=1.0)
    minutes_per_person = st.number_input(
        "Duration per person (minutes, incl. questionnaire and game)",
        min_value=1.0, value=30.0, step=5.0,
    )
    cost_each = pc.cost_per_person(rate_per_hour, minutes_per_person)
    n_total = pc.participants_affordable(budget, rate_per_hour, minutes_per_person)
    st.metric("Participants we can afford", n_total)
    st.metric("Cost per person", f"${cost_each:,.2f}")
    st.metric("Total spend", f"${n_total * cost_each:,.2f}")

if n_total < 4:
    st.warning("The budget must cover at least 4 people (one per group in the 4-way design).")
    st.stop()


# ---------------------------------------------------------------- formatting helpers
def format_level(fraction):
    """0.95 -> '95%', 0.98333 -> '98.3%', 0.99967 -> '99.97%' (never rounds up to 100%)."""
    for decimals in (1, 2, 3):
        if round(fraction * 100, decimals) < 100:
            break
    return f"{round(fraction * 100, decimals):g}%"


def format_probability(probability):
    """1 decimal place; 2 between 0.01% and 0.1%; '< 0.01%' below that."""
    if probability < 0.0001:
        return "< 0.01%"
    return f"{probability:.2%}" if probability < 0.001 else f"{probability:.1%}"


def format_raw(mde, outcome_type):
    """'0.82 pts' for continuous, '25 pp' for binary."""
    return f"{mde * 100:.0f} pp" if outcome_type == "Binary" else f"{mde:.2f} pts"


def format_key(mde, sd, outcome_type):
    """Short form for the key results panel: '0.82 pts (0.54 SD)' or '25 pp'."""
    if outcome_type == "Binary":
        return format_raw(mde, outcome_type)
    return f"{format_raw(mde, outcome_type)} ({pc.in_sd_units(mde, sd):.2f} SD)"


def format_detail(mde, sd, mean):
    """'0.54 SD · 19% of mean'."""
    share = pc.share_of_mean(mde, mean)
    share_text = f" · {share:.0%} of mean" if share is not None else ""
    return f"{pc.in_sd_units(mde, sd):.2f} SD{share_text}"


def is_achievable(mde, mean, outcome_type):
    """False if there are too few people to estimate it (None) or a binary rate can't move that far."""
    if mde is None:
        return False
    return outcome_type != "Binary" or pc.binary_mde_achievable(mde, mean)


def not_achievable_text(mde, outcome_type):
    return "Not achievable" if mde is None else f"{format_raw(mde, outcome_type)} (not achievable)"


# ---------------------------------------------------------------- input helpers
def reset_mean(prefix, q):
    """When a question's type changes, reset its average to a sensible default."""
    st.session_state[f"{prefix}_q{q}_mean"] = DEFAULT_MEAN[st.session_state[f"{prefix}_q{q}_type"]]


def basic_settings(prefix):
    """Significance, power and number of questions for one design."""
    cols = st.columns(3)
    significance = cols[0].number_input(
        "Significance (confidence level, %)", 50.0, 99.9, 95.0, 0.5, key=f"{prefix}_sig"
    ) / 100
    power = cols[1].number_input("Power (%)", 50.0, 99.9, 80.0, 0.5, key=f"{prefix}_power") / 100
    n_questions = cols[2].number_input(
        "Number of questions (attitudinal + behavioral)", 1, 10, 3, 1, key=f"{prefix}_nq"
    )
    return significance, power, int(n_questions)


def testing_settings(prefix, significance, n_questions, tests_per_question):
    """Show the test count and Bonferroni toggle. Returns (per-test alpha, total tests)."""
    total_tests = n_questions * tests_per_question
    question_word = "question" if n_questions == 1 else "questions"
    comparison_word = "comparison" if tests_per_question == 1 else "comparisons"
    st.caption(
        f"{total_tests} test{'s' if total_tests != 1 else ''} in total "
        f"({n_questions} {question_word} x {tests_per_question} {comparison_word})"
    )
    bonferroni = st.toggle("Correct for multiple tests (Bonferroni)", key=f"{prefix}_bonferroni")
    alpha = pc.per_test_alpha(significance, total_tests, bonferroni)
    st.caption(f"Each test uses {format_level(1 - alpha)} significance")
    return alpha, total_tests, bonferroni


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


# ---------------------------------------------------------------- output helpers
def question_card(prefix, q, groups_text, compute_mdes, copy_from=None, copy_missing=False):
    """One bordered card: inputs left, results right. Returns (inputs, [(label, mde), ...])."""
    with st.container(border=True):
        st.subheader(f"Q{q}")
        left, right = st.columns(2, gap="large")
        with left:
            if copy_missing:
                st.warning("The matching 2-way question has invalid inputs; fix it there.")
                return None, []
            inputs = question_inputs(prefix, q, copy_from)
        if inputs is None:
            return None, []
        outcome_type, mean, sd = inputs
        mdes = compute_mdes(sd)
        with right:
            for label, mde in mdes:
                if is_achievable(mde, mean, outcome_type):
                    st.metric(label, format_raw(mde, outcome_type))
                    st.caption(format_detail(mde, sd, mean))
                else:
                    st.error(f"{label}: {not_achievable_text(mde, outcome_type)}")
            st.markdown(f"**Group sizes:** {groups_text}")
        return inputs, mdes


def key_results(panel, groups_text, results, alpha, total_tests):
    """Fill the key results container. `results` is a list of (q, inputs, [(label, mde), ...])."""
    with panel:
        st.subheader("Key results")
        cols = st.columns(3)
        cols[0].metric("Total participants", n_total)
        cols[1].metric("Per group", groups_text)
        cols[2].metric(
            "At least one false positive",
            format_probability(pc.prob_at_least_one_false_positive(alpha, total_tests)),
            border=True,
        )
        tiles = []
        for q, inputs, mdes in results:
            if inputs is None:
                tiles.append((f"Q{q}", None, True))
                continue
            outcome_type, mean, sd = inputs
            for label, mde in mdes:
                tile_label = f"Q{q}" if len(mdes) == 1 else f"Q{q} · {label}"
                if is_achievable(mde, mean, outcome_type):
                    tiles.append((tile_label, format_key(mde, sd, outcome_type), True))
                else:
                    tiles.append((tile_label, not_achievable_text(mde, outcome_type), False))
        per_row = 3
        for start in range(0, len(tiles), per_row):
            row = st.columns(per_row)
            for col, (label, value, achievable) in zip(row, tiles[start:start + per_row]):
                if value is None:
                    col.metric(label, "—")
                elif achievable:
                    col.metric(label, value)
                else:
                    col.error(f"**{label}**  \n{value}")


def false_positive_panel(significance, alpha, total_tests, bonferroni):
    with st.container(border=True):
        st.subheader("Chance of false positives (if no treatment has a real effect)")
        at_least_one = pc.prob_at_least_one_false_positive(alpha, total_tests)
        cols = st.columns(3)
        cols[0].metric("No false positives", format_probability(pc.prob_no_false_positive(alpha, total_tests)))
        cols[1].metric("At least one false positive", format_probability(at_least_one))
        cols[2].metric("All tests false positive", format_probability(pc.prob_all_false_positives(alpha, total_tests)))

        if total_tests == 1:
            st.caption(
                f"With a single test at {format_level(1 - alpha)} significance, there is a "
                f"{format_probability(at_least_one)} chance it comes out significant purely by chance."
            )
        elif bonferroni:
            st.caption(
                f"Across {total_tests} tests at {format_level(1 - alpha)} significance each (Bonferroni), "
                f"there is a {format_probability(at_least_one)} chance at least one comes out significant "
                f"purely by chance, close to the {format_level(1 - significance)} target for the whole experiment."
            )
        else:
            corrected = pc.prob_at_least_one_false_positive(
                pc.per_test_alpha(significance, total_tests, bonferroni=True), total_tests
            )
            st.caption(
                f"Across {total_tests} tests at {format_level(significance)} significance, there is a "
                f"{format_probability(at_least_one)} chance at least one comes out significant purely by "
                f"chance. Turn on the Bonferroni correction to bring this down to about "
                f"{format_probability(corrected)}."
            )


# ---------------------------------------------------------------- tabs
def two_way_tab():
    """Render the 2-way tab. Returns {q: inputs} so the 4-way tab can copy them."""
    significance, power, n_questions = basic_settings("two")
    alpha, total_tests, bonferroni = testing_settings("two", significance, n_questions, 1)
    n_control, n_variant = pc.split_into_groups(n_total, 2)
    df = pc.degrees_of_freedom(n_total, 2)
    groups_text = f"{n_control} / {n_variant}"

    def compute_mdes(sd):
        return [("MDE", pc.mde_two_way(sd, n_control, n_variant, alpha, power, df))]

    panel = st.container(border=True)
    results, inputs_by_question = [], {}
    for q in range(1, n_questions + 1):
        inputs, mdes = question_card("two", q, groups_text, compute_mdes)
        inputs_by_question[q] = inputs
        results.append((q, inputs, mdes))
    key_results(panel, groups_text, results, alpha, total_tests)
    false_positive_panel(significance, alpha, total_tests, bonferroni)
    return inputs_by_question


def four_way_tab(two_way_inputs):
    mirror = st.checkbox("Use same question inputs as the 2-way experiment", value=True)
    significance, power, n_questions = basic_settings("four")
    selected = st.multiselect(
        "Comparisons you will test for each question",
        list(TESTS_PER_COMPARISON), default=[MAIN_A, MAIN_B], key="four_comparisons",
    )
    if not selected:
        st.warning("Select at least one comparison.")
        return
    tests_per_question = sum(TESTS_PER_COMPARISON[name] for name in selected)
    alpha, total_tests, bonferroni = testing_settings("four", significance, n_questions, tests_per_question)

    n_c, n_v1, n_v2, n_v3 = pc.split_into_groups(n_total, 4)
    n_smallest_variant = min(n_v1, n_v2, n_v3)
    groups_text = f"{n_c} / {n_v1} / {n_v2} / {n_v3}"
    # Every 4-way comparison pools variance across all four groups.
    df = pc.degrees_of_freedom(n_total, 4)

    def compute_mdes(sd):
        mdes = []
        if MAIN_A in selected or MAIN_B in selected:
            # Balanced design: A and B have the same MDE, so show it once.
            label = "Main effects" if {MAIN_A, MAIN_B} <= set(selected) else (
                "Main effect A" if MAIN_A in selected else "Main effect B")
            mdes.append((label, pc.mde_main_effect(sd, n_c, n_v1, n_v2, n_v3, alpha, power, df)))
        if INTERACTION in selected:
            mdes.append(("Interaction", pc.mde_interaction(sd, n_c, n_v1, n_v2, n_v3, alpha, power, df)))
        if VS_CONTROL in selected:
            # Smallest variant group gives the largest (most cautious) of the three MDEs.
            mdes.append(("Variant vs control", pc.mde_single_variant_vs_control(
                sd, n_c, n_smallest_variant, alpha, power, df)))
        return mdes

    panel = st.container(border=True)
    results = []
    for q in range(1, n_questions + 1):
        copy_from = two_way_inputs.get(q) if mirror else None
        copy_missing = mirror and q in two_way_inputs and copy_from is None
        inputs, mdes = question_card("four", q, groups_text, compute_mdes, copy_from, copy_missing)
        results.append((q, inputs, mdes))
    key_results(panel, groups_text, results, alpha, total_tests)
    false_positive_panel(significance, alpha, total_tests, bonferroni)


tab_two, tab_four = st.tabs(["2-way experiment", "4-way experiment (2x2)"])
with tab_two:
    two_way_inputs = two_way_tab()
with tab_four:
    four_way_tab(two_way_inputs)
