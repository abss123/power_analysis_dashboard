# How the MDE calculator works

## What is a minimum detectable effect?

When we compare groups in an experiment, random noise means two groups will
rarely have exactly the same average, even if the treatment does nothing. The
**minimum detectable effect (MDE)** is the smallest true difference that our
experiment would reliably tell apart from noise. "Reliably" means we would
detect it 80% of the time (the **power**) while being wrong no more than 5% of
the time when there is no effect (a **95% significance** level).

If the effect you expect is *smaller* than the MDE, the experiment will probably
miss it, even if the effect is real. Bigger groups give smaller MDEs.

## From budget to group sizes

1. Cost per person = hourly rate × minutes ÷ 60. At $15/hour for 30 minutes, that is $7.50.
2. Participants = budget ÷ cost per person, **rounded down** so we never overspend.
   $800 ÷ $7.50 = 106.7, so we get 106 people.
3. People are split as evenly as possible, with any leftovers going to the first groups:
   2-way: 53 / 53. 4-way: 27 / 27 / 26 / 26.

## The formula

    MDE = M × SD × √(sum of 1/n over the groups being compared)

- **M** = 1.96 + 0.84 ≈ 2.80 at 95% significance and 80% power. Stricter settings give a larger M.
- **SD** is the standard deviation: how spread out answers are. For a yes/no
  question with rate p, SD = √(p × (1 − p)). At 30%, SD ≈ 0.46.
- **n** is the number of people in each group.

The app shows each MDE three ways: in the question's own units (points, or
percentage points for yes/no questions), in SDs, and as a % of the average.

## What each comparison means

| Comparison | Question it answers | Groups under the square root |
|---|---|---|
| **2-way** | Does the variant differ from control? | 1/n_control + 1/n_variant |
| **Main effect** (4-way) | Does treatment A work, averaging over whether people also got B? | (1/n_c + 1/n_v1 + 1/n_v2 + 1/n_v3) ÷ 4 |
| **Single variant vs control** (4-way) | Does one specific cell differ from control? | 1/n_control + 1/n_variant |
| **Interaction** (4-way) | Does doing *both* add more (or less) than the two effects separately? | 1/n_c + 1/n_v1 + 1/n_v2 + 1/n_v3 |

The main effect uses all four groups, so it is about as precise as the 2-way
comparison. A single cell vs control uses only half the people, so its MDE is
about 1.4× larger. The interaction is the hardest to detect: about 2× the main effect.
For the single-variant comparison, the app uses the smallest variant group, which is the cautious choice.

In the 4-way tab, the main effects of A and B always have the same MDE (the
design is balanced), so the app shows it once as "Main effects". For a yes/no
question, an MDE is flagged as **not achievable** if the rate can't move that
far in either direction (for example, a 75 pp change from a 30% baseline).

## False positives and counting tests

A **false positive** is a "significant" result that happened purely by luck.
At 95% significance, each test has a 5% chance of one when nothing is really going on.
Run many tests and the chance that *at least one* of them is a false positive grows quickly.

**How tests are counted.** Total tests = questions × tests per question.
- 2-way: 1 test per question (variant vs control).
- 4-way: 1 each for main effect A, main effect B and the interaction, and
  3 for "each variant vs control" (one per variant). With 3 questions and both
  main effects, that is 3 × 2 = 6 tests.

Assuming no treatment has a real effect, with k tests each at false-positive rate α:

| | Formula | 3 tests at 5% |
|---|---|---|
| No false positives | (1 − α)^k | 85.7% |
| At least one false positive | 1 − (1 − α)^k | 14.3% |
| Every test a false positive | α^k | 0.01% |

**The Bonferroni correction** divides α by the number of tests (5% ÷ 3 ≈ 1.67%,
so each test uses 98.3% significance). This keeps the chance of *any* false
positive across the whole experiment at about 5%. The price: each test needs
stronger evidence, so **every MDE gets larger** (e.g. 2-way with SD 1.5 goes
from 0.82 to 0.94 points with 3 tests).

## Assumptions

- **Normal approximation (z-test).** Reasonable for groups of a few dozen or more.
- **Equal variance.** Every group has the same spread of answers.
- **Binary SD at the baseline rate.** Slightly optimistic if the treatment moves the rate towards 50%.
- **No attrition.** Everyone we pay gives usable answers. If you expect dropouts, lower the budget accordingly.
- **Multiple tests are uncorrected unless Bonferroni is switched on.**
- **Tests are treated as independent.** Outcomes measured on the same people are
  usually correlated, so the false-positive numbers are approximate. (With
  correlated tests the true chance of at least one false positive is somewhat lower,
  and Bonferroni is somewhat conservative.)
- **No interaction for main effects.** The main-effect MDE assumes the two treatments don't change each other's effect.
