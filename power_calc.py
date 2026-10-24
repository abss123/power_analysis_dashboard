"""Minimum detectable effect (MDE) and false-positive calculations for a budget-constrained experiment.

Method
------
The budget fixes how many participants we can pay. They are split as evenly as
possible into groups. For each outcome question, the MDE is the smallest true
difference between groups that we would detect with the chosen power, using a
two-sided t-test at the per-test alpha:

    MDE = (t_{1 - alpha/2, df} + t_{power, df}) * SD * sqrt(sum of c_j^2 / n_j over the groups)

with df = participants - groups, because the analysis pools the variance across
every group in the design. This swaps the usual z quantiles for t quantiles, a
standard approximation that matches the exact noncentral-t calculation to within
about 0.001 SD at these sample sizes.

Each comparison (2-way, main effect, single variant vs control, interaction)
differs only in which groups enter that square root, and with what weight.
With the optional Bonferroni correction, alpha is divided by the number of tests.

Assumptions
-----------
- Two-sided t-test with df = participants - groups.
- All groups share the same standard deviation (equal variance).
- Binary outcomes use the same t formula with SD = sqrt(p * (1 - p)) at the baseline
  rate p: slightly optimistic if the effect moves p towards 0.5, and slightly
  conservative compared with a two-proportion z-test.
- No attrition: everyone we pay provides usable data.
- Multiple tests are uncorrected unless Bonferroni is switched on.
- False-positive probabilities treat tests as independent (outcomes from the same
  people are usually correlated, so these are approximate).
- The main-effect MDE assumes the two treatments do not interact.
"""

import math

from scipy.stats import t as t_distribution


def cost_per_person(rate_per_hour, minutes_per_person):
    """Dollars paid to one participant."""
    # cost = rate * minutes / 60
    return rate_per_hour * minutes_per_person / 60


def participants_affordable(budget, rate_per_hour, minutes_per_person):
    """Number of participants the budget covers, rounded DOWN so we never overspend."""
    # N = floor(budget / cost per person)
    return math.floor(budget / cost_per_person(rate_per_hour, minutes_per_person))


def split_into_groups(n_total, n_groups):
    """Split n_total as evenly as possible; leftovers go to the first groups."""
    # e.g. 106 into 4 -> base 26, remainder 2 -> [27, 27, 26, 26]
    base_size, leftover = divmod(n_total, n_groups)
    return [base_size + 1 if index < leftover else base_size for index in range(n_groups)]


def degrees_of_freedom(n_total, n_groups):
    """Degrees of freedom for a t-test that pools variance across all groups."""
    # df = N - number of groups   (e.g. 106 - 2 = 104, 106 - 4 = 102)
    return n_total - n_groups


def sd_for_binary(rate):
    """Standard deviation of a yes/no outcome with the given rate."""
    # SD = sqrt(p * (1 - p))
    return math.sqrt(rate * (1 - rate))


def per_test_alpha(significance, total_tests, bonferroni):
    """False-positive rate allowed for each individual test."""
    # alpha = 1 - significance;  with Bonferroni: alpha / k
    alpha = 1 - significance
    return alpha / total_tests if bonferroni else alpha


def multiplier(alpha, power, df):
    """Number of standard errors the true effect must be (None if df < 1)."""
    # M = t_{1 - alpha/2, df} + t_{power, df}   (two-sided)
    if df < 1:
        return None
    return t_distribution.ppf(1 - alpha / 2, df) + t_distribution.ppf(power, df)


def _mde(sd, sum_of_weighted_inverses, alpha, power, df):
    """Shared step for every comparison: MDE = M * SD * sqrt(sum c_j^2 / n_j). None if df < 1."""
    standard_errors_needed = multiplier(alpha, power, df)
    if standard_errors_needed is None:
        return None
    return standard_errors_needed * sd * math.sqrt(sum_of_weighted_inverses)


def mde_two_way(sd, n_control, n_variant, alpha, power, df):
    """MDE for control vs one variant."""
    # MDE = M * SD * sqrt(1/n_c + 1/n_v)
    return _mde(sd, 1 / n_control + 1 / n_variant, alpha, power, df)


def mde_main_effect(sd, n_control, n_variant1, n_variant2, n_variant3, alpha, power, df):
    """MDE for one treatment's effect, averaged over whether the other treatment is present."""
    # MDE = M * SD * sqrt((1/n_c + 1/n_v1 + 1/n_v2 + 1/n_v3) / 4)
    sum_of_inverses = 1 / n_control + 1 / n_variant1 + 1 / n_variant2 + 1 / n_variant3
    return _mde(sd, sum_of_inverses / 4, alpha, power, df)


def mde_single_variant_vs_control(sd, n_control, n_variant, alpha, power, df):
    """MDE for comparing one cell of the 2x2 directly against control."""
    # MDE = M * SD * sqrt(1/n_c + 1/n_v)
    return _mde(sd, 1 / n_control + 1 / n_variant, alpha, power, df)


def mde_interaction(sd, n_control, n_variant1, n_variant2, n_variant3, alpha, power, df):
    """MDE for the interaction: does doing both treatments add more than the sum of each alone?"""
    # MDE = M * SD * sqrt(1/n_c + 1/n_v1 + 1/n_v2 + 1/n_v3)
    sum_of_inverses = 1 / n_control + 1 / n_variant1 + 1 / n_variant2 + 1 / n_variant3
    return _mde(sd, sum_of_inverses, alpha, power, df)


def binary_mde_achievable(mde, rate):
    """Can a rate move by `mde` in at least one direction without leaving 0..1?"""
    # achievable if MDE <= max(p, 1 - p)
    return mde <= max(rate, 1 - rate)


def in_sd_units(mde, sd):
    """MDE expressed as a fraction of a standard deviation (an effect size)."""
    # d = MDE / SD
    return mde / sd


def share_of_mean(mde, mean):
    """MDE as a fraction of the average (None if the average is zero)."""
    # share = MDE / |mean|
    return mde / abs(mean) if mean else None


# --- False positives, assuming no treatment has a real effect and k independent tests ---

def prob_no_false_positive(alpha, total_tests):
    """Chance that none of the tests is significant by luck."""
    # P(none) = (1 - alpha)^k
    return (1 - alpha) ** total_tests


def prob_at_least_one_false_positive(alpha, total_tests):
    """Chance that one or more tests is significant by luck."""
    # P(at least one) = 1 - (1 - alpha)^k
    return 1 - (1 - alpha) ** total_tests


def prob_all_false_positives(alpha, total_tests):
    """Chance that every test is significant by luck."""
    # P(all) = alpha^k
    return alpha ** total_tests
