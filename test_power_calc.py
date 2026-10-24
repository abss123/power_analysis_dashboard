"""Check numbers for power_calc.py at the defaults: $800, $15/hr, 30 min, 95%, 80%."""

import pytest

import power_calc as pc

SIG, ALPHA, POWER = 0.95, 0.05, 0.80
N_TOTAL = pc.participants_affordable(800, 15, 30)
CONTROL, VARIANT = pc.split_into_groups(N_TOTAL, 2)
C, V1, V2, V3 = pc.split_into_groups(N_TOTAL, 4)
SMALLEST_VARIANT = min(V1, V2, V3)
DF_TWO = pc.degrees_of_freedom(N_TOTAL, 2)
DF_FOUR = pc.degrees_of_freedom(N_TOTAL, 4)


def test_budget():
    assert pc.cost_per_person(15, 30) == 7.5
    assert N_TOTAL == 106  # 106.67 rounds down, not up


def test_groups():
    assert pc.split_into_groups(106, 2) == [53, 53]
    assert pc.split_into_groups(106, 4) == [27, 27, 26, 26]
    assert sum(pc.split_into_groups(107, 4)) == 107


def test_degrees_of_freedom():
    assert DF_TWO == 104
    assert DF_FOUR == 102


def test_multiplier():
    assert pc.multiplier(ALPHA, POWER, 104) == pytest.approx(2.828, abs=0.0005)
    assert pc.multiplier(ALPHA, POWER, 1_000_000) == pytest.approx(2.802, abs=0.0005)  # t -> z


def test_sd_for_binary():
    assert pc.sd_for_binary(0.30) == pytest.approx(0.4583, abs=1e-4)
    assert pc.sd_for_binary(0.50) == 0.5


def test_continuous_sd_1_5():
    sd = 1.5
    two_way = pc.mde_two_way(sd, CONTROL, VARIANT, ALPHA, POWER, DF_TWO)
    assert two_way == pytest.approx(0.824, abs=0.0005)
    assert pc.in_sd_units(two_way, sd) == pytest.approx(0.549, abs=0.0005)
    assert pc.mde_main_effect(sd, C, V1, V2, V3, ALPHA, POWER, DF_FOUR) == pytest.approx(0.824, abs=0.0005)
    assert pc.mde_single_variant_vs_control(sd, C, SMALLEST_VARIANT, ALPHA, POWER, DF_FOUR) == pytest.approx(1.166, abs=0.0005)
    assert pc.mde_interaction(sd, C, V1, V2, V3, ALPHA, POWER, DF_FOUR) == pytest.approx(1.649, abs=0.0005)


def test_binary_rate_0_30():
    sd = pc.sd_for_binary(0.30)
    assert pc.mde_two_way(sd, CONTROL, VARIANT, ALPHA, POWER, DF_TWO) == pytest.approx(0.252, abs=0.0005)
    assert pc.mde_main_effect(sd, C, V1, V2, V3, ALPHA, POWER, DF_FOUR) == pytest.approx(0.252, abs=0.0005)
    assert pc.mde_single_variant_vs_control(sd, C, SMALLEST_VARIANT, ALPHA, POWER, DF_FOUR) == pytest.approx(0.356, abs=0.0005)
    assert pc.mde_interaction(sd, C, V1, V2, V3, ALPHA, POWER, DF_FOUR) == pytest.approx(0.504, abs=0.0005)


def test_df_below_one_is_not_achievable():
    # 4 people in 4 groups -> df = 0
    df = pc.degrees_of_freedom(4, 4)
    assert pc.multiplier(ALPHA, POWER, df) is None
    assert pc.mde_main_effect(1.5, 1, 1, 1, 1, ALPHA, POWER, df) is None
    assert pc.mde_interaction(1.5, 1, 1, 1, 1, ALPHA, POWER, df) is None
    assert pc.mde_single_variant_vs_control(1.5, 1, 1, ALPHA, POWER, df) is None
    assert pc.mde_two_way(1.5, 1, 1, ALPHA, POWER, 0) is None


def test_share_of_mean():
    assert pc.share_of_mean(0.249, 0.30) == pytest.approx(0.83, abs=0.001)
    assert pc.share_of_mean(1.0, 0) is None


# --- False positives and Bonferroni ---

def test_false_positives_3_tests():
    assert pc.prob_no_false_positive(0.05, 3) == pytest.approx(0.857375, abs=1e-9)
    assert pc.prob_at_least_one_false_positive(0.05, 3) == pytest.approx(0.142625, abs=1e-9)
    assert pc.prob_all_false_positives(0.05, 3) == pytest.approx(0.000125, abs=1e-12)


def test_false_positives_6_tests():
    assert pc.prob_at_least_one_false_positive(0.05, 6) == pytest.approx(0.264908, abs=1e-6)


def test_per_test_alpha():
    assert pc.per_test_alpha(SIG, 3, bonferroni=False) == pytest.approx(0.05)
    assert pc.per_test_alpha(SIG, 3, bonferroni=True) == pytest.approx(0.05 / 3)


def test_bonferroni_false_positives():
    alpha_3 = pc.per_test_alpha(SIG, 3, bonferroni=True)
    alpha_6 = pc.per_test_alpha(SIG, 6, bonferroni=True)
    assert pc.prob_at_least_one_false_positive(alpha_3, 3) == pytest.approx(0.049171, abs=1e-6)
    assert pc.prob_at_least_one_false_positive(alpha_6, 6) == pytest.approx(0.04897, abs=1e-5)


def test_bonferroni_mdes_sd_1_5():
    alpha_3 = pc.per_test_alpha(SIG, 3, bonferroni=True)
    alpha_6 = pc.per_test_alpha(SIG, 6, bonferroni=True)
    assert pc.mde_two_way(1.5, CONTROL, VARIANT, alpha_3, POWER, DF_TWO) == pytest.approx(0.955, abs=0.0005)
    assert pc.mde_main_effect(1.5, C, V1, V2, V3, alpha_6, POWER, DF_FOUR) == pytest.approx(1.030, abs=0.0005)


def test_toggle_off_leaves_mdes_unchanged():
    alpha_off = pc.per_test_alpha(SIG, 6, bonferroni=False)
    assert pc.mde_two_way(1.5, CONTROL, VARIANT, alpha_off, POWER, DF_TWO) == pytest.approx(
        pc.mde_two_way(1.5, CONTROL, VARIANT, ALPHA, POWER, DF_TWO))


def test_binary_mde_achievable():
    assert pc.binary_mde_achievable(0.504, 0.30)
    assert not pc.binary_mde_achievable(0.75, 0.30)
