"""Check numbers for power_calc.py at the defaults: $800, $15/hr, 30 min, 95%, 80%."""

import pytest

import power_calc as pc

SIG, POWER = 0.95, 0.80
N_TOTAL = pc.participants_affordable(800, 15, 30)
CONTROL, VARIANT = pc.split_into_groups(N_TOTAL, 2)
C, V1, V2, V3 = pc.split_into_groups(N_TOTAL, 4)
SMALLEST_VARIANT = min(V1, V2, V3)


def test_budget():
    assert pc.cost_per_person(15, 30) == 7.5
    assert N_TOTAL == 106  # 106.67 rounds down, not up


def test_groups():
    assert pc.split_into_groups(106, 2) == [53, 53]
    assert pc.split_into_groups(106, 4) == [27, 27, 26, 26]
    assert sum(pc.split_into_groups(107, 4)) == 107


def test_multiplier():
    assert pc.multiplier(SIG, POWER) == pytest.approx(2.80, abs=0.005)


def test_sd_for_binary():
    assert pc.sd_for_binary(0.30) == pytest.approx(0.4583, abs=1e-4)
    assert pc.sd_for_binary(0.50) == 0.5


def test_continuous_sd_1_5():
    sd = 1.5
    two_way = pc.mde_two_way(sd, CONTROL, VARIANT, SIG, POWER)
    assert two_way == pytest.approx(0.816, abs=0.001)
    assert pc.in_sd_units(two_way, sd) == pytest.approx(0.54, abs=0.005)
    assert pc.mde_main_effect(sd, C, V1, V2, V3, SIG, POWER) == pytest.approx(0.816, abs=0.001)
    assert pc.mde_single_variant_vs_control(sd, C, SMALLEST_VARIANT, SIG, POWER) == pytest.approx(1.155, abs=0.001)
    assert pc.mde_interaction(sd, C, V1, V2, V3, SIG, POWER) == pytest.approx(1.633, abs=0.001)


def test_binary_rate_0_30():
    sd = pc.sd_for_binary(0.30)
    assert pc.mde_two_way(sd, CONTROL, VARIANT, SIG, POWER) == pytest.approx(0.249, abs=0.001)
    assert pc.mde_main_effect(sd, C, V1, V2, V3, SIG, POWER) == pytest.approx(0.249, abs=0.001)
    assert pc.mde_single_variant_vs_control(sd, C, SMALLEST_VARIANT, SIG, POWER) == pytest.approx(0.353, abs=0.001)
    assert pc.mde_interaction(sd, C, V1, V2, V3, SIG, POWER) == pytest.approx(0.499, abs=0.001)


def test_share_of_mean():
    assert pc.share_of_mean(0.249, 0.30) == pytest.approx(0.83, abs=0.001)
    assert pc.share_of_mean(1.0, 0) is None
