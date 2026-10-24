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

## Assumptions

- **Normal approximation (z-test).** Reasonable for groups of a few dozen or more.
- **Equal variance.** Every group has the same spread of answers.
- **Binary SD at the baseline rate.** Slightly optimistic if the treatment moves the rate towards 50%.
- **No attrition.** Everyone we pay gives usable answers. If you expect dropouts, lower the budget accordingly.
- **One test per question.** No correction for testing several questions at once.
- **No interaction for main effects.** The main-effect MDE assumes the two treatments don't change each other's effect.
